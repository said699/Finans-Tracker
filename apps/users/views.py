from django.shortcuts import render
from django.views import generic
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from .forms import RegisterForm, LoginForm
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin

class RegisterUserView(generic.CreateView):
    form_class = RegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

class LoginUserView(LoginView):
    form_class = LoginForm
    template_name = 'users/login.html'

class HomeView(generic.TemplateView, LoginRequiredMixin):
    template_name = 'users/home.html'

