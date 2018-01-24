from django.db import models
from jsonfield import JSONField


def gpus_default():
    return {
        'gpus': []
    }


class Worker(models.Model):
    name = models.CharField(max_length=100, blank=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=False)
    cpu_brand = models.CharField(max_length=200, default='')
    memory = models.FloatField(default=0)
    gpus = JSONField(default=gpus_default)

    def __str__(self):
        return f'Worker(name="{self.name}" active="{self.active}")'

class Metric(models.Model):
    MAX = 'max'
    MIN = 'min'
    MODE_CHOICES = (
        (MAX, MAX),
        (MIN, MIN)
    )

    name = models.CharField(max_length=50, blank=False, unique=True)
    mode = models.CharField(max_length=20, blank=False, choices=MODE_CHOICES)

    def __str__(self):
        return f'Metric(name="{self.name}" mode="{self.mode}")'


class Experiment(models.Model):
    group = models.CharField(max_length=100, blank=False)
    identifier = models.CharField(max_length=200, blank=False)
    hyper_parameters = JSONField(default=dict)
    metrics = models.ManyToManyField(Metric, blank=True)
    n_trials = models.IntegerField(default=1)


    def __str__(self):
        return f'Experiment(id="{self.id}" group="{self.group}" identifier="{self.identifier}" hyper_parameters="{self.hyper_parameters}")'

    class Meta:
        unique_together = ('group', 'identifier', 'hyper_parameters')


class Trial(models.Model):
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='trials')
    started_at = models.DateTimeField(auto_now_add=True)
    complete = models.BooleanField(default=False)

    class Meta:
        ordering = ('id', )

    def __str__(self):
        return f'Trial(worker="{self.worker}", experiment="{self.experiment}" started_at="{self.started_at}" complete="{self.complete}")'


class Result(models.Model):
    trial = models.ForeignKey(Trial, on_delete=models.CASCADE, related_name='results')
    metric = models.ForeignKey(Metric, on_delete=models.CASCADE, related_name='results')

    def __str__(self):
        return f'Result(trial="{self.trial}" metric="{self.metric}")'


class ResultValue(models.Model):
    result = models.ForeignKey(Result, on_delete=models.CASCADE, related_name='result_values')
    step = models.IntegerField(default=0)
    value = models.FloatField(blank=False)

    def __str__(self):
        return f'ResultValue(result="{self.result}" step="{self.step}" value="{self.value}")'

    class Meta:
        unique_together = ('result', 'step')
        ordering = ('result', 'step')
