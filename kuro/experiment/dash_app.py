from typing import Dict, List, Tuple
from collections import defaultdict

import numpy as np

from kuro.experiment.models import Experiment

import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html


def dispatcher(request):
    '''
    Main function
    @param request: Request object
    '''

    app = create_app()
    app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})
    params = {
        'data': request.body,
        'method': request.method,
        'content_type': request.content_type
    }
    with app.server.test_request_context(request.path, **params):
        app.server.preprocess_request()
        try:
            response = app.server.full_dispatch_request()
        except Exception as e:
            response = app.server.make_response(app.server.handle_exception(e))
        return response.get_data()


class MetricPlot:
    def __init__(self, experiment_id, trial_id, name, mode, values, steps):
        self.experiment_id = experiment_id
        self.trial_id = trial_id
        self.name = name
        self.mode = mode
        self.values = values
        self.steps = steps

    def to_plot(self, name=None, y=None):
        return {
            'name': f'Experiment {self.experiment_id}, Trial {self.trial_id}' if name is None else name,
            'mode': 'line',
            'type': 'scatter',
            'x': self.steps,
            'y': self.values if y is None else y
        }

    @staticmethod
    def to_figure(metric_plots, aggregate_mode='all'):
        metric_name = metric_plots[0].name
        experiment_id = metric_plots[0].experiment_id
        html_id = f'graph-experiment-{experiment_id}-metric-{metric_name}'
        if aggregate_mode == 'all':
            data = [m.to_plot() for m in metric_plots]
        elif aggregate_mode == 'max' or aggregate_mode == 'avg':
            experiment_plots = defaultdict(list)
            for m in metric_plots:
                experiment_plots[m.experiment_id].append(m)
            data = []
            if aggregate_mode == 'max':
                for exp_metric_plots in experiment_plots.values():
                    series_max = [max(m.values) for m in exp_metric_plots]
                    best_idx = np.argmax(series_max)
                    best_plot = exp_metric_plots[best_idx].to_plot()
                    data.append(best_plot)
            else:
                for exp_metric_plots in experiment_plots.values():
                    stacked_series = np.vstack([m.values for m in exp_metric_plots])
                    data.append(exp_metric_plots[0].to_plot(name='Trial Average', y=stacked_series.mean(axis=0)))
        else:
            raise ValueError('Invalid aggregate mode')

        graph = dcc.Graph(
            id=html_id,
            figure={
                'data': data,
                'layout': {
                    'title': f'Metric: {metric_name}',
                    'showlegend': True,
                    'xaxis': {'title': 'Step N'},
                    'yaxis': {'title': metric_name}
                }
            }
        )

        return graph


def create_app():
    app = dash.Dash(csrf_protect=False)
    app.layout = index()
    app.title = 'Kuro Dashboard'


    @app.callback(
        Output('content', 'children'),
        [Input('experiment-select', 'values'), Input('aggregate-mode', 'value')]
    )
    def update_experiment_plot(experiment_ids, aggregate_mode):
        return plot_experiments([int(exp_id) for exp_id in experiment_ids], aggregate_mode)
    return app


def index():
    experiments = Experiment.objects.all()
    experiment_checkbox = html.Div(children=[
        html.H5('Experiment Select'),
        dcc.Checklist(
        id='experiment-select',
        options=[{'label': str(exp), 'value': exp.id} for exp in experiments],
        values=[experiments[0].id]
        )
    ])
    aggregate_mode = html.Div(children=[
        html.H5('Trial Aggregate Mode'),
        dcc.RadioItems(
            id='aggregate-mode',
            options=[
                {'label': 'all', 'value': 'all'},
                {'label': 'max', 'value': 'max'},
                {'label': 'average', 'value': 'avg'}
            ],
            value='all'
        )
    ])
    page = html.Div(children=[
        aggregate_mode,
        experiment_checkbox,
        html.Div(id='content')
    ])
    return page


def plot_experiments(experiment_ids, aggregate_mode, experiment_same_plot=True):
    step_metric_data: Dict[Tuple[int, str], List[MetricPlot]] = defaultdict(list)
    summary_metric_data: Dict[Tuple[int, str], List[MetricPlot]] = defaultdict(list)

    for experiment in Experiment.objects.filter(id__in=experiment_ids):
        for trial in experiment.trials.all():
            for r in trial.results.all():
                metric_name = r.metric.name
                metric_mode = r.metric.mode
                result_values = r.result_values.all()
                steps = [v.step for v in result_values]
                values = [v.value for v in result_values]
                if len(steps) == 1:
                    summary_metric_data[(experiment.id, metric_name)].append(MetricPlot(
                        experiment.id, trial.id, metric_name, metric_mode, values, steps
                    ))
                else:
                    step_metric_data[(experiment.id, metric_name)].append(MetricPlot(
                        experiment.id, trial.id, metric_name, metric_mode, values, steps
                    ))

    if experiment_same_plot:
        plot_lookup = defaultdict(list)
        for metric_plot_list in step_metric_data.values():
            for metric_plot in metric_plot_list:
                plot_lookup[metric_plot.name].append(metric_plot)
        plots = [MetricPlot.to_figure(plots, aggregate_mode=aggregate_mode) for plots in plot_lookup.values()]
    else:
        plots = [MetricPlot.to_figure(plots, aggregate_mode=aggregate_mode) for plots in step_metric_data.values()]
    return html.Div(children=plots)
