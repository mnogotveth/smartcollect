from __future__ import annotations

import json
import logging
from decimal import Decimal
from urllib import error, request

from celery import shared_task
from django.conf import settings
from django.db import transaction

from payouts.models import Payout, PayoutStatus

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def process_payout(self, payout_id: str) -> None:
    try:
        payout = Payout.objects.get(id=payout_id)
    except Payout.DoesNotExist:
        logger.warning("Payout %s does not exist.", payout_id)
        return

    if payout.status not in {PayoutStatus.PENDING, PayoutStatus.PROCESSING}:
        logger.info("Skipping payout %s with status %s", payout_id, payout.status)
        return

    with transaction.atomic():
        payout.refresh_from_db()
        if payout.status == PayoutStatus.PENDING:
            payout.mark_processing()

    countdown = max(settings.PAYOUT_PROCESSING_DELAY_SECONDS, 0)
    finalize_payout.apply_async((payout_id,), countdown=countdown)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def finalize_payout(self, payout_id: str) -> None:
    try:
        payout = Payout.objects.get(id=payout_id)
    except Payout.DoesNotExist:
        logger.warning("Payout %s does not exist.", payout_id)
        return

    payout.refresh_from_db()
    if payout.status != PayoutStatus.PROCESSING:
        logger.info("Skipping payout %s with status %s", payout_id, payout.status)
        return

    if payout.amount >= Decimal("1000000"):
        payout.mark_failed()
        logger.error("Payout %s failed automatic risk checks.", payout_id)
    else:
        payout.mark_completed()
        logger.info("Payout %s processed successfully.", payout_id)

    if payout.callback_url:
        send_payout_webhook.delay(str(payout.id))


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def send_payout_webhook(self, payout_id: str) -> None:
    try:
        payout = Payout.objects.get(id=payout_id)
    except Payout.DoesNotExist:
        logger.warning("Webhook skipped: payout %s missing.", payout_id)
        return

    if not payout.callback_url:
        return

    data = {
        "payout_id": str(payout.id),
        "status": payout.status,
        "amount": str(payout.amount),
        "currency": payout.currency,
        "updated_at": payout.updated_at.isoformat(),
    }

    body = json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    request_obj = request.Request(
        payout.callback_url,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(request_obj, timeout=settings.WEBHOOK_TIMEOUT_SECONDS):
            logger.info("Webhook sent for payout %s", payout_id)
    except error.URLError as exc:
        logger.error("Webhook error for payout %s: %s", payout_id, exc)
