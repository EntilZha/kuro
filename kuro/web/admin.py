from django.contrib import admin
from django.utils.safestring import mark_safe
import json
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import HtmlFormatter
from kuro.web.models import Worker, Metric, Experiment, Trial, Result, ResultValue


class WorkerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'active', 'created_at', 'cpu_brand', 'memory', 'gpus')


class MetricAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'mode')


class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'identifier', 'n_trials', 'pretty_hyper_parameters')
    ordering = ('-id',)

    readonly_fields = ('pretty_hyper_parameters',)

    def pretty_hyper_parameters(self, instance):
        """Function to display pretty version of our data"""

        # Convert the data to sorted, indented JSON
        response = json.dumps(json.loads(instance.hyper_parameters), sort_keys=True, indent=2)

        # Truncate the data. Alter as needed
        response = response[:5000]

        # Get the Pygments formatter
        formatter = HtmlFormatter(style='colorful')

        # Highlight the data
        response = highlight(response, JsonLexer(), formatter)

        # Get the stylesheet
        style = "<style>" + formatter.get_style_defs() + "</style><br>"

        # Safe the output
        return mark_safe(style + response)


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
