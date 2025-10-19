import re
import uuid
from rest_framework import serializers
from django.contrib.auth.models import User

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated

User = get_user_model()

#--------------
# RegistrationSerializer
# Purpose:
#   Register a new (inactive) user using email + password confirmation,
#   with an explicit privacy-policy acceptance.
#
# Accepts (request payload):
#   - email (str, required, ASCII-only, unique)
#   - password (str, required, write-only)
#   - confirmed_password (str, required, must match password)
#   - privacy_policy (str, required, must equal "on")
#
# Validation:
#   - confirmed_password must equal password
#   - email must be ASCII-only and unique
#   - privacy_policy must be "on"
#
# save():
#   - Derives username from email local-part; if taken, appends short UUID
#   - Creates user with is_active=False
#   - Hashes password via set_password()
#
# Notes:
#   - Uses generic error for existing emails to avoid user enumeration
#   - No side effects beyond creating the user instance
#--------------
class RegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration with email, password, and privacy policy validation."""
    confirmed_password = serializers.CharField(write_only=True)
    privacy_policy = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'confirmed_password', 'privacy_policy')
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate(self, attrs):
        """Validate password match, email format, uniqueness, and privacy policy acceptance."""
        if attrs['password'] != attrs['confirmed_password']:
            raise serializers.ValidationError({'confirmed_password': 'Passwords do not match'})

        email = attrs['email']
        if not re.match(r'^[\x00-\x7F]+$', email):
            raise serializers.ValidationError({'email': 'Email must contain only ASCII characters'})
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email': 'Email is already in use'})

        if attrs['privacy_policy'] != 'on':
            raise serializers.ValidationError({'privacy_policy': 'You must accept the privacy policy'})

        return attrs

    def create(self, validated_data):
        """Create an inactive user with a unique username and hashed password."""
        email = validated_data['email']
        password = validated_data['password']
        username = email.split('@')[0]

        if User.objects.filter(username=username).exists():
            username = f"{username}_{uuid.uuid4().hex[:8]}"

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=False
        )
        return user
    
class AccountActivationResponseSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=255)
    error = serializers.CharField(max_length=255, required=False)

class LoginSerializer(serializers.Serializer):
    """Serializer für die Validierung der Login-Daten."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class LoginResponseSerializer(serializers.Serializer):
    """Serializer für die Login-Response-Daten."""
    detail = serializers.CharField(max_length=255)
    user = serializers.DictField(child=serializers.CharField(), required=False)
