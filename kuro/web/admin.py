from django.contrib import admin
from kuro.web.models import Worker, Metric, Experiment, Trial, Result, ResultValue


class WorkerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'active', 'created_at', 'cpu_brand', 'memory', 'gpus')


class MetricAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'mode')


class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'identifier', 'n_trials', 'hyper_parameters')
    ordering = ('-id',)


class TrialAdmin(admin.ModelAdmin):
    list_display = ('id', 'complete', 'worker', 'experiment', 'started_at')
    ordering = ('-id',)


class ResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'trial', 'metric')


class ResultValueAdmin(admin.ModelAdmin):
    list_display = ('id', 'result', 'step', 'value')


admin.site.register(Worker, WorkerAdmin)
admin.site.register(Metric, MetricAdmin)
admin.site.register(Experiment, ExperimentAdmin)
admin.site.register(Trial, TrialAdmin)
admin.site.register(Result, ResultAdmin)
admin.site.register(ResultValue, ResultValueAdmin)
