from django.contrib.auth.models import User, Group
from kuro.experiment.models import (
    Experiment, Worker, Trial, Metric, Result, ResultValue
)
from rest_framework import serializers


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')


class ExperimentSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Experiment
        fields = ('url', 'group', 'identifier', 'hyper_parameters', 'metrics', 'n_trials')
        depth = 1


class TrialSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Trial
        fields = ('url', 'worker', 'experiment', 'started_at', 'complete')


class WorkerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Worker
        fields = ('url', 'name', 'created_at', 'active', 'cpu_brand', 'memory', 'gpus')


class MetricSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Metric
        fields = ('url', 'name', 'mode')


class TrialCompleteSerializer(serializers.Serializer):
    trial = serializers.HyperlinkedRelatedField(
        queryset=Trial.objects.all(),
        view_name='trial-detail',
        required=True
    )


class TrialGetOrCreateSerializer(serializers.Serializer):
    worker = serializers.HyperlinkedRelatedField(
        queryset=Worker.objects.all(),
        view_name='worker-detail',
        required=True
    )
    experiment = serializers.HyperlinkedRelatedField(
        queryset=Experiment.objects.all(),
        view_name='experiment-detail',
        required=True
    )


class MetricGetOrCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50, allow_null=False, allow_blank=False, required=True)
    mode = serializers.CharField(max_length=20, allow_null=True, allow_blank=True, required=False)


class ExperimentGetOrCreateSerializer(serializers.Serializer):
    group = serializers.CharField(max_length=100, required=True, allow_blank=False)
    identifier = serializers.CharField(max_length=200, required=True, allow_blank=False)
    hyper_parameters = serializers.JSONField(required=False, default=dict)
    metrics = serializers.HyperlinkedRelatedField(
        queryset= Metric.objects.all(),
        many=True,
        view_name='metric-detail',
        required=False,
        default=list
    )
    n_trials = serializers.IntegerField(required=False, default=None)


class ResultSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Result
        fields = ('url', 'trial', 'metric')


class ResultValueSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ResultValue
        fields = ('url', 'result', 'step', 'value')
        depth = 1


class ResultValueCreateSerializer(serializers.Serializer):
    trial = serializers.HyperlinkedRelatedField(
        required=True,
        queryset=Trial.objects.all(),
        view_name='trial-detail'
    )
    metric = serializers.HyperlinkedRelatedField(
        required=True,
        queryset=Metric.objects.all(),
        view_name='metric-detail'
    )
    step = serializers.IntegerField(required=True)
    value = serializers.FloatField(required=True)