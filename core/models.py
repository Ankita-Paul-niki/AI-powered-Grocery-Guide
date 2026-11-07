from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
#from django.db import conf, models
from django.contrib.auth.models import User
from django.conf import settings
from django.db import models       # Correct
# Create your models here.
class Category(models.Model):
    """Global catalog of items with average supermarket prices."""
    Category_name = models.CharField(max_length=100, unique=True)
    Category_slug = models.SlugField(null=True, blank=True)
    Category_created_at = models.DateField(auto_now_add=True)
    def save(self,*args,**kwargs):
        self.Category_slug=slugify(self.Category_name)
        return super().save(*args,**kwargs)
    def __str__(self):
        return self.Category_name
class Product(models.Model):
    # Measurement unit options
    UNIT_CHOICES = [
        # --- Standard Metric Settings ---
        ('KG', 'Kilogram (kg)'),
        ('G', 'Gram (g)'),
        ('L', 'Litre (L)'),
        ('ML', 'Millilitre (ml)'),
        ('M', 'Meter (m)'),
        ('PCS', 'Piece/Item (pcs)'),
        
        # --- Custom Text/Container Settings ---
        ('PKT', 'Packet'),
        ('BOX', 'Box'),
        ('BTL', 'Bottle'),
        ('BND', 'Bundle'),
        ('DZN', 'Dozen'),
    ]

    SHELF_LIFE_UNITS = [
        ('DAYS', 'Day(s)'),
        ('WEEKS', 'Week(s)'),
        ('MONTHS', 'Month(s)'),
        ('YEARS', 'Year(s)'),
    ]

    categories = models.ManyToManyField(
        Category, 
        blank=True, 
        related_name='products',
        help_text="Select one or more categories for this product"
    )
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    
    # Financials and Core Stock
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(
    max_digits=10, 
    decimal_places=2, 
    blank=True, 
    null=True) 
    stock = models.IntegerField(default=0, help_text="Available inventory units in warehouse")
    
    # Quantitative sizing tracking configuration
    package_quantity = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=1.00,
        help_text="The numeric size of a single product package (e.g., 500.00, 1.50, or 1.00)"
    )
    package_unit = models.CharField(
        max_length=5, 
        choices=UNIT_CHOICES, 
        default='PCS',
    )

    # Shelf Life duration details
    shelf_life_value = models.PositiveIntegerField(
        blank=True, 
        null=True, 
        help_text="The duration number of the shelf life (e.g., 6, 12, 30)"
    )
    shelf_life_unit = models.CharField(
        max_length=10, 
        choices=SHELF_LIFE_UNITS, 
        default='DAYS',
        blank=True, 
        null=True,
    )

    # --- START OPTIONAL DATES SECTION ---
    manufacture_date = models.DateField(
        blank=True, 
        null=True, 
        help_text="Optional: The date this specific batch was manufactured."
    )
    expiry_date = models.DateField(
        blank=True, 
        null=True, 
        help_text="Optional: Explicit expiration date. Supercedes generic shelf life logic."
    )
    # --- END OPTIONAL DATES SECTION ---
    
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reward_pocket_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00, 
        #help_text="Admin defined reward amount credited to user pockets after #successful delivery"
    )
    class Meta:
        ordering = ['-created_at']

    @property
    def full_measurement(self):
        """Returns a clean display name checking whether it's a metric sign or plain text."""
        qty = f"{self.package_quantity}".rstrip('0').rstrip('.') if '.' in f"{self.package_quantity}" else self.package_quantity
        
        if self.package_unit in ['PKT', 'BOX', 'BTL', 'BND', 'DZN']:
            unit_display = self.get_package_unit_display().lower()
            if float(self.package_quantity) > 1:
                if self.package_unit == 'BOX':
                    return f"{qty} boxes"
                return f"{qty} {unit_display}s"
            return f"{qty} {unit_display}"
            
        unit_label = self.get_package_unit_display()
        if '(' in unit_label and ')' in unit_label:
            return f"{qty} {unit_label.split('(')[-1].replace(')', '')}"
            
        return f"{qty} {unit_label}"

    @property
    def formatted_shelf_life(self):
        if self.shelf_life_value:
            unit_display = self.get_shelf_life_unit_display()
            if self.shelf_life_value == 1:
                return f"1 {unit_display.replace('(s)', '')}"
            return f"{self.shelf_life_value} {unit_display.replace('(s)', 's')}"
        return "N/A"

    @property
    def is_expired(self):
        """Dynamic flag check evaluating current real-world timeframe states."""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    def clean(self):
        """Backend safety checks validating user-input date chronologies."""
        super().clean()
        if self.manufacture_date and self.expiry_date:
            if self.expiry_date <= self.manufacture_date:
                raise ValidationError({
                    'expiry_date': "The expiry date must be later than the manufacture date."
                })

    def __str__(self):
        status = " (EXPIRED)" if self.is_expired else ""
        return f"{self.title} ({self.full_measurement}){status}"

    def save(self, *args, **kwargs):
        self.full_clean()  # Forces the clean validation to execute on admin saves
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart #{self.id} ({self.user.username if self.user else 'Guest'})"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total_price(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.title}"


class UserPocket(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pocket')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username}'s Pocket: ₹{self.balance}"
class Order(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('On the way', 'On the way'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    address = models.CharField(max_length=250)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # Fixed here
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    is_reward_credited = models.BooleanField(default=False)
    return_requested = models.BooleanField(default=False)
    is_returned = models.BooleanField(default=False)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.product.title}"
class ProductImage(models.Model):
    """Supports multiple gallery images for the same product."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Gallery Image for {self.product.title}"
class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(default=5, help_text="Rating from 1 to 5")
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.title} ({self.rating}★)"