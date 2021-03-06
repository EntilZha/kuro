from typing import Dict, List, Tuple
import json
from collections import defaultdict
from functional import seq

from kuro.web.models import Experiment

import numpy as np

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dt


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
    def __init__(self, identifier, experiment_id, trial_id, name, mode, values, steps):
        self.identifier = identifier
        self.experiment_id = experiment_id
        self.trial_id = trial_id
        self.name = name
        self.mode = mode
        self.values = values
        self.steps = steps

    def to_json(self):
        return {
            'identifier': self.identifier,
            'experiment_id': self.experiment_id,
            'trial_id': self.trial_id,
            'name': self.name,
            'mode': self.mode,
            'values': self.values,
            'steps': self.steps
        }

    @classmethod
    def from_json(cls, json_obj):
        return MetricSeries(
            json_obj['identifier'],
            json_obj['experiment_id'],
            json_obj['trial_id'],
            json_obj['name'],
            json_obj['mode'],
            json_obj['values'],
            json_obj['steps']
        )


    def to_plot(self, name=None, y=None):
        return {
            'name': f'{self.identifier}, Exp {self.experiment_id}, Trial {self.trial_id}' if name is None else name,
            'mode': 'lines+markers',
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
        [
            Input('aggregate-mode', 'value'),
            Input('update-tables-plots', 'n_clicks'),
            Input('interval-component', 'n_intervals')
        ],
        [State('experiment-detail-table', 'rows'), State('experiment-detail-table', 'selected_row_indices')]
    )
    def update_experiment_plot(aggregate_mode, n_clicks, n_intervals, exp_rows, exp_selected_rows):
        if exp_selected_rows is None:
            exp_selected_rows = []
        selected_experiments = []
        for i in exp_selected_rows:
            selected_experiments.append(exp_rows[i])
        if len(selected_experiments) == 0:
            return html.H5('No Experiments Selected')
        experiment_ids = [int(exp['id']) for exp in selected_experiments]
        step_metric_data, summary_metric_data = create_metric_series(experiment_ids)
        return html.Div(plot_experiments(step_metric_data, aggregate_mode))

    @app.callback(
        Output('experiment-trials-json', 'children'),
        [
            Input('aggregate-mode', 'value'),
            Input('update-tables-plots', 'n_clicks'), Input('interval-component', 'n_intervals')
        ],
        [State('experiment-detail-table', 'rows'), State('experiment-detail-table', 'selected_row_indices')]
    )
    def update_experiment_trials_json(aggregate_mode, n_clicks, n_intervals, exp_rows, exp_selected_rows):
        if exp_selected_rows is None:
            exp_selected_rows = []
        selected_experiments = []
        for i in exp_selected_rows:
            selected_experiments.append(exp_rows[i])
        experiment_ids = [int(exp['id']) for exp in selected_experiments]
        step_metric_data, summary_metric_data = create_metric_series(experiment_ids)
        json_step_data = {json.dumps(key): [v.to_json() for v in value] for key, value in step_metric_data.items()}
        json_summary_data = {json.dumps(key): [v.to_json() for v in value] for key, value in summary_metric_data.items()}
        return json.dumps([json_step_data, json_summary_data])

    @app.callback(
        Output('experiment-trials-table', 'rows'),
        [
            Input('experiment-trials-json', 'children'),
        ]
    )
    def update_experiment_trials_table(metric_json):
        step_metric_data, summary_metric_data = load_json_metrics(metric_json)
        return experiment_table(summary_metric_data, step_metric_data)

    @app.callback(
        Output('experiment-aggregate-trials-table', 'rows'),
        [Input('experiment-trials-json', 'children'), Input('metric-name-filter', 'value')]
    )
    def update_experiment_aggregate_trials_table(metric_json, metric_name_filter):
        if metric_json == '':
            return []
        step_metric_data, summary_metric_data = load_json_metrics(metric_json)
        metric_statistics, metric_names = compute_experiment_aggregate_rows(step_metric_data, summary_metric_data)
        rows = []
        for exp_id, metric_dict in metric_statistics.items():
            for name in metric_names:
                if metric_name_filter is None or metric_name_filter in name:
                    r = {'experiment_id': exp_id, 'metric': name}
                    if name in metric_dict:
                        m_mean, m_max, m_std = metric_dict[name]
                        r['avg'] = m_mean
                        r['max'] = m_max
                        r['std'] = m_std
                        rows.append(r)

        return rows

    @app.callback(
        Output('experiment-aggregate-trials-plots', 'children'),
        [Input('experiment-aggregate-trials-table', 'rows')]
    )
    def update_experiment_aggregate_trials_plots(rows):
        metric_names = {r['metric'] for r in rows}
        if len(metric_names) == 0:
            return ''
        figures = []
        for m_name in metric_names:
            plots = []
            m_rows = [r for r in rows if r['metric'] == m_name]
            x = [r['experiment_id'] for r in m_rows]
            y_max = [r['max'] for r in m_rows]
            y_std = [r['std'] for r in m_rows]
            y_avg = [r['avg'] for r in m_rows]

            for i in range(len(x)):
                p = {
                    'name': x[i],
                    'type': 'bar',
                    'x': ['max', 'avg'],
                    'y': [y_max[i], y_avg[i]],
                    'text': [x[i], x[i]],
                    'textposition': 'auto',
                    'error_y': {
                        'type': 'data',
                        'array': [y_std[i], y_std[i]],
                        'visible': True
                    }
                }
                plots.append(p)

            def sort_key(p):
                return p['y'][0]
            plots.sort(key=sort_key, reverse=True)


            figures.append(dcc.Graph(
                id=f'experiment-aggregate-trials-plots-figure-{m_name}',
                figure={
                    'data': plots,
                    'layout': {
                        'title': f'Metric: {m_name}',
                        'showlegend': True,
                        'barmode': 'group'
                    }
                })
            )
        return figures

    @app.callback(
        Output('interval-component', 'interval'),
        [Input('refresh-interval', 'value')]
    )
    def update_refresh_mode(refresh_interval):
        return refresh_interval * 1000

    return app


MetricDataLookup = Dict[Tuple[int, str], List[MetricSeries]]


def compute_experiment_aggregate_rows(step_metric_data, summary_metric_data):
    metric_statistics = defaultdict(dict)
    metric_names = set()

    for (experiment_id, metric_name), val in step_metric_data.items():
        metric_statistics[experiment_id][metric_name] = compute_experiment_statistics(val)
        metric_names.add(metric_name)

    for (experiment_id, metric_name), val in summary_metric_data.items():
        metric_statistics[experiment_id][metric_name] = compute_experiment_statistics(val)
        metric_names.add(metric_name)

    return metric_statistics, metric_names


def load_json_metrics(metric_json) -> Tuple[MetricDataLookup, MetricDataLookup]:
    json_step_metric_data, json_summary_metric_data = json.loads(metric_json)
    step_metric_data = {
        tuple(json.loads(key)): [MetricSeries.from_json(v) for v in value] for key, value in json_step_metric_data.items()
    }
    summary_metric_data = {
        tuple(json.loads(key)): [MetricSeries.from_json(v) for v in value] for key, value in json_summary_metric_data.items()
    }
    return step_metric_data, summary_metric_data

def compute_experiment_statistics(trial_metric_series: List[MetricSeries]):
    values = []
    for ms in trial_metric_series:
        if len(ms.values) == 0:
            continue
        elif len(ms.values) == 1:
            values.append(ms.values[0])
        else:
            if ms.mode == 'max':
                values.append(max(ms.values))
            elif ms.mode == 'min':
                values.append(min(ms.values))
            else:
                raise ValueError(f'Invalid mode {ms.mode}')
    return np.mean(values), np.max(values), np.std(values)

def filter_dictionaries(dictionaries):
    all_kvs = []
    for curr_dict in dictionaries:
        dict_kvs = set()
        for key, value in curr_dict.items():
            try:
                dict_kvs.add((key, value))
            except TypeError:
                pass
        all_kvs.append(dict_kvs)

    common_kvs = set.intersection(*all_kvs)

    filtered_dictionaries = []
    for curr_dict in dictionaries:
        new_dict = {}
        for key, value in curr_dict.items():
            try:
                if (key, value) not in common_kvs:
                    new_dict[key] = value
            except TypeError:
                new_dict[key] = value
        filtered_dictionaries.append(new_dict)
    return filtered_dictionaries


def create_experiment_detail_table(group):
    all_experiments = Experiment.objects.filter(group=group)
    grouped_experiments = seq(all_experiments).group_by(lambda e: e.identifier)
    rows = []
    for identifier, experiments in grouped_experiments:
        experiments = list(experiments)
        hp_dictionaries = [json.loads(e.hyper_parameters) for e in experiments]
        filtered_hp_dictionaries = filter_dictionaries(hp_dictionaries)
        for e, hp_dict in zip(experiments, filtered_hp_dictionaries):
            rows.append({
                'identifier': e.identifier,
                'id': e.id,
                'hyper_parameters': json.dumps(hp_dict)
            })

    return dt.DataTable(
        rows=rows, id='experiment-detail-table',
        row_selectable=True, filterable=True, sortable=True, enable_drag_and_drop=False, editable=False,
        columns=['identifier', 'id', 'hyper_parameters'],
        column_widths=[100, 50, None],
        min_height=1000
    )

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

    options_style = {
        'display': 'inline-block',
        'margin-left': '20px',
        'margin-right': '20px',
        'margin-bottom': '20px',
        'vertical-align': 'top'
    }

    auto_refresh_toggle = html.Div([
        html.H5('Auto Refresh Toggle'),
        dcc.RadioItems(
            id='refresh-interval', options=[
            {'label': '60s', 'value': 60},
            {'label': '5m', 'value': 60 * 5},
            {'label': 'off', 'value': 60 * 60 * 24}
        ],
        value=60 * 60 * 24
    )], style=options_style)

    group_selector = html.Div(children=[
        html.H5('Group Selector'),
        dcc.RadioItems(
            id='group-select',
            options=[{'label': g, 'value': g} for g in groups],
            value=initial_group
        )
    ], style=options_style)

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
    ], style=options_style)

    experiment_detail_table = html.Div(
        id='experiment-detail-div',
        children=create_experiment_detail_table(initial_group)
    )

    experiment_trials_table = dt.DataTable(
        rows=[{}], id='experiment-trials-table',
        selected_row_indices=[],
        row_selectable=True, filterable=True, sortable=True, enable_drag_and_drop=False, editable=False,
        min_height=1000
    )

    experiment_trials_json = html.Div(id='experiment-trials-json', style={'display': 'none'})
    experiment_aggregate_trials_table = dt.DataTable(
        rows=[{}], id='experiment-aggregate-trials-table',
        selected_row_indices=[],
        row_selectable=True, filterable=True, sortable=True, enable_drag_and_drop=False, editable=False,
        min_height=1000
    )
    experiment_trials_div = html.Div(
        id='experiment-trials-json',
        children=[
            experiment_trials_json,
            html.H5('All Trials'),
            experiment_trials_table,
            html.H5('Aggregated Trials'),
            html.Label('Metric Name Filter'),
            dcc.Input(id='metric-name-filter'),
            experiment_aggregate_trials_table,
            html.Div(id='experiment-aggregate-trials-plots')
        ]
    )
    page = html.Div(children=[
        dcc.Interval(id='interval-component', interval=30 * 1000, n_intervals=0),
        info,
        html.Div([auto_refresh_toggle, group_selector, aggregate_mode]),
        html.H5('Experiment Summary'),
        html.Button('Update Tables and Plots', id='update-tables-plots'),
        experiment_detail_table,
        experiment_trials_div,
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
                        experiment.identifier, experiment.id, trial.id, metric_name, metric_mode, values, steps
                    ))
                else:
                    step_metric_data[(experiment.id, metric_name)].append(MetricSeries(
                        experiment.identifier, experiment.id, trial.id, metric_name, metric_mode, values, steps
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
    metric_names = set()
    for ms_list in summary_metric_data.values():
        for ms in ms_list:
            metric_names.add(ms.name)

    for ms_list in step_metric_data.values():
        for ms in ms_list:
            metric_names.add(ms.name)

    exp_trial_lookup = defaultdict(dict)
    for ms_list in summary_metric_data.values():
        for ms in ms_list:
            exp_trial_lookup[(ms.experiment_id, ms.trial_id)][ms.name] = ms
    for ms_list in step_metric_data.values():
        for ms in ms_list:
            exp_trial_lookup[(ms.experiment_id, ms.trial_id)][ms.name] = ms

    rows = []
    for (experiment_id, trial_id), metric_dict in exp_trial_lookup.items():
        r = {'experiment_id': experiment_id, 'trial_id': trial_id}
        for name in metric_names:
            if name in metric_dict:
                r[name] = extract_metric_series_value(metric_dict[name])
            else:
                r[name] = None
        rows.append(r)

    return rows


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
