from typing import Dict
import json
import os
from collections import defaultdict

import coreapi
import cpuinfo
import psutil
from gpustat import GPUStatCollection


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
    def __init__(self, endpoint: str):
        self.schema_endpoint = os.path.join(endpoint, 'schema')
        self.client = coreapi.Client()
        self.schema = self.client.get(self.schema_endpoint)

    def list_workers(self):
        return self.client.action(self.schema, ['workers', 'list'])

    def register_worker(self, name, cpu_brand, memory, gpus):
        return self.client.action(
            self.schema,
            ['workers', 'create'],
            params={'name': name, 'cpu_brand': cpu_brand, 'memory': memory, 'gpus': gpus, 'active': True}
        )

    def get_or_create_experiment(self, group, identifier, hyper_parameters, metrics: Dict[str, str], n_trials=1):
        pass


class Experiment:
    def __init__(self, group, identifier, hyper_parameters=None, metrics=None, n_trials=1):
        self.group = group
        self.identifier = identifier
        if hyper_parameters is None:
            self.hyper_parameters = {}
        else:
            self.hyper_parameters = hyper_parameters

        self.n_trials = n_trials

        if metrics is None:
            self.metrics = {}
        elif isinstance(metrics, dict):
            self.metrics = metrics
        elif isinstance(metrics, list):
            self.metrics = {}
            for name, mode in metrics:
                self.metrics[name] = mode


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
            worker = self.client.register_worker(self.name, cpu_brand, memory, gpus)

        self.name = worker['name']
        self.created_at = worker['created_at']
        self.active = worker['active']
        self.cpu_brand = worker['cpu_brand']
        self.memory = worker['memory']
        self.gpus = worker['gpus']


class Manager:
    def __init__(self, worker: Worker, experiment: Experiment):
        self.worker = worker
        self.experiment = experiment

    def trial(self):
        return Trial(self.worker, self.experiment)

    def exit(self):
        # Mark worker as not-active, delete all incomplete trials
        pass


class Trial:
    def __init__(self, worker: Worker, experiment: Experiment):
        self.worker = worker
        self.experiment = experiment
        self.results = defaultdict(list)

    def report_metric(self, name, value, step=None, mode=None):
        pass

    def complete(self):
        pass
