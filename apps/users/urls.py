from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import RegisterUserView, HomeView, LoginUserView

urlpatterns = [
    path('register/', RegisterUserView.as_view(), name='register'),
    path('login/', LoginUserView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('home', HomeView.as_view(), name='home'),
]