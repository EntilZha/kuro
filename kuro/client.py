from typing import Dict, Optional
import json
import os
from collections import defaultdict, namedtuple

import coreapi
import cpuinfo
import psutil
from gpustat import GPUStatCollection


KURO_SERVER = os.environ.get('KURO_SERVER', 'http://localhost:8000')
if len(KURO_SERVER) == 0:
    KURO_SERVER = 'http://localhost:8000'


Metric = namedtuple('Metric', ['url', 'name', 'mode'])


def get_gpu_list():
    try:
        gpu_collection = GPUStatCollection.new_query()
        gpu_infos = [
            g.jsonify()
            for g in gpu_collection
        ]
        gpu_json = {
            'gpus': [
                {'name': g['name'], 'memory': float(g['memory.total']) / 1024}
                for g in gpu_infos
            ]
        }
        return gpu_json
    except:
        return {'gpus': []}


class TooManyTrials(Exception):
    pass


class KuroClient:
    def __init__(self, server=KURO_SERVER):
        self.schema_endpoint = os.path.join(server, 'schema')
        self.client = coreapi.Client()
        self.schema = self.client.get(self.schema_endpoint)

    def query(self, args, params=None):
        return self.client.action(self.schema, args, params)

    def list_workers(self):
        return self.client.action(self.schema, ['workers', 'list'])

    def create_worker(self, name, cpu_brand, memory, gpus):
        return self.query(
            ['workers', 'create'],
            params={'name': name, 'cpu_brand': cpu_brand, 'memory': memory, 'gpus': gpus, 'active': True}
        )

    def get_trial(self, trial_id):
        return self.query(['trials', 'read'], params={'id': trial_id})

    def list_metrics(self, name=None):
        metrics = self.query(['metrics', 'list'])
        return [
            m for m in metrics if name is None or m['name'] == name
        ]

    def get_or_create_metric(self, name, mode=None):
        return self.query(['metrics', 'get-or-create', 'create'], params={'name': name, 'mode': mode})

    def get_update_create_experiment(self, group, identifier, hyper_parameters=None, metrics=None, n_trials=None):
        """
        Attempt to find an experiment keyed by group, identifier, and hyper_parameters. If an experiment is found then
        metrics are appended to existing metrics and n_trials is updated if it is not None. The return value is the
        full experiment including possibly more metrics from previous creations

        If the experiment does not exist then one is created based on the input parameters. If hyper_parameters is
        None then an empty set of parameters is used represented by a blank dictionary
        :param group:
        :param identifier:
        :param hyper_parameters:
        :param metrics:
        :param n_trials:
        :return:
        """
        params = {
            'group': group,
            'identifier': identifier,
        }

        if hyper_parameters is not None:
            params['hyper_parameters'] = hyper_parameters

        if metrics is not None:
            params['metrics'] = metrics

        if n_trials is not None:
            params['n_trials'] = n_trials

        return self.query(['experiments', 'get-or-create', 'create'], params=params)

    def get_or_create_trial(self, worker_url, experiment_url):
        return self.query(
            ['trials', 'get-or-create', 'create'],
            params={'worker': worker_url, 'experiment': experiment_url}
        )

    def create_result_value(self, trial_url, metric_url, step, value):
        if step is None:
            step = 0
        return self.query(
            ['result_values', 'report', 'create'],
            params={
                'trial': trial_url,
                'metric': metric_url,
                'step': step,
                'value': value
            }
        )

    def trial_complete(self, trial_url):
        return self.query(
            ['trials', 'complete', 'create'],
            params={'trial': trial_url}
        )


class Experiment:
    def __init__(self, worker: 'Worker', group, identifier, hyper_parameters=None, metrics=None, n_trials=None):
        self.worker = worker
        self.client = worker.client
        self.group = group
        self.identifier = identifier
        if hyper_parameters is None:
            self.hyper_parameters = {}
        else:
            self.hyper_parameters = hyper_parameters

        self.n_trials = n_trials
        initial_metrics = self._init_metrics(metrics)
        metric_urls = [m.url for m in initial_metrics.values()]
        experiment = self.client.get_update_create_experiment(
            group, identifier, hyper_parameters=hyper_parameters, metrics=metric_urls, n_trials=n_trials
        )

        self.metrics = {e['name']: Metric(e['url'], e['name'], e['mode']) for e in experiment['metrics']}
        self.n_trials = experiment['n_trials']
        self.url = experiment['url']

    def _init_metrics(self, metrics):
        if metrics is None:
            return {}
        metric_lookup = {}
        validated_metrics = {}
        if isinstance(metrics, dict):
            for name, mode in metrics.items():
                validated_metrics[name] = mode if mode is not None else 'auto'
        elif isinstance(metrics, list) or isinstance(metrics, tuple):
            for m in metrics:
                if isinstance(m, str):
                    validated_metrics[m] = 'auto'
                elif (isinstance(m, tuple) or isinstance(m, list)) and len(m) == 2:
                    validated_metrics[m[0]] = m[1]
                else:
                    raise ValueError('Invalid metric, expected string or 2-tuple of strings')
        else:
            raise ValueError('Incompatible metrics input')

        for name, mode in validated_metrics.items():
            m = self.client.get_or_create_metric(name, mode)
            metric_lookup[name] = Metric(m['url'], m['name'], m['mode'])
        return metric_lookup

    def trial(self) -> Optional['Trial']:
        try:
            return Trial.from_worker_experiment(self.worker, self)
        except TooManyTrials:
            return None


class Worker:
    def __init__(self, name, server=KURO_SERVER):
        self.client = KuroClient(server=server)
        workers = self.client.list_workers()
        worker = None
        for w in workers:
            if w['name'] == name:
                worker = w

        if worker is None:
            cpu_data = cpuinfo.get_cpu_info()
            cpu_brand = cpu_data['brand'] if 'brand' in cpu_data else ''
            memory = psutil.virtual_memory().total / 1073741824
            gpus = json.dumps(get_gpu_list())
            worker = self.client.create_worker(name, cpu_brand, memory, gpus)

        self.name = worker['name']
        self.created_at = worker['created_at']
        self.active = worker['active']
        self.cpu_brand = worker['cpu_brand']
        self.memory = worker['memory']
        self.gpus = worker['gpus']
        self.url = worker['url']

    def experiment(self, group, identifier, hyper_parameters=None, metrics=None, n_trials=1) -> Experiment:
        return Experiment(
            self, group, identifier, hyper_parameters=hyper_parameters, metrics=metrics, n_trials=n_trials
        )


class Trial:
    def __init__(self):
        self.kuro_worker = None
        self.kuro_experiment = None
        self.client = None
        self.results = None
        self.url = None
        self.id = None
        self.worker = None
        self.experiment = None
        self.started_at = None
        self.complete = None

    def report_metric(self, name, value, step=None, mode=None):
        if name not in self.kuro_experiment.metrics:
            metric = self.kuro_experiment._init_metrics({name: mode})[name]
            self.kuro_experiment.metrics[name] = metric
        else:
            metric = self.kuro_experiment.metrics[name]

        self.client.create_result_value(self.url, metric.url, step, value)

    def end(self):
        self.client.trial_complete(self.url)

    @classmethod
    def from_worker_experiment(cls, worker: Worker, experiment: Experiment):
        trial = cls()
        trial.kuro_worker = worker
        trial.kuro_experiment = experiment
        trial.client = worker.client
        trial.results = defaultdict(list)

        trial_instance = trial.client.get_or_create_trial(worker.url, experiment.url)
        if 'error' in trial_instance and trial_instance['error'] == 'TooManyTrials':
            raise TooManyTrials()
        trial.url = trial_instance['url']
        trial.id = trial_instance['id']
        trial.worker = trial_instance['worker']
        trial.experiment = trial_instance['experiment']
        trial.started_at = trial_instance['started_at']
        trial.complete = trial_instance['complete']
        return trial

    @classmethod
    def from_trial_id(cls, trial_id):
        client = KuroClient()
        trial_instance = client.get_trial(trial_id)
        worker = Worker(trial_instance['worker']['name'])
        experiment_instance = trial_instance['experiment']
        experiment = Experiment(
            worker,
            experiment_instance['group'],
            experiment_instance['identifier'],
            hyper_parameters=json.loads(experiment_instance['hyper_parameters'])
        )

        trial = cls()
        trial.kuro_worker = worker
        trial.kuro_experiment = experiment
        trial.client = worker.client
        trial.results = defaultdict(list)
        trial.trial_instance = trial_instance
        trial.url = trial_instance['url']
        trial.id = trial_instance['id']
        trial.worker = trial_instance['worker']
        trial.experiment = trial_instance['experiment']
        trial.started_at = trial_instance['started_at']
        trial.complete = trial_instance['complete']

        return trial
