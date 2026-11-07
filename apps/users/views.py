from django.shortcuts import render
from django.views import generic
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from .forms import RegisterForm, LoginForm, UserUpdateForm
from django.urls import reverse_lazy
from .models import CustomUser
from django.contrib.auth.mixins import LoginRequiredMixin

class RegisterUserView(generic.CreateView):
    form_class = RegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('finans:home')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

class LoginUserView(LoginView):
    form_class = LoginForm
    template_name = 'users/login.html'
    success_url = reverse_lazy('finans:home')

class AccountDetails(generic.DetailView):
    model = CustomUser
    template_name = 'users/accdetail.html'
    context_object_name = 'user'

    def get_object(self):
        return self.request.user
        
class UpdateAccount(generic.UpdateView, LoginRequiredMixin):
    model = CustomUser
    form_class = UserUpdateForm
    template_name = 'users/profile_update.html'
    success_url = reverse_lazy('finans:home')

    def get_object(self):
        return self.request.user

class DeleteAccount(generic.DeleteView, LoginRequiredMixin):
    model = CustomUser
    success_url = reverse_lazy('users:register')

    def get_object(self, queryset=None):
        return self.request.user