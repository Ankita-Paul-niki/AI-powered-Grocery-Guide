from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .forms import RegisterForm
from .models import Product,Category
from core.models import *
import os
from django.core.paginator import Paginator
from .models import Product, Category, Cart, CartItem
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
import threading
from .models import Order, UserPocket
from .models import ProductReview
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
@login_required(login_url='login')
def bootstrap(request):
    return render(request, 'bootstrap.html')
@login_required(login_url='login')
def shop_view(request):
    categories = Category.objects.all()
    products_qs = Product.objects.all()

    # 1. Apply Category filter (using Category_slug from your model)
    category_slug = request.GET.get('category')
    if category_slug:
        products_qs = products_qs.filter(categories__Category_slug=category_slug)

    # 2. Apply Search keyword filter
    query = request.GET.get('keywords')
    if query:
        products_qs = products_qs.filter(title__icontains=query)

    # 3. Retrieve current cart for logged-in user or guest session
    cart = None
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    elif request.session.session_key:
        cart = Cart.objects.filter(session_key=request.session.session_key, user=None).first()

    # 4. Map product IDs to their current cart quantities
    cart_quantities = {}
    if cart:
        cart_quantities = {
            item.product_id: item.quantity 
            for item in CartItem.objects.filter(cart=cart)
        }

    # 5. Attach in_cart_qty attribute to each product in queryset
    for product in products_qs:
        product.in_cart_qty = cart_quantities.get(product.id, 0)

    # 6. Apply Django Paginator (9 items per page)
    paginator = Paginator(products_qs, 9)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    context = {
        'categories': categories,
        'products': products,
        'cart_count': get_cart_count(request)
    }
    return render(request, 'shop.html', context)
@login_required(login_url='login')
def add_to_cart(request, product_id):
    product = Product.objects.get(id=product_id)
    
    # Get or create cart for logged-in user or session
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key, user=None)
    
    # Get or create cart item
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
        
    messages.success(request, f"Added {product.title} to your cart!")
    return redirect(request.META.get('HTTP_REFERER', 'shop_page'))
@login_required(login_url='login')
def remove_from_cart(request, product_id):
    product = Product.objects.get(id=product_id)
    
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key, user=None).first()
        
    if cart:
        cart_item = CartItem.objects.filter(cart=cart, product=product).first()
        if cart_item:
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
                
    messages.info(request, f"Updated cart for {product.title}")
    return redirect(request.META.get('HTTP_REFERER', 'shop_page'))
@login_required(login_url='login')
def get_user_cart(request):
    """Helper function to retrieve or create the active cart."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart
@login_required(login_url='login')
def cart_view(request):
    cart = get_user_cart(request)
    cart_items = CartItem.objects.filter(cart=cart).select_related('product')
    discount = Decimal('0.00')
    shipping_fee = Decimal('0.00')
    subtotal = sum(item.total_price for item in cart_items)

    if not cart_items:
        shipping_fee = Decimal('0.00')
    # FIXED: Checked in descending order (highest to lowest) so larger tiers match properly
    elif subtotal >= Decimal('999.00'):
        shipping_fee = Decimal('0.00')
        discount = subtotal * Decimal('0.20')
    elif subtotal >= Decimal('499.00'):
        shipping_fee = Decimal('0.00')
        discount = subtotal * Decimal('0.10')
    elif subtotal >= Decimal('100.00'):
        shipping_fee = Decimal('0.00')
        discount = subtotal * Decimal('0.05')
    else:
        shipping_fee = Decimal('30.00')
        
    total = subtotal - discount + shipping_fee    

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'discount': discount,
        'total': total,
        'cart_count': get_cart_count(request)
    }
    return render(request, 'cart.html', context)
@login_required(login_url='login')
def delete_cart_item(request, item_id):
    cart = get_user_cart(request)
    cart_item = CartItem.objects.filter(cart=cart, id=item_id).first()
    if cart_item:
        cart_item.delete()
        messages.info(request, "Item removed from cart.")
    return redirect('cart_page')

def get_cart_count(request):
    """Helper to get total item quantity in the current user's cart."""
    cart = None
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    elif request.session.session_key:
        cart = Cart.objects.filter(session_key=request.session.session_key, user=None).first()
    
    if cart:
        return sum(item.quantity for item in cart.items.all())
    return 0

def home(request):
    categories = Category.objects.all()
    products_qs = Product.objects.filter(is_active=True)[:8]

    # Fetch products belonging to the 'Fresh Produce' category
    vegetable_products = Product.objects.filter(
        is_active=True, 
        categories__Category_name__icontains='Fresh Produce'
    ).distinct()

    # Get active cart for quantity tracking
    cart = None
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    elif request.session.session_key:
        cart = Cart.objects.filter(session_key=request.session.session_key, user=None).first()

    cart_quantities = {}
    if cart:
        cart_quantities = {
            item.product_id: item.quantity 
            for item in CartItem.objects.filter(cart=cart)
        }

    # Attach cart quantities to products
    for product in list(products_qs) + list(vegetable_products):
        product.in_cart_qty = cart_quantities.get(product.id, 0)

    context = {
        'categories': categories,
        'products': products_qs,
        'vegetable_products': vegetable_products,
        'cart_count': get_cart_count(request),
    }
    return render(request, 'bootstrap.html', context)
@login_required(login_url='login')
def orders_view(request):
    orders_list = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by status if selected
    status_filter = request.GET.get('status')
    if status_filter:
        orders_list = orders_list.filter(status=status_filter)
        
    # Search query
    query = request.GET.get('q')
    if query:
        orders_list = orders_list.filter(items__product__title__icontains=query).distinct()

    context = {
        'orders': orders_list,
        'selected_status': status_filter,
        'cart_count': get_cart_count(request),
    }
    return render(request, 'orders.html', context)
def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserPocket.objects.get_or_create(user=user)
            subject = 'Welcome to Grocery Guide!'
            message = (
                f"Hello {user.first_name or user.username},\n\n"
                f"Welcome to Grocery Guide!\n"
                f"Your account has been successfully created. You can now explore grocery recommendations, produce tips, and seasonal guides.\n\n"
                f"Best regards,\nThe Grocery Guide Team"
            )
            from_email="groceryguideai@gmail.com"
            recipient_list = [user.email]

            try:
                send_mail(
                    subject,
                    message,
                    from_email,
                    recipient_list,
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Error sending email: {e}")

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
def credit_reward_after_delay(order_id):
    """Wait 2 seconds after delivery, check if returned, then credit pockets."""
    import time
    time.sleep(2)
    try:
        order = Order.objects.get(id=order_id)
        # Verify order is still delivered and not returned/cancelled
        if order.status == 'Delivered' and not order.is_returned and not order.return_requested and not order.is_reward_credited:
            total_reward = sum(item.product.reward_pocket_amount * item.quantity for item in order.items.all())
            
            if total_reward > 0:
                pocket, created = UserPocket.objects.get_or_create(user=order.user)
                pocket.balance += total_reward
                pocket.save()
                
                order.is_reward_credited = True
                order.save()
    except Order.DoesNotExist:
        pass

# 1. Order Cancellation Policy (Within 1 minute)
@login_required(login_url='login')
def cancel_order_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    time_diff = timezone.now() - order.created_at
    
    if time_diff <= timedelta(minutes=1) and order.status == 'Pending':
        order.status = 'Cancelled'
        order.save()
        messages.success(request, "Order successfully cancelled within the 1-minute window.")
    else:
        messages.error(request, "Cancellation window of 1 minute has expired.")
    return redirect('orders_page')

# 2. Return Policy Request (Within 5 hours of delivery)
@login_required(login_url='login')
def request_return_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status == 'Delivered' and order.delivered_at:
        delivery_time_diff = timezone.now() - order.delivered_at
        if delivery_time_diff <= timedelta(hours=5):
            order.return_requested = True
            order.save()
            messages.success(request, "Return request registered successfully within the 5-hour window.")
        else:
            messages.error(request, "The 5-hour return window after delivery has expired.")
    else:
        messages.error(request, "Return is only available for successfully delivered items.")
    return redirect('orders_page')

# 3. Admin / System action when marking order as Delivered
def mark_order_delivered(order):
    if order.status != 'Delivered':
        order.status = 'Delivered'
        order.delivered_at = timezone.now()
        order.save()
        
        # Trigger background thread for 2-second automatic reward crediting
        threading.Thread(target=credit_reward_after_delay, args=(order.id,)).start()
def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug)
    reviews = product.reviews.all().order_by('-created_at')
    
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to leave a review.")
            return redirect('login')
            
        rating = request.POST.get('rating', 5)
        comment = request.POST.get('comment')
        if comment:
            ProductReview.objects.create(
                product=product,
                user=request.user,
                rating=rating,
                comment=comment
            )
            messages.success(request, "Your review has been submitted successfully!")
            return redirect('product_detail', slug=product.slug)

    context = {
        'product': product,
        'reviews': reviews,
        'cart_count': get_cart_count(request)
    }
    return render(request, 'product_detail.html', context)
@login_required(login_url='login')
def pocket_view(request):
    pocket, created = UserPocket.objects.get_or_create(user=request.user)
    context = {
        'pocket': pocket,
        'cart_count': get_cart_count(request),
    }
    return render(request, 'pocket.html', context)