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

class Metric(models.Model):
    MAX = 'max'
    MIN = 'min'
    MODE_CHOICES = (
        (MAX, MAX),
        (MIN, MIN)
    )

    name = models.CharField(max_length=50, blank=False, unique=True)
    mode = models.CharField(max_length=20, blank=False, choices=MODE_CHOICES)


class Experiment(models.Model):
    group = models.CharField(max_length=100, blank=False)
    identifier = models.CharField(max_length=200, blank=False)
    hyper_parameters = JSONField(default=dict)
    metrics = models.ManyToManyField(Metric)
    n_trials = models.IntegerField(default=1)

    class Meta:
        ordering = ('group', 'identifier')
        unique_together = ('group', 'identifier', 'hyper_parameters')


class Trial(models.Model):
    worker = models.ForeignKey(Worker, models.CASCADE)
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ('experiment',)


class Result(models.Model):
    trial = models.ForeignKey(Trial, models.CASCADE)
    metric = models.ForeignKey(Metric, models.CASCADE)

    class Meta:
        ordering = ('trial', 'metric')


class ResultValue(models.Model):
    result = models.ForeignKey(Result, models.CASCADE)
    step = models.IntegerField(default=0)
    value = models.FloatField(blank=False)

    class Meta:
        unique_together = ('result', 'step')
