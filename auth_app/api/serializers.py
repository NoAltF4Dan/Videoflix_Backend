import re
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

Account = get_user_model()

#--------------
# UserSignupSerializer
# Purpose:
#   Facilitates creation of a new, inactive user account with email, password, and privacy policy agreement.
#
# Input (request data):
#   - user_email (str, required, ASCII-only, must be unique)
#   - user_password (str, required, write-only)
#   - password_repeat (str, required, must match user_password)
#   - accept_privacy (str, required, must be "on")
#
# Validation:
#   - Checks that password_repeat equals user_password
#   - Ensures user_email is ASCII-only and not already registered
#   - Verifies accept_privacy is set to "on"
#
# save():
#   - Generates username from email's local part; appends UUID if taken
#   - Creates inactive user (is_active=False)
#   - Secures password with set_password()
#
# Notes:
#   - Generic error for duplicate emails to prevent enumeration attacks
#   - No additional side effects beyond user creation
#--------------
class UserSignupSerializer(serializers.ModelSerializer):
    """Handles new user registration with email, password, and privacy policy validation."""
    password_repeat = serializers.CharField(write_only=True)
    accept_privacy = serializers.CharField(write_only=True)

    class Meta:
        model = Account
        fields = ['user_email', 'user_password', 'password_repeat', 'accept_privacy']
        extra_kwargs = {
            'user_password': {'write_only': True},
            'user_email': {'required': True, 'source': 'email'},
            'user_password': {'source': 'password'},
        }

    def validate_password_repeat(self, value):
        """Verify that the repeated password matches the original."""
        pwd = self.initial_data.get('user_password')
        if pwd and value and pwd != value:
            raise serializers.ValidationError('The passwords do not match.')
        return value

    def validate_user_email(self, value):
        """Ensure email is ASCII-only and not already in use."""
        if not re.match(r'^[\x00-\x7F]+$', value):
            raise serializers.ValidationError('Email must contain only ASCII characters.')
        if Account.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError('Invalid email or password.')
        return value.lower()

    def validate_accept_privacy(self, value):
        """Confirm privacy policy acceptance."""
        if value != 'on':
            raise serializers.ValidationError('You must accept the privacy policy.')
        return value

    def save(self):
        """Create a new inactive user with a unique username and hashed password."""
        email = self.validated_data['email']
        pwd = self.validated_data['password']
        base_username = email.split('@')[0]

        # Handle username collision with UUID suffix
        username = base_username
        if Account.objects.filter(username=username).exists():
            username = f"{base_username}_{uuid.uuid4().hex[:8]}"

        new_user = Account(email=email, username=username, is_active=False)
        new_user.set_password(pwd)
        new_user.save()
        return new_user


#--------------
# EmailAuthTokenSerializer
# Purpose:
#   Generates JWT tokens using email and password for authentication.
#
# Input (request data):
#   - auth_email (str, required, case-insensitive)
#   - auth_password (str, required, write-only)
#
# Validation & Flow:
#   - Normalizes auth_email to lowercase
#   - Finds user by email; if not found, returns generic error
#   - Validates password with check_password(); fails with same error if incorrect
#   - Adds username to attributes and uses SimpleJWT for token generation
#
# Returns:
#   - {"refresh": "<token>", "access": "<token>"}
#
# Notes:
#   - Drops 'username' field from schema to avoid ambiguity
#   - Uses generic errors to prevent leaking user existence
#--------------
class EmailAuthTokenSerializer(TokenObtainPairSerializer):
    """Authenticates users with email and password to issue JWT tokens."""
    auth_email = serializers.EmailField()
    auth_password = serializers.CharField(write_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            del self.fields['username']

    def validate(self, data):
        """Clean email and authenticate user credentials."""
        email = data.get('auth_email')
        pwd = data.get('auth_password')

        if isinstance(email, str):
            email = email.lower().strip()
            data['auth_email'] = email

        try:
            user = Account.objects.get(email=email)
        except Account.DoesNotExist:
            raise serializers.ValidationError('Incorrect email or password.')

        if not user.check_password(pwd):
            raise serializers.ValidationError('Incorrect email or password.')

        data['username'] = user.username
        result = super().validate(data)
        return result


#--------------
# PasswordRecoverySerializer
# Purpose:
#   Initiates password recovery by validating and normalizing an email.
#
# Input (request data):
#   - recovery_email (str, required)
#
# Validation:
#   - Converts email to lowercase and removes whitespace
#
# Notes:
#   - Email sending logic is handled by the view or service
#--------------
class PasswordRecoverySerializer(serializers.Serializer):
    """Processes email input for password recovery requests."""
    recovery_email = serializers.EmailField()

    def validate_recovery_email(self, value):
        """Normalize email by converting to lowercase and trimming spaces."""
        return value.lower().strip()


#--------------
# NewPasswordSetSerializer
# Purpose:
#   Validates and updates a user's password during recovery.
#
# Input (request data):
#   - fresh_password (str, required, minimum 8 characters)
#   - confirm_password (str, required, must match fresh_password)
#
# Validation:
#   - Applies Django's password validation rules (length, complexity, etc.)
#   - Ensures fresh_password matches confirm_password
#
# update(account):
#   - Hashes and sets the new password, saves the user
#   - Returns the updated user object
#
# Notes:
#   - Errors are returned in JSON-compatible DRF format
#--------------
class PasswordSetSerializer(serializers.Serializer):
    """Validates and sets a new password for a user during recovery."""
    fresh_password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="New password (at least 8 characters)"
    )
    confirm_password = serializers.CharField(
        write_only=True,
        help_text="Confirm the new password"
    )

    def validate_fresh_password(self, value):
        """Apply Django's password validation rules."""
        try:
            validate_password(value)
        except ValidationError as error:
            raise serializers.ValidationError(list(error.messages))
        return value

    def validate(self, data):
        """Check that the new password and confirmation match."""
        if data['fresh_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        return data

    def update(self, account):
        """Set and save the new validated password for the user."""
        pwd = self.validated_data['fresh_password']
        account.set_password(pwd)
        account.save()
        return account

