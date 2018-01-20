from typing import Dict
import json
import os
from collections import defaultdict, namedtuple

import coreapi
import cpuinfo
import psutil
from gpustat import GPUStatCollection


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


class KuroClient:
    def __init__(self, endpoint: str='http://localhost:8000'):
        self.schema_endpoint = os.path.join(endpoint, 'schema')
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

    def get_or_create_experiment(self, group, identifier, hyper_parameters, metrics: Dict[str, str], n_trials=1):
        pass

    def list_metrics(self, name=None):
        metrics = self.query(['metrics', 'list'])
        return [
            m for m in metrics if name is None or m['name'] == name
        ]

    def get_or_create_metric(self, name, mode=None):
        return self.query(['metrics', 'get-or-create', 'create'], params={'name': name, 'mode': mode})


class Experiment:
    def __init__(self, worker: 'Worker', group, identifier, hyper_parameters=None, metrics=None, n_trials=1):
        self.worker = worker
        self.client = worker.client
        self.group = group
        self.identifier = identifier
        if hyper_parameters is None:
            self.hyper_parameters = {}
        else:
            self.hyper_parameters = hyper_parameters

        self.n_trials = n_trials
        self.metrics = {}
        self._init_metrics(metrics)

    @staticmethod
    def insert_metric(validated_metrics, name, raw_mode):
        if raw_mode == 'auto':
            if 'acc' in name:
                mode = 'max'
            elif 'loss' in name:
                mode = 'min'
            else:
                raise ValueError(f'No default mode associated with metric "{name}"')
            validated_metrics[name] = mode
        elif raw_mode == 'max' or raw_mode == 'min':
            validated_metrics[name] = raw_mode
        else:
            raise ValueError(f'Invalid mode: {raw_mode}')

    def _init_metrics(self, metrics):
        validated_metrics = {}
        if isinstance(metrics, dict):
            for name, mode in metrics.items():
                self.insert_metric(validated_metrics, name, mode)
        elif isinstance(metrics, list) or isinstance(metrics, tuple):
            for m in metrics:
                if isinstance(m, str):
                    self.insert_metric(validated_metrics, m, 'auto')
                elif (isinstance(m, tuple) or isinstance(m, list)) and len(m) == 2:
                    self.insert_metric(validated_metrics, m[0], m[1])
                else:
                    raise ValueError('Invalid metric, expected string or 2-tuple of strings')
        else:
            raise ValueError('Incompatible metrics input')

        for name, mode in validated_metrics.items():
            m = self.client.get_or_create_metric(name, mode)
            self.metrics[name] = Metric(m['url'], m['name'], m['mode'])

    def trial(self) -> 'Trial':
        return Trial(self.worker, self)


class Worker:
    def __init__(self, name, endpoint='http://localhost:8000'):
        self.client = KuroClient(endpoint=endpoint)
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
            worker = self.client.create_worker(self.name, cpu_brand, memory, gpus)

        self.name = worker['name']
        self.created_at = worker['created_at']
        self.active = worker['active']
        self.cpu_brand = worker['cpu_brand']
        self.memory = worker['memory']
        self.gpus = worker['gpus']

    def experiment(self, group, identifier, hyper_parameters=None, metrics=None, n_trials=1) -> Experiment:
        return Experiment(
            self, group, identifier, hyper_parameters=hyper_parameters, metrics=metrics, n_trials=n_trials
        )


class Trial:
    def __init__(self, worker: Worker, experiment: Experiment):
        self.worker = worker
        self.experiment = experiment
        self.client = worker.client
        self.results = defaultdict(list)

    def report_metric(self, name, value, step=None, mode=None):
        if name in self.experiment.metrics:
            pass
        else:
            self.experiment._init_metrics({name: mode})

    def complete(self):
        pass
