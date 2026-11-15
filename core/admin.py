from django.contrib import admin
from .models import (
    Category, 
    Product, 
    ProductImage, 
    Cart, 
    CartItem, 
    Order, 
    OrderItem, 
    UserPocket, 
    ProductReview, 
    DeliveryProfile,
    ContactMessage,
    Wishlist,
    Cuisine,       
    Recipe,        
    RecipeIngredient,
    RecipeReview 
)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3  # Provides 3 empty image upload slots by default

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('Category_name', 'Category_created_at')
    search_fields = ('Category_name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'original_price', 'stock', 'package_quantity', 'package_unit', 'admin_badge', 'is_active')
    list_filter = ('admin_badge', 'is_organic', 'package_unit', 'is_active', 'categories')
    search_fields = ('title', 'description')
    list_editable = ('admin_badge',) # Allows changing badges directly from the list table
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
    list_display = ('id', 'user', 'total_price', 'status', 'delivery_person', 'return_requested', 'is_reward_credited', 'created_at')
    list_filter = ('status', 'delivery_person', 'return_requested', 'is_reward_credited', 'created_at')
    search_fields = ('user__username', 'first_name', 'last_name', 'email', 'phone')
    list_editable = ('status', 'delivery_person')
    readonly_fields = ('created_at', 'delivered_at')

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

@admin.register(DeliveryProfile)
class DeliveryProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_attended_today', 'is_available')
    list_filter = ('is_attended_today', 'is_available')
    search_fields = ('user__username', 'user__email')

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('created_at',)
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product', 'created_at')
    search_fields = ('user__username', 'product__title')
class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    fields = ('product', 'required_quantity', 'unit_measure')

@admin.register(Cuisine)
class CuisineAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'cuisine', 'slug')
    list_filter = ('cuisine',)
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [RecipeIngredientInline]

@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'product', 'required_quantity', 'unit_measure')
    list_filter = ('recipe__cuisine', 'recipe', 'unit_measure')
    search_fields = ('recipe__title', 'product__title')
@admin.register(RecipeReview)
class RecipeReviewAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('comment', 'user__username', 'recipe__title')