"""kuro URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls import url, include
from rest_framework import routers
from rest_framework.schemas import get_schema_view
from kuro.experiment import views


router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)
router.register(r'experiments/get-or-create', views.ExperimentGetOrCreateViewSet, base_name='experiment')
router.register(r'experiments', views.ExperimentViewSet)
router.register(r'workers', views.WorkerViewSet)
router.register(r'trials/get-or-create', views.TrialGetOrCreateViewSet, base_name='trial')
router.register(r'trials/complete', views.TrialCompleteViewSet, base_name='trial')
router.register(r'trials', views.TrialViewSet)
router.register(r'results', views.ResultViewSet)
router.register(r'result_values/report', views.ResultValueCreateViewSet, base_name='result_value')
router.register(r'result_values', views.ResultValueViewSet)
router.register(r'metrics/get-or-create', views.MetricGetOrCreateViewSet, base_name='metric')
router.register(r'metrics', views.MetricViewSet)

schema_view = get_schema_view(title='Kuro API')

urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^schema/$', schema_view),
    url(r'^api/v1.0/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^dash-', views.dash),
    url(r'^_dash', views.dash_ajax)
]
