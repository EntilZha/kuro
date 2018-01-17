from typing import Dict, Optional
from collections import defaultdict
from kuro.client.api import KuroClient



class KuroExperiment:
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
        else:
            self.metrics = {}
            for name, mode in metrics:
                self.metrics[name] = mode


class KuroWorker:
    def __init__(self, name, endpoint='http://localhost:8000'):
        self.name = name
        self.client = KuroClient(endpoint=endpoint)
        workers = self.client.list_workers()
        self.worker = None
        for w in workers:
            if w.name == name:
                self.worker = w
        if self.worker is None:
            self.worker = self.client.register_worker(self.name)

    def exit(self):
        # Mark worker as not-active, delete all incomplete trials
        pass


class KuroManager:
    def __init__(self, worker: KuroWorker, experiment: KuroExperiment):
        self.worker = worker
        self.experiment = experiment

    def trial(self):
        return KuroTrial(self.worker, self.experiment)

    def exit(self):
        # Mark worker as not-active, delete all incomplete trials
        pass


class KuroTrial:
    def __init__(self, worker: KuroWorker, experiment: KuroExperiment):
        self.worker = worker
        self.experiment = experiment
        self.results = defaultdict(list)

    def report_metric(self, name, value, step=None, mode=None):
        pass

    def complete(self):
        pass

worker = KuroWorker('nibel')
experiment = KuroExperiment(
    'guesser', 'qanta.guesser.dan.DanGuesser',
    metrics={'test_acc': 'max'},
    hyper_parameters={'lr': .001} # Used to group models together and compare them
)
manager = KuroManager(worker, experiment)

# Run 5 trials of same parameters
for _ in range(5):
    trial = manager.trial() # If worker doesn't have a trial for experiment make one, otherwise fetch it
    for step in range(10): # Steps can be epochs or batch steps etc
        acc, loss = 9 + step, -1 - step # Model results here from testing data
        trial.report_metric('test_acc', acc, step=step) # Explicitly pass step, no need for mode since it was passed in metrics
        trial.report_metric('test_loss', loss, mode='min') # Allow step to be auto-computed, need mode since its a new metric on first iteration

    trial.report_metric('final_metric', 98, mode='max') # similarly new metric needs mode
    trial.complete() # Mark trial as complete
manager.exit()
