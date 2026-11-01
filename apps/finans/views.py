from django.shortcuts import render
from django.views import generic
from .forms import AddPaymentForm, AddCategoryForm
from .models import PayCategory, Payment
from django.contrib.auth.mixins import LoginRequiredMixin


class AddCategoryView(generic.CreateView, LoginRequiredMixin):
    model = PayCategory
    template_name = 'finans/addcategory.html'
    form_class = AddCategoryForm
    success_url = 'http://127.0.0.1:8000/acc/home/'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_queryset(self):
        return PayCategory.objects.filter(user=self.request.user)

class AddPaymentView(generic.CreateView, LoginRequiredMixin):
    model = Payment
    form_class = AddPaymentForm
    template_name = 'finans/addpayment.html'
    success_url = 'http://127.0.0.1:8000/finans/home/'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class HomeHistoryView(generic.ListView, LoginRequiredMixin):
    model = Payment
    template_name = 'finans/home.html'
    paginate_by = 10
    ordering = ['-date_done']
    context_object_name = 'payments'

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)

class PaymentDetView(generic.DetailView, LoginRequiredMixin):
    model = Payment
    template_name = 'finans/paymentdet.html'
    context_object_name = 'payment'

