from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .forms import RegisterForm

# Create your views here.

def about(request):
    fruits = ['Apple', 'Banana', 'Mango', 'Orange', 'Grapes']
    payload = {
        'fruits': fruits
    }
    return render(request, 'about.html', payload)

def services(request):
    return render(request, "services.html")

def contact(request):
    return render(request, "contact.html")

def bootstrap(request):
    return render(request, 'bootstrap.html')

# This is your main home view template loader
def home(request):
    return render(request, 'bootstrap.html')

def register_view(request):
    # If they are already logged in, send them away from the signup page
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # 1. Send the Welcome Email
            subject = 'Welcome to Grocery Guide!'
            message = (
                f"Hello {user.first_name or user.username},\n\n"
                f"Welcome to Grocery Guide!\n"
                f"Your account has been successfully created. You can now explore grocery recommendations, produce tips, and seasonal guides.\n\n"
                f"Best regards,\nThe Grocery Guide Team"
            )
            recipient_list = [user.email]

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_list,
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Error sending email: {e}")

            # 2. Inform user and send them directly to the Login page instead of auto-logging in
            messages.success(request, f"Account created successfully for {user.username}! Please login below.")
            return redirect('login')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')
