from functools import wraps
import os
import threading
from datetime import timedelta
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import ContactMessage
from .forms import RegisterForm
from django.db.models import Avg, Count, Q, F
from .models import Cuisine, Recipe, RecipeIngredient

from .models import (
    Cart,
    CartItem,
    Category,
    DeliveryProfile,
    Order,
    OrderItem,
    Product,
    ProductImage,
    ProductReview,
    UserPocket,
    Wishlist,
    RecipeReview,
)


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


def about(request):
    fruits = ['Apple', 'Banana', 'Mango', 'Orange', 'Grapes']
    payload = {
        'fruits': fruits
    }
    return render(request, 'about.html', payload)


def services(request):
    return render(request, "services.html")


@login_required(login_url='login')
def bootstrap(request):
    return render(request, 'bootstrap.html')


@login_required(login_url='login')
def shop_view(request):
    categories = Category.objects.all()
    products_qs = Product.objects.all()

    # 1. Category Filter
    category_slug = request.GET.get('category')
    if category_slug:
        products_qs = products_qs.filter(categories__Category_slug=category_slug)

    # 2. Keyword Search (e.g., "sugar")
    query = request.GET.get('keywords')
    if query:
        products_qs = products_qs.filter(title__icontains=query)

    # 3. Price Filter Slider (max price)
    max_price = request.GET.get('max_price')
    if max_price:
        try:
            products_qs = products_qs.filter(price__lte=Decimal(max_price))
        except (ValueError, TypeError):
            pass

    # 4. Additional Filters (Organic, Fresh, Sales, Discount, Expired)
    additional_filter = request.GET.get('additional')
    today = timezone.now().date()

    if additional_filter == 'organic':
        products_qs = products_qs.filter(
            Q(admin_badge='ORGANIC') | 
            Q(admin_badge='AUTO', is_organic=True)
        )
    elif additional_filter == 'fresh':
        products_qs = products_qs.filter(
            Q(admin_badge='FRESH') | 
            Q(admin_badge='AUTO', expiry_date__isnull=True) | 
            Q(admin_badge='AUTO', expiry_date__gte=today)
        )
    elif additional_filter in ['sales', 'discount']:
        products_qs = products_qs.filter(
            Q(admin_badge='DISCOUNT') | 
            Q(admin_badge='AUTO', original_price__isnull=False, original_price__gt=F('price'))
        )
    elif additional_filter == 'expired':
        products_qs = products_qs.filter(
            Q(admin_badge='EXPIRED') | 
            Q(admin_badge='AUTO', expiry_date__isnull=False, expiry_date__lt=today)
        )

    # 5. Sorting Logic (Popularity based on customer reviews)
    sort_option = request.GET.get('sort')
    
    # Annotate with average rating and total reviews for popularity sorting
    products_qs = products_qs.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )

    if sort_option == 'popularity':
        # Sort by highest average rating first, then by review count
        products_qs = products_qs.order_by('-avg_rating', '-review_count', '-created_at')
    elif sort_option == 'organic':
        products_qs = products_qs.filter(is_organic=True).order_by('-created_at')
    elif sort_option == 'fantastic':
        products_qs = products_qs.order_by('-price')
    else:
        products_qs = products_qs.order_by('-created_at')

    # Cart quantity tracking
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

    # Wishlist IDs for favorited status tracking
    user_wishlist_ids = []
    if request.user.is_authenticated:
        user_wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    for product in products_qs:
        product.in_cart_qty = cart_quantities.get(product.id, 0)
        product.is_favorited = product.id in user_wishlist_ids

    # Pagination setup
    paginator = Paginator(products_qs, 9)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    context = {
        'categories': categories,
        'products': products,
        'cart_count': get_cart_count(request),
        'selected_max_price': max_price,
        'selected_additional': additional_filter,
        'selected_sort': sort_option,
        'search_query': query,
    }
    return render(request, 'shop.html', context)


@login_required(login_url='login')
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    
    cart = Cart.objects.filter(user=request.user).first()
    cart_quantities = {}
    if cart:
        cart_quantities = {item.product_id: item.quantity for item in CartItem.objects.filter(cart=cart)}

    for item in wishlist_items:
        item.product.in_cart_qty = cart_quantities.get(item.product.id, 0)
        item.product.is_favorited = True

    context = {
        'wishlist_items': wishlist_items,
        'cart_count': get_cart_count(request),
    }
    return render(request, 'wishlist.html', context)


@login_required(login_url='login')
def toggle_wishlist_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    
    if not created:
        wishlist_item.delete()
        messages.info(request, f"Removed {product.title} from your wishlist.")
    else:
        messages.success(request, f"Added {product.title} to your wishlist!")
        
    return redirect(request.META.get('HTTP_REFERER', 'shop_page'))


@login_required(login_url='login')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Read the requested quantity from the URL query parameter ?qty= (defaults to 1)
    try:
        add_qty = int(request.GET.get('qty', 1))
        if add_qty < 1:
            add_qty = 1
    except ValueError:
        add_qty = 1
    
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key, user=None)
    
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if created:
        cart_item.quantity = add_qty
    else:
        cart_item.quantity += add_qty  # Adds up when you click + or add again
    cart_item.save()
        
    messages.success(request, f"Added {add_qty} x {product.title} to your cart!")
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


def home(request):
    categories = Category.objects.all()
    products_qs = Product.objects.filter(is_active=True)[:8]

    vegetable_products = Product.objects.filter(
        is_active=True, 
        categories__Category_name__icontains='Fresh Produce'
    ).distinct()

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
    
    status_filter = request.GET.get('status')
    if status_filter:
        orders_list = orders_list.filter(status=status_filter)
        
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
                f"Your account has been successfully created, and you are all set to explore our platform."
            )
            from_email = "groceryguideai@gmail.com"
            recipient_list = [user.email]

            try:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
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


def mark_order_delivered(order):
    if order.status != 'Delivered':
        order.status = 'Delivered'
        order.delivered_at = timezone.now()
        order.save()
        
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


def delivery_required(view_func):
    """Restricts view execution exclusively to users with a valid DeliveryProfile."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to access this page.")
            return redirect('delivery_login')
            
        if not hasattr(request.user, 'delivery_profile'):
            messages.error(request, "Access denied. This area is strictly reserved for delivery personnel.")
            return redirect('home')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def assign_delivery_person(order):
    """Automatically assigns the first available delivery agent who is marked present today."""
    available_agent = DeliveryProfile.objects.filter(
        is_attended_today=True, 
        is_available=True
    ).first()

    if available_agent:
        order.delivery_person = available_agent.user
        order.status = 'On the way'
        order.save()

        available_agent.is_available = False
        available_agent.save()
        return True
    return False


def delivery_login_view(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'delivery_profile'):
            return redirect('delivery_dashboard')
        else:
            logout(request)

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            if hasattr(user, 'delivery_profile'):
                login(request, user)
                messages.success(request, f"Welcome back, Delivery Partner {user.username}!")
                return redirect('delivery_dashboard')
            else:
                messages.error(request, "Access Denied: This login portal is strictly for delivery personnel.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'delivery_login.html', {'form': form})


@delivery_required
def delivery_dashboard_view(request):
    profile = request.user.delivery_profile
    
    active_orders = Order.objects.filter(delivery_person=request.user, status='On the way').order_by('-created_at')
    completed_orders = Order.objects.filter(delivery_person=request.user, status='Delivered').order_by('-delivered_at')[:10]
    
    context = {
        'profile': profile,
        'active_orders': active_orders,
        'completed_orders': completed_orders,
        'cart_count': get_cart_count(request),
    }
    return render(request, 'delivery_dashboard.html', context)


@delivery_required
def toggle_attendance_view(request):
    profile = request.user.delivery_profile
    profile.is_attended_today = not profile.is_attended_today
    profile.save()
    
    if profile.is_attended_today:
        unassigned_order = Order.objects.filter(status='Pending', delivery_person__isnull=True).first()
        if unassigned_order:
            assign_delivery_person(unassigned_order)

    status_label = "Present & Active" if profile.is_attended_today else "Off Duty"
    messages.info(request, f"Attendance status updated: {status_label}")
    return redirect('delivery_dashboard')


@delivery_required
def confirm_delivery_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, delivery_person=request.user)
    
    if request.method == 'POST':
        proof_file = request.FILES.get('delivery_proof')
        if not proof_file:
            messages.error(request, "Please upload a photo proof of delivery!")
            return redirect('delivery_dashboard')
            
        order.delivery_proof = proof_file
        order.save()
        
        mark_order_delivered(order)

        profile = request.user.delivery_profile
        profile.is_available = True
        profile.save()

        next_order = Order.objects.filter(status='Pending', delivery_person__isnull=True).first()
        if next_order:
            assign_delivery_person(next_order)

        messages.success(request, f"Order #{order.id} delivered and rewards credited!")
        return redirect('delivery_dashboard')
        
    return redirect('delivery_dashboard')


@login_required(login_url='login')
def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        if name and email and message:
            ContactMessage.objects.create(name=name, email=email, message=message)
            messages.success(request, "Your message has been sent successfully!")
        else:
            messages.error(request, "Please fill out all fields.")
            
        return redirect('contact')
        
    context = {
        'cart_count': get_cart_count(request),
    }
    return render(request, 'contact.html', context)

@login_required(login_url='login')
def meal_guide_view(request):
    cuisines = Cuisine.objects.all()
    recipes = []
    
    selected_cuisine_id = request.GET.get('cuisine')
    selected_recipe_id = request.GET.get('recipe')
    selected_budget = request.GET.get('budget')
    
    try:
        servings = int(request.GET.get('servings', 1))
        if servings < 1:
            servings = 1
    except ValueError:
        servings = 1
    
    selected_recipe = None
    filtered_products = []
    total_cost = Decimal('0.00')
    recipe_in_budget = True

    if selected_cuisine_id:
        try:
            recipes = Recipe.objects.filter(cuisine_id=int(selected_cuisine_id))
        except ValueError:
            recipes = []

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

    if selected_recipe_id:
        try:
            selected_recipe = get_object_or_404(Recipe, id=int(selected_recipe_id))
            recipe_ingredients = RecipeIngredient.objects.filter(recipe=selected_recipe).select_related('product')

            product_list = []
            for ri in recipe_ingredients:
                prod = ri.product
                # Multiply required quantity by the user's selected servings count
                base_req_qty = Decimal(str(ri.required_quantity))
                req_qty = base_req_qty * Decimal(str(servings))
                unit = ri.unit_measure
                
                cart_multiplier = 1
                if unit in ['g', 'kg', 'pcs']:
                    pkg_qty = Decimal(str(prod.package_quantity)) if prod.package_quantity else Decimal('1.00')
                    if pkg_qty <= 0:
                        pkg_qty = Decimal('1.00')
                    multiplier = req_qty / pkg_qty
                    item_total_price = prod.price * multiplier
                    cart_multiplier = max(1, int(round(float(multiplier))))
                else:
                    item_total_price = prod.price * Decimal(str(servings))
                
                product_list.append({
                    'product': prod,
                    'required_qty': req_qty,
                    'unit_measure': ri.get_unit_measure_display(),
                    'store_measurement': prod.full_measurement,
                    'price': prod.price,
                    'item_total': item_total_price,
                    'cart_multiplier': cart_multiplier,
                    'in_cart_qty': cart_quantities.get(prod.id, 0)
                })

            filtered_products = product_list
            total_cost = sum(item['item_total'] for item in filtered_products)

            if selected_budget:
                try:
                    if '-' in selected_budget:
                        min_val, max_val = map(float, selected_budget.split('-'))
                        recipe_in_budget = min_val <= float(total_cost) <= max_val
                    elif '+' in selected_budget:
                        min_val = float(selected_budget.replace('+', ''))
                        recipe_in_budget = float(total_cost) >= min_val
                except ValueError:
                    recipe_in_budget = True

        except (ValueError, Recipe.DoesNotExist):
            selected_recipe = None

    recipe_reviews = selected_recipe.reviews.all().order_by('-created_at') if selected_recipe else []
    avg_rating = selected_recipe.reviews.aggregate(Avg('rating'))['rating__avg'] if selected_recipe else 0
    avg_rating = round(avg_rating, 1) if avg_rating else 0

    context = {
        'cuisines': cuisines,
        'recipes': recipes,
        'selected_cuisine_id': int(selected_cuisine_id) if selected_cuisine_id and selected_cuisine_id.isdigit() else None,
        'selected_recipe_id': int(selected_recipe_id) if selected_recipe_id and selected_recipe_id.isdigit() else None,
        'selected_recipe': selected_recipe if recipe_in_budget else selected_recipe,
        'filtered_products': filtered_products if recipe_in_budget else [],
        'selected_budget': selected_budget,
        'servings': servings,
        'total_cost': total_cost if recipe_in_budget else Decimal('0.00'),
        'recipe_in_budget': recipe_in_budget,
        'recipe_reviews': recipe_reviews,
        'avg_rating': avg_rating,
        'cart_count': get_cart_count(request) if 'get_cart_count' in globals() else 0,
    }
    return render(request, 'recipe_planner.html', context)
@login_required(login_url='login')
def add_all_recipe_to_cart(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    recipe_ingredients = RecipeIngredient.objects.filter(recipe=recipe).select_related('product')
    
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key, user=None)
        
    for ri in recipe_ingredients:
        prod = ri.product
        req_qty = Decimal(str(ri.required_quantity))
        unit = ri.unit_measure
        
        cart_multiplier = 1
        if unit in ['g', 'kg', 'pcs']:
            pkg_qty = Decimal(str(prod.package_quantity)) if prod.package_quantity else Decimal('1.00')
            if pkg_qty <= 0:
                pkg_qty = Decimal('1.00')
            multiplier = req_qty / pkg_qty
            cart_multiplier = max(1, int(round(float(multiplier))))
        
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=prod)
        if created:
            cart_item.quantity = cart_multiplier
        else:
            cart_item.quantity += cart_multiplier
        cart_item.save()
        
    messages.success(request, f"Successfully added all items for {recipe.title} to your cart!")
    return redirect(request.META.get('HTTP_REFERER', 'guide'))