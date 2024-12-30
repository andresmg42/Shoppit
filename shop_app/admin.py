from django.contrib import admin
from .models import Product,Cart,CartItem

admin.site.register([Product,Cart,CartItem])

# Register your models here.
