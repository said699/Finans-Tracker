from django.shortcuts import render, get_object_or_404, redirect
from django.views import generic
from django.urls import reverse_lazy
from .forms import AddEarningCategoryForm, AddEarningForm
from .models import EarningCategory, Earnings
from django.contrib.auth.mixins import LoginRequiredMixin

class AddEarningView(generic.CreateView, LoginRequiredMixin):
    model = Earnings
    template_name = 'finans/add_earning.html'
    form_class = AddEarningForm
    success_url = reverse_lazy('finans:earnings')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class AddEarningCategoryView(generic.CreateView, LoginRequiredMixin):
    model = EarningCategory
    template_name = 'finans/add_earn_category.html'
    form_class = AddEarningCategoryForm
    success_url = reverse_lazy('finans:earnings')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)
    
    def get_queryset(self):
        return EarningCategory.objects.filter(user=self.request.user)

class EarningsView(generic.ListView, LoginRequiredMixin):
    model = Earnings
    template_name = 'finans/earnings.html'
    paginate_by = 10
    ordering = ['-date_done']
    context_object_name = 'earnings'

    def get_queryset(self):
        return Earnings.objects.filter(user=self.request.user).order_by('-date_done')

class EarningDetView(generic.DetailView, LoginRequiredMixin):
    model = Earnings
    template_name = 'finans/earning_detail.html'
    context_object_name = 'earning'

def earning_delete(request, pk):
    earning = get_object_or_404(Earnings, pk=pk, user=request.user)
    if request.method == 'POST':
        earning.delete()
        return redirect('finans:earnings')
    return redirect('finans:earnings')

class ListEarnCategory(generic.ListView, LoginRequiredMixin):
    model = EarningCategory
    template_name = 'finans/earn_category.html'
    context_object_name = 'earn_categories'

    def get_queryset(self):
        return EarningCategory.objects.filter(user=self.request.user)

def earn_category_delete(request, pk):
    earn_category = get_object_or_404(EarningCategory, pk=pk, user=request.user)
    if request.method == 'POST':
        earn_category.delete()
        return redirect('finans:earnings')
    return redirect('finans:earnings')