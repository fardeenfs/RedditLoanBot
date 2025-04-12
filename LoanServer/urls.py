"""LoanServer URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from loanmanager.api import (
    ConfirmLoanWithIDView,
    LoanViewSet, 
    ConfirmLoanByThreadView, 
    PayLoanByThreadView, 
    PayLoanWithIDView, 
    UnpaidLoanWithIDView,
    UnpaidLoanByThreadView, 
    CheckUserLoansView, 
    CancelLoanByThreadView,
    CancelLoanWithIDView,
    TrackCommentView,
    PaymentViewSet,
    CancelPaymentView
)
from rest_framework_simplejwt import views as jwt_views

from loanmanager.views import loan_list, reddit_user_detail, search_users



# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register('loans', LoanViewSet)
router.register('payments', PaymentViewSet)

urlpatterns = [
    path('', loan_list, name='loan-list'),
    path('user/', search_users, name='search_users'),
    path('user/<str:username>/', reddit_user_detail, name='reddit_user_detail'),
    # The API URLs are now determined automatically by the router.
    path('api/', include(router.urls)),
    path('admin/', admin.site.urls),
    
    # Additional custom view URLs
    path('api/confirm-loan-by-thread/', ConfirmLoanByThreadView.as_view(), name='confirm-loan'),
    path('api/confirm-loan-with-id/', ConfirmLoanWithIDView.as_view(), name='confirm-loan'),
    path('api/pay-loan-by-thread/', PayLoanByThreadView.as_view(), name='pay-loan-by-thread'),
    path('api/pay-loan-with-id/', PayLoanWithIDView.as_view(), name='pay-loan-by-id'),
    path('api/unpaid-loan-by-thread/', UnpaidLoanByThreadView.as_view(), name='unpaid-loan-by-thread'),
    path('api/unpaid-loan-with-id/', UnpaidLoanWithIDView.as_view(), name='unpaid-loan-by-id'),
    path('api/check-user-loans/', CheckUserLoansView.as_view(), name='check-user-loans'),
    path('api/cancel-loan-by-thread/', CancelLoanByThreadView.as_view(), name='cancel-loan-by-thread'),
    path('api/cancel-loan-with-id/', CancelLoanWithIDView.as_view(), name='cancel-loan-by-id'),
    path('api/cancel-payment-with-id/', CancelPaymentView.as_view(), name='cancel-payment-by-id'),
    path('api/track-comment/', TrackCommentView.as_view(), name='track-comment'),

     # JWT Token authentication URLs
    path('api/token/', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', jwt_views.TokenVerifyView.as_view(), name='token_verify'),
    
]
