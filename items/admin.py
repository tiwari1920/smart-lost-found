from django.contrib import admin

from .models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'item_type', 'category', 'location', 'status', 'user', 'created_at')
    list_filter = ('item_type', 'status', 'category')
    search_fields = ('title', 'description', 'brand', 'color')