from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import RegisterUserView, LoginUserView

app_name = 'users'

urlpatterns = [
    path('register/', RegisterUserView.as_view(), name='register'),
    path('login/', LoginUserView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='users:login'), name='logout'),
]