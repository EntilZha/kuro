from typing import Dict, List, Tuple
from collections import defaultdict

from kuro.web.models import Experiment

import numpy as np

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


class MetricSeries:
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
        Output('experiment-select-div', 'children'),
        [Input('interval-component', 'n_intervals'), Input('group-select', 'value')]
    )
    def update_experiment_div(n_intervals, group):
        return create_experiment_div(group)

    @app.callback(
        Output('content', 'children'),
        [Input('interval-component', 'n_intervals'), Input('experiment-select', 'values'), Input('aggregate-mode', 'value')]
    )
    def update_experiment_plot(n_intervals, experiment_ids, aggregate_mode):
        if len(experiment_ids) == 0:
            return html.H5('No Experiments Selected')
        experiment_ids = [int(exp_id) for exp_id in experiment_ids]
        step_metric_data, summary_metric_data = create_metric_series(experiment_ids)
        return html.Div(children=[
            experiment_table(summary_metric_data, step_metric_data),
            plot_experiments(step_metric_data, aggregate_mode)
        ])

    return app


def create_experiment_div(group):
    experiments = Experiment.objects.filter(group=group)
    experiment_checkbox = dcc.Checklist(
        id='experiment-select',
        options=[{'label': str(exp), 'value': exp.id} for exp in experiments],
        values=[exp.id for exp in experiments]
    )
    return html.Div(children=[
        html.H5('Experiment Select'),
        experiment_checkbox
    ])

dashboard_info_text = '''
### Kuro Dashboard Guide

* One experiment `group` can be selected at a time. For example `guesser` experiments
* Each group can have any number of experiments
* Each experiment is represented by its unique grouping of group, identifier (name), and json serialized hyper parameters
* Each experiment can have one more more trials which represent a single run of that experiment and its parameters
* Each trial can have one or more metrics such as accuracy, loss, etc.
* Each metric can be time series (eg accuracy over epochs), or a single "summary" metric.
* Each time series metric has its best value (min or max) displayed in the table of trials
* Trial Aggregate Mode controls how trials are displayed: all of them, the trial with the best metric at any point in the series, or the mean of each metric at each time step
'''


def index():
    info = dcc.Markdown(dashboard_info_text)
    groups = {e[0] for e in Experiment.objects.values_list('group')}
    if len(groups) == 0:
        groups = {'empty'}
        initial_group = 'empty'
    else:
        initial_group = next(iter(groups))

    group_selector = html.Div(children=[
        html.H5('Group Selector'),
        html.Div(children='There are no experiments and thus no groups, please add some' if initial_group =='empty' else ''),
        dcc.RadioItems(
            id='group-select',
            options=[{'label': g, 'value': g} for g in groups],
            value=initial_group
        )
    ])
    experiment_checkbox = html.Div(id='experiment-select-div', children=create_experiment_div(initial_group))
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
        dcc.Interval(id='interval-component', interval=30 * 1000, n_intervals=0),
        info,
        group_selector,
        aggregate_mode,
        experiment_checkbox,
        html.Div(id='content')
    ])
    return page


MetricData = Dict[Tuple[int, str], List[MetricSeries]]


def create_metric_series(experiment_ids):
    step_metric_data: MetricData = defaultdict(list)
    summary_metric_data: MetricData = defaultdict(list)

    for experiment in Experiment.objects.filter(id__in=experiment_ids):
        for trial in experiment.trials.all():
            for r in trial.results.all():
                metric_name = r.metric.name
                metric_mode = r.metric.mode
                result_values = r.result_values.all()
                steps = [v.step for v in result_values]
                values = [v.value for v in result_values]
                if len(steps) == 1:
                    summary_metric_data[(experiment.id, metric_name)].append(MetricSeries(
                        experiment.id, trial.id, metric_name, metric_mode, values, steps
                    ))
                else:
                    step_metric_data[(experiment.id, metric_name)].append(MetricSeries(
                        experiment.id, trial.id, metric_name, metric_mode, values, steps
                    ))

    return step_metric_data, summary_metric_data


def extract_metric_series_value(metric: MetricSeries):
    if len(metric.values) == 1:
        return metric.values[0]
    elif len(metric.values) == 0:
        raise ValueError('Missing metric values')
    else:
        if metric.mode == 'max':
            return max(metric.values)
        elif metric.mode == 'min':
            return min(metric.values)
        else:
            raise ValueError('Invalid mode, must be max or min')


def experiment_table(summary_metric_data: MetricData, step_metric_data: MetricData):
    exp_trial_lookup = defaultdict(list)
    for ms_list in summary_metric_data.values():
        for ms in ms_list:
            exp_trial_lookup[(ms.experiment_id, ms.trial_id)].append(ms)

    for ms_list in step_metric_data.values():
        for ms in ms_list:
            exp_trial_lookup[(ms.experiment_id, ms.trial_id)].append(ms)

    for key in exp_trial_lookup.keys():
        exp_trial_lookup[key].sort(key=lambda ms: ms.name)

    metric_names = [ms.name for ms in next(iter(exp_trial_lookup.values()))]

    table = html.Table(
        [html.Tr([html.Th('Experiment'), html.Th('Trial')] + [html.Th(col) for col in metric_names])] +
        [html.Tr(
            [html.Td(ms_list[0].experiment_id), html.Td(ms_list[0].trial_id)] +
            [html.Td(extract_metric_series_value(ms)) for ms in ms_list]
        ) for ms_list in exp_trial_lookup.values()]
    )
    return html.Div(children=[html.H5('Summary Metrics'), table])


def plot_experiments(step_metric_data, aggregate_mode, experiment_same_plot=True):
    if experiment_same_plot:
        plot_lookup = defaultdict(list)
        for metric_plot_list in step_metric_data.values():
            for metric_plot in metric_plot_list:
                plot_lookup[metric_plot.name].append(metric_plot)
        plots = [MetricSeries.to_figure(plots, aggregate_mode=aggregate_mode) for plots in plot_lookup.values()]
    else:
        plots = [MetricSeries.to_figure(plots, aggregate_mode=aggregate_mode) for plots in step_metric_data.values()]
    return html.Div(children=plots)
