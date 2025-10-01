from django.urls import path

from wallet.apps import WalletConfig
from wallet.views import WalletDetailAPIView, WalletOperationsAPIView

app_name = WalletConfig.name


urlpatterns = [
    path('api/v1/wallets/<uuid:wallet_uuid>', WalletDetailAPIView.as_view(), name='wallet-detail'),
    path('api/v1/wallets/<uuid:wallet_uuid>/operation', WalletOperationsAPIView.as_view(), name='wallet-operation'),
]
