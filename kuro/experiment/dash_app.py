import sys
from typing import Dict, List
from random import randint
from collections import defaultdict

from kuro.experiment.models import Experiment, Trial

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go


class MetricPlot:
    def __init__(self, trial_id, name, mode, values, steps):
        self.trial_id = trial_id
        self.name = name
        self.mode = mode
        self.values = values
        self.steps = steps

    def to_plot(self):
        return {
            'name': f'Trial {self.trial_id}',
            'mode': 'line',
            'type': 'scatter',
            'x': self.steps,
            'y': self.values
        }

    @staticmethod
    def to_figure(metric_plots):
        metric_name = metric_plots[0].name
        html_id = f'graph-metric-{metric_name}'
        return dcc.Graph(
        id=html_id,
        figure={
            'data': [m.to_plot() for m in metric_plots],
            'layout': {
                'title': f'Metric: {metric_name}',
                'showlegend': True,
                'xaxis': {'title': 'Step N'},
                'yaxis': {'title': metric_name}
            }
        }
    )


def dispatcher(request):
    '''
    Main function
    @param request: Request object
    '''

    app = _create_app()
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


def _create_app():
    ''' Creates dash application '''

    app = dash.Dash(csrf_protect=False)
    app.layout = html.Div(children=[
        dcc.Location(id='url', refresh=False),
        dcc.Link('Index', href='/dash-index'),
        ', ',
        dcc.Link('Figure 1', href='/dash-fig1'),
        ', ',
        dcc.Link('Figure 2', href='/dash-fig2'),
        html.Br(),
        html.Br(),
        html.Div(id='content')
    ])
    @app.callback(
        dash.dependencies.Output('content', 'children'),
        [dash.dependencies.Input('url', 'pathname')]
    )
    def display_page(pathname):
        ''' '''
        if not pathname:
            return ''
        if pathname == '/':
            return dash_index()
        method = pathname[1:].replace('-', '_')
        func = getattr(sys.modules[__name__], method, None)
        if func and func.__name__.startswith('dash'):
            return func()
        return 'Unknown link'
    return app


def dash_index():
    ''' '''
    return 'Welcome to index page'


def dash_fig1():
    experiment = Experiment.objects.filter(id=7).first()

    step_metric_data: Dict[str, List[MetricPlot]] = defaultdict(list)
    summary_metric_data: Dict[str, List[MetricPlot]] = defaultdict(list)

    for trial in experiment.trials.all():
        for r in trial.results.all():
            metric_name = r.metric.name
            metric_mode = r.metric.mode
            result_values = r.result_values.all()
            steps = [v.step for v in result_values]
            values = [v.value for v in result_values]
            if len(steps) == 1:
                summary_metric_data[metric_name].append(MetricPlot(trial.id, metric_name, metric_mode, values, steps))
            else:
                step_metric_data[metric_name].append(MetricPlot(trial.id, metric_name, metric_mode, values, steps))


    return html.Div(children=[
        MetricPlot.to_figure(plots)
        for plots in step_metric_data.values()
    ])


def dash_fig2():
    ''' '''
    return dcc.Graph(
        id='main-graph',
        figure={
            'data': [{
                'name': 'Some name',
                'mode': 'line',
                'line': {
                    'color': 'rgb(0, 0, 0)',
                    'opacity': 1
                },
                'type': 'scatter',
                'x': [randint(1, 100) for x in range(0, 20)],
                'y': [randint(1, 100) for x in range(0, 20)]
            }],
            'layout': {
                'autosize': True,
                'scene': {
                    'bgcolor': 'rgb(255, 255, 255)',
                    'xaxis': {
                        'titlefont': {'color': 'rgb(0, 0, 0)'},
                        'title': 'X-AXIS',
                        'color': 'rgb(0, 0, 0)'
                    },
                    'yaxis': {
                        'titlefont': {'color': 'rgb(0, 0, 0)'},
                        'title': 'Y-AXIS',
                        'color': 'rgb(0, 0, 0)'
                    }
                }
            }
        }
    )