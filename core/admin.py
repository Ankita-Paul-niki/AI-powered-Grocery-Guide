from django.contrib import admin
from .models import Category, Product, ProductImage, Cart, CartItem, Order, OrderItem, UserPocket
from .models import ProductReview
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3  # Provides 3 empty image upload slots by default

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('Category_name', 'Category_created_at')
    search_fields = ('Category_name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'price','original_price', 'stock', 'package_quantity', 'package_unit', 'reward_pocket_amount', 'is_active')
    list_filter = ('package_unit', 'is_active', 'categories')
    search_fields = ('title', 'description')
    filter_horizontal = ('categories',)
    inlines = [ProductImageInline]

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'created_at')
    search_fields = ('user__username', 'session_key')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'quantity', 'total_price')
    list_filter = ('product',)
    search_fields = ('cart__user__username', 'product__title')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_price', 'status', 'return_requested', 'is_reward_credited', 'created_at')
    list_filter = ('status', 'return_requested', 'is_reward_credited', 'created_at')
    search_fields = ('user__username', 'first_name', 'last_name', 'email', 'phone')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'price', 'quantity')
    list_filter = ('product',)
    search_fields = ('order__id', 'order__user__username', 'product__title')

@admin.register(UserPocket)
class UserPocketAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'balance')
    search_fields = ('user__username', 'user__email')
@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('product__title', 'user__username', 'comment')
