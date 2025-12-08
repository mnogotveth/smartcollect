from __future__ import annotations

from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase

from payouts.models import CurrencyChoices, Payout, PayoutStatus
from payouts.tasks import finalize_payout


class PayoutAPITestCase(APITestCase):
    def setUp(self) -> None:
        self.list_url = reverse("payout-list")
        self.user = get_user_model().objects.create_user(
            username="test",
            email="test@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    @mock.patch("payouts.views.process_payout.delay")
    def test_create_payout_success(self, mock_delay: mock.Mock) -> None:
        payload = {
            "amount": "120.50",
            "currency": "usd",
            "recipient_name": "Alice",
            "recipient_account": "ACC-00123",
            "description": "Salary",
        }

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payout = Payout.objects.get()
        self.assertEqual(payout.status, PayoutStatus.PENDING)
        self.assertEqual(response.data["currency"], CurrencyChoices.USD)
        self.assertEqual(Decimal(response.data["amount"]), Decimal("120.50"))
        mock_delay.assert_called_once()

    @mock.patch("payouts.views.process_payout.delay")
    def test_celery_task_enqueued_on_create(self, mock_delay: mock.Mock) -> None:
        payload = {
            "amount": "15.00",
            "currency": "EUR",
            "recipient_name": "Bob",
            "recipient_account": "RECIP-009",
        }

        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payout = Payout.objects.get()
        mock_delay.assert_called_once_with(str(payout.id))


class PayoutTaskTestCase(TestCase):
    def setUp(self) -> None:
        self.payout = Payout.objects.create(
            amount="100.00",
            currency=CurrencyChoices.USD,
            recipient_name="Hook",
            recipient_account="ACC-777",
            status=PayoutStatus.PROCESSING,
            callback_url="https://example.com/webhook",
        )

    @mock.patch("payouts.tasks.send_payout_webhook.delay")
    def test_finalize_triggers_webhook(self, mock_webhook: mock.Mock) -> None:
        finalize_payout.apply(args=(str(self.payout.id),))
        mock_webhook.assert_called_once_with(str(self.payout.id))
