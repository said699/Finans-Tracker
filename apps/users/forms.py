from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django import forms

User = get_user_model()

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, max_length=200, label="Email")
    phone = forms.CharField(required=True, label="Phone")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'phone')

class LoginForm(AuthenticationForm):
    pass