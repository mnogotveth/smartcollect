from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from payouts.models import CurrencyChoices, Payout, PayoutStatus


class PayoutSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    currency = serializers.CharField(max_length=3)
    status = serializers.ChoiceField(
        choices=PayoutStatus.choices,
        required=False,
        allow_blank=False,
    )

    class Meta:
        model = Payout
        fields = [
            "id",
            "amount",
            "currency",
            "recipient_name",
            "recipient_account",
            "status",
            "description",
            "callback_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_currency(self, value: str) -> str:
        value = value.upper()
        if value not in CurrencyChoices.values:
            raise serializers.ValidationError("Unsupported currency.")
        return value

    def validate_recipient_account(self, value: str) -> str:
        normalized = value.replace(" ", "").upper()
        if len(normalized) < 6:
            raise serializers.ValidationError("Recipient account is too short.")
        return normalized

    def validate_status(self, value: str) -> str:
        instance: Payout | None = getattr(self, "instance", None)
        if instance and instance.status == PayoutStatus.COMPLETED and value != instance.status:
            raise serializers.ValidationError("Completed payouts cannot be updated.")
        return value

    def create(self, validated_data: dict) -> Payout:
        validated_data["status"] = PayoutStatus.PENDING
        return super().create(validated_data)
