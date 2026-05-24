"""
SourceSystem views.
"""
from rest_framework import viewsets
from .models import SourceSystem
from .serializers import SourceSystemSerializer


class SourceSystemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SourceSystemSerializer

    def get_queryset(self):
        return SourceSystem.objects.filter(tenant=self.request.user.tenant)
