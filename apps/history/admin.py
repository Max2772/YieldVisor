from django.contrib import admin
from .models import History


@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'operation', 'asset_type', 'asset_name', 'quantity', 'price', 'created_at')
    list_filter = ('operation', 'asset_type', 'created_at')
    search_fields = ('user__username', 'asset_name')
    readonly_fields = ('created_at',)
