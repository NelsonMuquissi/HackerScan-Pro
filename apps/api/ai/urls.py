from django.urls import path
from . import views, views_credits

urlpatterns = [
    path('findings/<uuid:finding_id>/explain/', views.AIExplanationView.as_view(), name='ai-explain'),
    path('findings/<uuid:finding_id>/remediate/', views.AIRemediationView.as_view(), name='ai-remediate'),
    path('scans/<uuid:scan_id>/prediction/', views.AIScanPredictionView.as_view(), name='ai-scan-prediction'),

    # Credits
    path('wallet/', views_credits.AIWalletView.as_view(), name='ai-wallet'),
    path('transactions/', views_credits.AITransactionListView.as_view(), name='ai-transactions'),
    path('packages/', views_credits.CreditPackageListView.as_view(), name='ai-packages'),
    path('achievements/', views_credits.AchievementListView.as_view(), name='ai-achievements'),
    path('checkout/', views_credits.CreditCheckoutView.as_view(), name='ai-checkout'),
]
