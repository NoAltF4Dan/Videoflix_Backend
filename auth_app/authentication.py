from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.exceptions import AuthenticationFailed

class CookieBasedJWTAuth(JWTAuthentication):
    """Custom authentication class to validate JWT tokens stored in HTTP-only cookies."""
    
    def authenticate(self, request):
        """Extract and validate JWT access token from cookies, returning user and token if valid."""
        token = request.COOKIES.get('access_token')
        
        if not token:
            return None  

        try:
            validated_token = self.get_validated_token(token)
        except InvalidToken:
            return None  

        try:
            account = self.get_user(validated_token)
        except AuthenticationFailed:
            return None  

        return (account, validated_token)