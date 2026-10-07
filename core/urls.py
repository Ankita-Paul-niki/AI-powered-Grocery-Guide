from ensurepip import bootstrap

from django.urls import path
from .views import *
from core import views



urlpatterns = [
    #path('', home, name="home_page"),
    path('about/', about, name="about_page"),
    path('service/', services, name="service_page"),
    path('contact/', contact, name="contact_page"),
    path('bootstrap/', bootstrap, name="bootstrap"),

    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]