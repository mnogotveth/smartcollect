from __future__ import annotations

import logging
from decimal import Decimal

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
