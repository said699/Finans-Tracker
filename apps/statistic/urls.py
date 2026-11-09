from django.urls import path
from .views import statistics

app_name = 'statistic'

urlpatterns = [
    path("stats/", statistics, name="statistics"),
]