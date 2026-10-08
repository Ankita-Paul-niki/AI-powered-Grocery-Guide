from django.urls import path
from core import views

urlpatterns = [
    # Main Landing Pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about_page'),
    path('service/', views.services, name='service_page'),
    path('contact/', views.contact, name='contact_page'),
    path('bootstrap/', views.bootstrap, name='bootstrap'),

    # Authentication System Pages
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
