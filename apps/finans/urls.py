from django.urls import path
from .views import HistoryPaymentView, AddPaymentView

urlpatterns = [
    path('history/', HistoryPaymentView.as_view(), name='history_payment'),
    path('add/', AddPaymentView.as_view(), name='add_payment'),
]