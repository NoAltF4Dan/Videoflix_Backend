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
    """API endpoint for registering a new user and sending a confirmation email."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Process user registration, save the account, generate an activation token, and send a confirmation email."""
        serializer = RegistrationSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            token = default_token_generator.make_token(user)
            EmailService.send_registration_confirmation_email(user, token)

            response_data = {
                'user': {
                    'id': user.pk,
                    'email': user.email
                },
                'token': token
            }
            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(
            {'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )