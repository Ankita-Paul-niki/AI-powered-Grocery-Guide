from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static
from . import views
urlpatterns = [
    # Main Landing Pages
    path('', views.home, name='home'),
    path('shop/', views.shop_view, name='shop_page'),
    path('about/', views.about, name='about_page'),
    path('service/', views.services, name='service_page'),
    path('contact/', views.contact, name='contact_page'),
    path('bootstrap/', views.bootstrap, name='bootstrap'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart_view, name='cart_page'),
    path('cart/delete/<int:item_id>/', views.delete_cart_item, name='delete_cart_item'),
    path('orders/', views.orders_view, name='orders_page'),
    path('orders/cancel/<int:order_id>/', views.cancel_order_view, name='cancel_order'),
    path('orders/return/<int:order_id>/', views.request_return_view, name='request_return'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('pocket/', views.pocket_view, name='pocket_page'),
    # Authentication System Pages
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)