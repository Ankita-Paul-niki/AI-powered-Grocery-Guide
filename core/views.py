from django.shortcuts import render
from django.http import HttpResponse

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .forms import RegisterForm

# Create your views here.

def home(request):
    site_title="Welcome to Grocery Guide"
    site_description="This is your assistant for all your grocery needs. Find the best products, recipes, and tips just by entering your budget and recipe name. Our app will provide you with a list of ingredients and their prices, so you can make informed decisions and save money on your grocery shopping."
    site_image="https://hips.hearstapps.com/hmg-prod/images/online-buying-and-delivery-concept-royalty-free-image-1675370119.jpg?crop=0.563xw:1.00xh;0.216xw,0&resize=640:*"
    payload = {
        'site_title': site_title,   
        'site_description': site_description,
        'site_image': site_image    
    }
 
    
    return render(request, 'home.html', payload)

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







def home(request):
    return render(request, 'bootstrap.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()

            # 1. Log the user in right away
            login(request, user)

            # 2. Send the Welcome Email
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

            messages.success(request, f"Welcome to Grocery Guide, {user.username}!")
            return redirect('home')
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