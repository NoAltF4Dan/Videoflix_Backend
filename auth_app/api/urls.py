from django.urls import path

from .views import (
    csrf_token,                    
    RegistrationView,              
    LoginView,                     
    TokenRenewView,               
    activate_account_view,         
    LogoutView,                    
    PasswordResetInitiateView,     
    PasswordResetCompleteView,     
)

app_name = "authentication"

urlpatterns = [
    path("csrf/", csrf_token, name="csrf"),
    path("register/", RegistrationView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRenewView.as_view(), name="token_refresh"),
    path("activate/<str:uidb64>/<str:token>/", activate_account_view, name="activate_account"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password_reset/", PasswordResetInitiateView.as_view(), name="password_reset"),
    path("password_confirm/<str:uidb64>/<str:token>/", PasswordResetCompleteView.as_view(), name="password_reset_confirm"),
]