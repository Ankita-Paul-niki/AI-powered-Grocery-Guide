from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email Address")
    first_name = forms.CharField(max_length=100, required=False, label="Full Name")

    class Meta:
        model = User
        fields = ('username', 'first_name', 'email')