from django.shortcuts import render, get_object_or_404, redirect
from django.views import generic
from django.urls import reverse_lazy
from .forms import AddPaymentForm, AddCategoryForm
from .models import PayCategory, Payment
from django.contrib.auth.mixins import LoginRequiredMixin


class AddCategoryView(generic.CreateView, LoginRequiredMixin):
    model = PayCategory
    template_name = 'finans/addcategory.html'
    form_class = AddCategoryForm
    success_url = reverse_lazy('finans:home')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_queryset(self):
        return PayCategory.objects.filter(user=self.request.user)

class AddPaymentView(generic.CreateView, LoginRequiredMixin):
    model = Payment
    form_class = AddPaymentForm
    template_name = 'finans/addpayment.html'
    success_url = reverse_lazy('finans:home')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class HomeHistoryView(generic.ListView, LoginRequiredMixin):
    model = Payment
    template_name = 'finans/home.html'
    paginate_by = 10
    ordering = ['-date_done']
    context_object_name = 'payments'

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).order_by('-date_done')

class PaymentDetView(generic.DetailView, LoginRequiredMixin):
    model = Payment
    template_name = 'finans/paymentdet.html'
    context_object_name = 'payment'

def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk, user=request.user)
    if request.method == 'POST':
        payment.delete()
        return redirect('finans:home')
    return redirect('finans:home')

class ListCategory(generic.ListView, LoginRequiredMixin):
    model = PayCategory
    template_name = 'finans/category.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return PayCategory.objects.filter(user=self.request.user)

def category_delete(request, pk):
    category = get_object_or_404(PayCategory, pk=pk, user=request.user)
    if request.method == 'POST':
        category.delete()
        return redirect('finans:home')
    return redirect('finans:home')

