from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegistrationSerializer
from .services import EmailService
from django.contrib.auth.tokens import default_token_generator


#--------------
# RegistrationView
# Purpose:
#   Handle user sign-up, create an inactive account, generate an activation token,
#   and trigger a confirmation email.
#
# Methods:
#   - POST: validates payload with RegistrationSerializer, saves user (inactive),
#           creates token via default_token_generator, and sends confirmation email.
#
# Security & UX:
#   - Returns generic 400 with "Email or Password is invalid" on serializer errors
#     to avoid leaking exact validation reasons to attackers.
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
        

class LoginView(APIView):
    """
    API endpoint for authenticating a user and returning JWT tokens as HTTP-Only cookies.
    
    Purpose:
        Authenticate user credentials, generate JWT tokens, and set them as HTTP-Only cookies.
    
    Methods:
        - POST: Validates email and password, authenticates user, generates tokens,
                and sets access_token and refresh_token cookies.
    
    Security & UX:
        - Returns generic 400 errors to avoid leaking sensitive information.
        - Sets HTTP-Only, secure cookies for JWT tokens.
    """
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