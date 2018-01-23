from kuro import Worker
import random


def main():
    worker = Worker('nibel')
    experiment = worker.experiment(
        'guesser', 'qanta.guesser.dan.DanGuesser',
        metrics=[('test_acc', 'max'), 'test_loss'],
        hyper_parameters={'lr': .001, 'dropout': .5},
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
    main()