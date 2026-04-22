from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MarketplaceViewSet, ModuleCheckoutView

router = DefaultRouter()
router.register(r"modules", MarketplaceViewSet, basename="module")

urlpatterns = [
    path("", include(router.urls)),
    path("modules/<slug:slug>/checkout/", ModuleCheckoutView.as_view(), name="module-checkout"),
]
