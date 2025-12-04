from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


class CurrencyChoices(models.TextChoices):
    USD = "USD", "US Dollar"
    EUR = "EUR", "Euro"
    RUB = "RUB", "Russian Ruble"
    GBP = "GBP", "British Pound"


class PayoutStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class Payout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(
        max_length=3,
        choices=CurrencyChoices.choices,
        default=CurrencyChoices.USD,
    )
    recipient_name = models.CharField(max_length=128)
    recipient_account = models.CharField(
        max_length=64,
        validators=[
            RegexValidator(
                regex=r"^[A-Z0-9\-]+$",
                message="Recipient account may only contain uppercase letters, digits, and dashes.",
            )
        ],
    )
    status = models.CharField(
        max_length=16,
        choices=PayoutStatus.choices,
        default=PayoutStatus.PENDING,
    )
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.id} ({self.amount} {self.currency})"

    def mark_processing(self) -> None:
        self.status = PayoutStatus.PROCESSING
        self.save(update_fields=["status", "updated_at"])

    def mark_completed(self) -> None:
        self.status = PayoutStatus.COMPLETED
        self.save(update_fields=["status", "updated_at"])

    def mark_failed(self) -> None:
        self.status = PayoutStatus.FAILED
        self.save(update_fields=["status", "updated_at"])
