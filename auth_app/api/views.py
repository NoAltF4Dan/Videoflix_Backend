from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.http import Http404, JsonResponse
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from .services import EmailService  # Annahme: Diese Service-Klasse existiert
from .serializers import (
    UserSignupSerializer,
    EmailAuthTokenSerializer,
    PasswordRecoverySerializer,
    PasswordSetSerializer,
)

Account = get_user_model()

#--------------
# csrf_token
# Purpose:
#   Provides a CSRF token cookie for client-side requests requiring CSRF protection.
#
# Methods:
#   - GET: Sets CSRF cookie and returns confirmation message.
#
# Security:
#   - Uses Django's ensure_csrf_cookie decorator for CSRF protection.
#--------------
@ensure_csrf_cookie
def csrf_token(request):
    """Set a CSRF token cookie for the client."""
    return JsonResponse({"message": "CSRF cookie successfully set"})

#--------------
# RegistrationView
# Purpose:
#   Handles user signup, creates an inactive account, generates an activation token,
#   and dispatches a confirmation email.
#
# Methods:
#   - POST: Validates data with UserSignupSerializer, saves inactive user,
#           creates token, and sends email via EmailService.
#
# Security & UX:
#   - Uses AllowAny permission for public access.
#   - Returns generic 400 error to prevent leaking validation details.
#--------------
class RegistrationView(APIView):
    """Endpoint for user registration and sending activation email."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Process registration, save inactive account, and send confirmation email."""
        serializer = UserSignupSerializer(data=request.data)
        if serializer.is_valid():
            account = serializer.save()
            token = default_token_generator.make_token(account)
            EmailService.send_registration_confirmation_email(account, token)

            return Response({
                'account': {'id': account.pk, 'email': account.email},
                'token': token
            }, status=status.HTTP_201_CREATED)

        return Response({
            'error': 'Provided email or password is invalid'
        }, status=status.HTTP_400_BAD_REQUEST)

#--------------
# ActivateAccountView
# Purpose:
#   Activates a user account using a base64-encoded user ID and token from an email link.
#
# Methods:
#   - GET: Decodes uidb64, checks token validity, and activates account if valid.
#
# Security & UX:
#   - Returns generic 400 errors for invalid/expired tokens to avoid enumeration.
#   - Confirms activation or already active status with 200 response.
#--------------
@api_view(['GET'])
@permission_classes([AllowAny])
def activate_account_view(request, uidb64, token):
    """Activate user account via email link with encoded ID and token."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        account = Account.objects.get(pk=uid)

        if not default_token_generator.check_token(account, token):
            return Response({
                'error': 'Invalid or expired activation token.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if account.is_active:
            return Response({
                'message': 'Account already activated.'
            }, status=status.HTTP_200_OK)

        account.is_active = True
        account.save()

        return Response({
            'message': 'Account activated successfully.'
        }, status=status.HTTP_200_OK)

    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        return Response({
            'error': 'Activation link is invalid or expired.'
        }, status=status.HTTP_400_BAD_REQUEST)

#--------------
# TokenRenewView
# Purpose:
#   Refreshes JWT access token using a refresh token stored in an HTTP-only cookie.
#
# Methods:
#   - POST: Retrieves refresh_token from cookies, validates it, and sets new access token as cookie.
#
# Cookies:
#   - Reads: refresh_token
#   - Writes: access_token (HTTP-only, secure, samesite=None, domain from settings)
#
# Security:
#   - AllowAny permission for token-based authentication.
#   - Returns 400 for missing token, 401 for invalid token.
#--------------
class TokenRenewView(TokenRefreshView):
    """Endpoint to refresh JWT access token from cookie-stored refresh token."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Validate cookie refresh token and issue new access token."""
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response({
                'detail': 'Refresh token missing.'
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({
                'detail': 'Refresh token is invalid or expired.'
            }, status=status.HTTP_401_UNAUTHORIZED)

        access_token = serializer.validated_data.get('access')
        response = Response({'message': 'Access token renewed successfully'})
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=True,
            samesite='None',
            path='/',
            domain=settings.COOKIE_DOMAIN
        )
        return response

#--------------
# LoginView
# Purpose:
#   Authenticates users via email and password, issuing JWT tokens as HTTP-only cookies.
#
# Methods:
#   - POST: Validates credentials with EmailAuthTokenSerializer and sets tokens as cookies.
#
# Cookies:
#   - Writes: access_token, refresh_token (HTTP-only, secure, samesite=None, domain from settings)
#
# Security:
#   - AllowAny permission, as authentication is handled by the serializer.
#   - Checks account activation status before issuing tokens.
#--------------
class LoginView(APIView):
    """Endpoint for email-based authentication with JWT tokens stored in cookies."""
    permission_classes = [AllowAny]
    serializer_class = EmailAuthTokenSerializer

    def post(self, request):
        """Authenticate user and set JWT tokens as secure cookies."""
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response({
                'detail': 'Provided email or password is invalid.'
            }, status=status.HTTP_400_BAD_REQUEST)

        account = Account.objects.get(email=serializer.validated_data['auth_email'])
        if not account.is_active:
            return Response({
                'detail': 'Account is not activated.'
            }, status=status.HTTP_400_BAD_REQUEST)

        tokens = serializer.validated_data
        response = Response({'message': 'Login successful'})
        response.set_cookie(
            key='access_token',
            value=str(tokens['access']),
            httponly=True,
            secure=True,
            samesite='None',
            path='/',
            domain=settings.COOKIE_DOMAIN
        )
        response.set_cookie(
            key='refresh_token',
            value=str(tokens['refresh']),
            httponly=True,
            secure=True,
            samesite='None',
            path='/',
            domain=settings.COOKIE_DOMAIN
        )
        return response

#--------------
# LogoutView
# Purpose:
#   Logs out a user by invalidating the refresh token and clearing authentication cookies.
#
# Methods:
#   - POST: Blacklists refresh_token (if present) and deletes access/refresh cookies.
#
# Cookies:
#   - Reads: refresh_token
#   - Deletes: access_token, refresh_token
#
# Notes:
#   - Ignores TokenError for idempotent logout behavior.
#--------------
class LogoutView(APIView):
    """Endpoint for user logout by invalidating tokens and clearing cookies."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Invalidate refresh token and remove authentication cookies."""
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        response = Response({
            'detail': 'Logout completed. Tokens invalidated and cookies cleared.'
        }, status=status.HTTP_200_OK)
        response.delete_cookie('access_token', path='/', samesite='None', domain=settings.COOKIE_DOMAIN)
        response.delete_cookie('refresh_token', path='/', samesite='None', domain=settings.COOKIE_DOMAIN)
        return response

#--------------
# PasswordResetInitiateView
# Purpose:
#   Starts a password reset by validating an email and sending a reset link if the account is active.
#
# Methods:
#   - POST: Uses PasswordRecoverySerializer to validate email and sends reset email if valid.
#
# Security:
#   - Returns generic success message to prevent account enumeration.
#--------------
class PasswordResetInitiateView(APIView):
    """Endpoint to initiate a password reset via email."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate email and send reset email if account exists and is active."""
        serializer = PasswordRecoverySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['recovery_email']
        try:
            account = Account.objects.get(email=email, is_active=True)
            EmailService.send_password_reset_email(account)
        except Account.DoesNotExist:
            pass

        return Response({
            'detail': 'If the account exists, a password reset email has been sent.'
        }, status=status.HTTP_200_OK)

#--------------
# PasswordResetCompleteView
# Purpose:
#   Completes password reset by validating a token and updating the password.
#
# Methods:
#   - POST: Decodes uidb64, verifies token, and uses PasswordSetSerializer to update password.
#
# Errors:
#   - Returns 400 for invalid/expired tokens or validation errors, 500 for unexpected issues.
#
# Notes:
#   - Requires uidb64 and token from the reset email link.
#--------------
class PasswordResetCompleteView(APIView):
    """Endpoint to finalize password reset by setting a new password."""
    permission_classes = [AllowAny]
    serializer_class = PasswordSetSerializer

    def retrieve_user(self, uidb64):
        """Decode base64 user ID and fetch the corresponding account."""
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            return Account.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
            raise Http404('Invalid or expired password reset link.')

    def verify_token(self, account, token):
        """Check if the reset token is valid for the given account."""
        if not default_token_generator.check_token(account, token):
            raise Http404('Password reset token is invalid or expired.')

    def post(self, request, uidb64, token):
        """Validate token and update password with provided data."""
        try:
            account = self.retrieve_user(uidb64)
            self.verify_token(account, token)

            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.update(account)
                return Response({
                    'detail': 'Password updated successfully.'
                }, status=status.HTTP_200_OK)

            return Response({
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Http404 as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({
                'detail': 'An unexpected error occurred during password reset.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)