from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# router.register('webhooks', WebhookViewSet, basename='webhook')

urlpatterns = [
    path('', include(router.urls)),
]
