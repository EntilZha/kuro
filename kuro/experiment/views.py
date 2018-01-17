from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from kuro.experiment.serializers import (
    UserSerializer, GroupSerializer, ExperimentSerializer,
    TrialSerializer, WorkerSerializer, MetricSerializer,
    ResultSerializer, ResultValueSerializer
)
from kuro.experiment.models import (
    Experiment, Trial, Worker, Metric, Result, ResultValue
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class ExperimentViewSet(viewsets.ModelViewSet):
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


class ResultViewSet(viewsets.ModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer


class ResultValueViewSet(viewsets.ModelViewSet):
    queryset = ResultValue.objects.all()
    serializer_class = ResultValueSerializer