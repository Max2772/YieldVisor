from django.contrib import admin
from .models import Portfolio


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('user', 'asset_type', 'asset_name', 'quantity', 'avg_buy_price', 'app_id', 'created_at')
    list_filter = ('asset_type', 'created_at')
    search_fields = ('user__username', 'asset_name')
    readonly_fields = ('created_at', 'updated_at')
