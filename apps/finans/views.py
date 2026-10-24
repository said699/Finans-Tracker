from django.shortcuts import render
from django.views import generic
from .forms import AddPaymentForm
from .models import PayCategory, Payment
from django.contrib.auth.mixins import LoginRequiredMixin

class AddPaymentView(generic.CreateView, LoginRequiredMixin):
    model = Payment
    form_class = AddPaymentForm
    template_name = 'finans/addpayment.html'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class HistoryPaymentView(generic.ListView, LoginRequiredMixin):
    model = Payment
    template_name = 'finans/historypayment.html'
    paginate_by = 10
    ordering = ['-date_done']

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)