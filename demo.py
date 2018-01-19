from kuro import Worker, Experiment, Manager


def main():
    worker = Worker('nibel')
    experiment = Experiment(
        'guesser', 'qanta.guesser.dan.DanGuesser',
        metrics={'test_acc': 'max'},
        hyper_parameters={'lr': .001} # Used to group models together and compare them
    )
    manager = Manager(worker, experiment)

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


if __name__ == '__main__':
    main()