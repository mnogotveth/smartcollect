from rest_framework import filters, permissions, viewsets

from payouts.models import Payout
from payouts.serializers import PayoutSerializer
from payouts.tasks import process_payout


class PayoutViewSet(viewsets.ModelViewSet):
    queryset = Payout.objects.all().order_by("-created_at")
    serializer_class = PayoutSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    ordering_fields = ["created_at", "amount", "status"]
    search_fields = ["recipient_name", "recipient_account", "currency", "status"]

    def perform_create(self, serializer: PayoutSerializer) -> None:
        payout = serializer.save()
        process_payout.delay(str(payout.id))
