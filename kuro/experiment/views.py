import json
from django.contrib.auth.models import User, Group
from django.db import transaction

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from kuro.experiment.serializers import (
    UserSerializer, GroupSerializer, ExperimentSerializer,
    TrialSerializer, WorkerSerializer, MetricSerializer,
    ResultSerializer, ResultValueSerializer, MetricGetOrCreateSerializer,
ExperimentGetOrCreateSerializer
)
from kuro.experiment.models import (
    Experiment, Trial, Worker, Metric, Result, ResultValue
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class ExperimentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Experiment.objects.all()
    serializer_class = ExperimentSerializer


class TrialViewSet(viewsets.ModelViewSet):
    queryset = Trial.objects.all()
    serializer_class = TrialSerializer


class WorkerViewSet(viewsets.ModelViewSet):
    queryset = Worker.objects.all()
    serializer_class = WorkerSerializer


class MetricViewSet(viewsets.ModelViewSet):
    queryset = Metric.objects.all()
    serializer_class = MetricSerializer


class MetricGetOrCreateViewSet(viewsets.GenericViewSet):
    serializer_class = MetricGetOrCreateSerializer

    @staticmethod
    def infer_mode(name):
        if 'acc' in name:
            return 'max'
        elif 'loss' in name:
            return 'min'
        else:
            raise ValidationError(f'mode could not be inferred from the name:"{name}"')

    @transaction.atomic
    def create(self, request):
        validated_metric = MetricGetOrCreateSerializer(data=request.data)
        if validated_metric.is_valid():
            name = validated_metric.data['name']
            mode = validated_metric.data['mode']
            metric = Metric.objects.filter(name=name).first()
            if metric is None:
                if mode == 'auto':
                    mode = MetricGetOrCreateViewSet.infer_mode(name)
                metric_serializer = MetricSerializer(data={'name': name, 'mode': mode}, context={'request': request})
                if metric_serializer.is_valid():
                    metric_serializer.save()
                    return Response(metric_serializer.data)
                else:
                    return Response(metric_serializer.errors, status=400)
            else:
                if mode is not None and mode != 'auto' and metric.mode != mode:
                    return Response(
                        data={'errors': f'Metric with name={name} exists but with mode={metric.mode} instead of the given mode={mode}'},
                        status=400
                    )
                else:
                    return Response(MetricSerializer(metric, context={'request': request}).data)
        else:
            return Response(validated_metric.errors, status=400)


class ExperimentGetOrCreateViewSet(viewsets.GenericViewSet):
    serializer_class = ExperimentGetOrCreateSerializer

    @transaction.atomic
    def create(self, request):
        validated_experiment = ExperimentGetOrCreateSerializer(data=request.data, context={'request': request})
        if validated_experiment.is_valid():
            data = validated_experiment.validated_data
            group = data['group']
            identifier = data['identifier']
            hyper_parameters = data['hyper_parameters']
            metrics = data['metrics']
            n_trials = data['n_trials']

            str_hyper_parameters = json.dumps(hyper_parameters, sort_keys=True)
            experiment = Experiment.objects.filter(
                group=group,
                identifier=identifier,
                hyper_parameters=str_hyper_parameters
            ).first()
            if experiment is None:
                if n_trials is None:
                    del data['n_trials']
                data['hyper_parameters'] = str_hyper_parameters

                experiment_serializer = ExperimentSerializer(data=data, context={'request': request})
                if experiment_serializer.is_valid():
                    experiment_serializer.save()
                    return Response(experiment_serializer.data)
                else:
                    return Response(experiment_serializer.errors, status=400)
            else:
                if n_trials is not None:
                    experiment.n_trials = n_trials
                if metrics is not None:
                    for m in metrics:
                        experiment.metrics.add(m)
                experiment.save()
                return Response(ExperimentSerializer(experiment, context={'request': request}).data)
        else:
            return Response(validated_experiment.errors, status=400)


class ResultViewSet(viewsets.ModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer


class ResultValueViewSet(viewsets.ModelViewSet):
    queryset = ResultValue.objects.all()
    serializer_class = ResultValueSerializer
