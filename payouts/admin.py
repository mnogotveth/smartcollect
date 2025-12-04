from django.contrib import admin

from payouts.models import Payout


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "amount",
        "currency",
        "recipient_name",
        "status",
        "created_at",
    )
    search_fields = ("recipient_name", "recipient_account", "status")
    list_filter = ("status", "currency", "created_at")
    ordering = ("-created_at",)
