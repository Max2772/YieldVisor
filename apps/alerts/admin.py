from django.contrib import admin
from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'asset_type', 'asset_name', 'direction', 'target_price', 'is_active', 'created_at', 'triggered_at')
    list_filter = ('is_active', 'asset_type', 'direction', 'created_at')
    search_fields = ('user__username', 'asset_name')
    readonly_fields = ('created_at', 'triggered_at')
    list_editable = ('is_active',)
