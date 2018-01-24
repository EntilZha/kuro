# kuro

Kuro is a python-based experiment management system developed by [Pedro Rodriguez](https://pedrorodriguez.io), a PhD Candidate in
machine learning at University of Maryland, College Park.

Kuro is focused on:

* Providing a client library that can be used from experiment code to log metrics such as accuracy and loss.
* Providing a django web application to store information sent from the client library.
* Providing a [Dash](https://plot.ly/products/dash/) app that visualizes the results of experiments.

This is all aimed at making it easy to:
* Collect results from experiments running on heterogenous resources (local workstations, university computing clusters, AWS etc) to one central server
* Be agnostic to the learning library used (PyTorch, SKLearn, Tensorflow etc)
* Analyze these results with the goal of:
    * Comparing many hyper parameter settings
    * Collecting results for multiple trials of the same hyper parameter settings
    * Handling either time series data (accuracy by epoch) or summary data (best accuracy)
    * Analyze either with a web visualization based on Dash, or raw JSON data for scripts (eg scripts converting data to publication ready plots)

Below is a sample of what using the client library looks like from `demo.py`:

Start the kuro server

```bash
$ python manage.py migrate
$ python manage.py runserver
```

Run a dummy experiment

```python
from kuro import Worker
import random


def run(guesser_name, hyper_parameters):
    worker = Worker('nibel')
    experiment = worker.experiment(
        'guesser', guesser_name,
        metrics=[('test_acc', 'max'), 'test_loss'],
        hyper_parameters=hyper_parameters,
        n_trials=3# Used to group models together and compare them
    )

    # Run 5 trials of same parameters
    for _ in range(5):
        trial = experiment.trial() # If worker doesn't have a trial for experiment make one, otherwise fetch it
        # If there is nothing more to run, skip running a trial
        if trial is None:
            continue
        for step in range(10): # Steps can be epochs or batch steps etc
            acc, loss = 9 + step, -1 - step # Model results here from testing data
            trial.report_metric('test_acc', acc + random.uniform(0, 5), step=step) # Explicitly pass step, no need for mode since it was passed in metrics
            trial.report_metric('test_loss', loss + random.uniform(0, 10), step=step) # For common things such as loss/accuracy, these are automatically inferred if not given
            trial.report_metric('optimality', 0, mode='min', step=step)# Allow step to be auto-computed, need mode since its a new metric on first iteration

        trial.report_metric('final_metric', 98 + random.uniform(-3, 0), mode='max') # similarly new metric needs mode
        trial.report_metric('final_nums', 93 + random.uniform(-10, 10), mode='min')
        trial.report_metric('final_digits', random.randint(0, 100), mode='min')
        trial.end() # Mark trial as complete


if __name__ == '__main__':
    run('qanta.guesser.dan.DanGuesser', {'lr': .001, 'dropout': .5})
    run('qanta.guesser.rnn.RnnGuesser', {'lr': .1, 'dropout': .1})
```

The results are in dashboard at `http://localhost:8000/dash-index`

![Dashboard Top Half](https://imgur.com/download/hWGog4L)

![Dashboard Bottom half](https://imgur.com/download/pUq5RPH)

At some point in the future, the following features are planned

* Central server maintaining queue of work, and Workers being able to request work from the central server
* Paired with this feature would be automatic hyper parameter tuning
