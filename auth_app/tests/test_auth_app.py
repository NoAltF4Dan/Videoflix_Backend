import pytest
from django.urls import reverse
from django.core import mail
from rest_framework import status
from django.contrib.auth import get_user_model
from django.test import Client
import base64
import json

User = get_user_model()
pytestmark = pytest.mark.django_db

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def user_data():
    return {
        "email": "test@example.com",
        "password": "securepassword123",
        "confirmed_password": "securepassword123"
    }

def test_register_user_success(client, user_data):
    response = client.post('/api/register/', data=user_data, content_type='application/json')
    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.filter(email=user_data["email"]).exists()
    assert len(mail.outbox) == 1  
    assert mail.outbox[0].subject  
    user = User.objects.get(email=user_data["email"])
    assert not user.is_active  

def test_register_user_password_mismatch(client):
    data = {
        "email": "test@example.com",
        "password": "securepassword123",
        "confirmed_password": "differentpassword"
    }
    response = client.post('/api/register/', data=data, content_type='application/json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(email=data["email"]).exists()

def test_register_user_existing_email(client, user_data):
    User.objects.create_user(email=user_data["email"], password=user_data["password"])
    response = client.post('/api/register/', data=user_data, content_type='application/json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_activate_user_success(client, user_data):
    response = client.post('/api/register/', data=user_data, content_type='application/json')
    user = User.objects.get(email=user_data["email"])
    
    uidb64 = base64.urlsafe_b64encode(str(user.id).encode()).decode()
    token = "valid-token"  
    response = client.get(f'/api/activate/{uidb64}/{token}/')
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("message") == "Account successfully activated."
    user.refresh_from_db()
    assert user.is_active

def test_activate_user_invalid_token(client, user_data):
    response = client.post('/api/register/', data=user_data, content_type='application/json')
    user = User.objects.get(email=user_data["email"])
    uidb64 = base64.urlsafe_b64encode(str(user.id).encode()).decode()
    response = client.get(f'/api/activate/{uidb64}/invalid-token/')
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_login_user_success(client, user_data):
    client.post('/api/register/', data=user_data, content_type='application/json')
    user = User.objects.get(email=user_data["email"])
    user.is_active = True
    user.save()
    
    login_data = {"email": user_data["email"], "password": user_data["password"]}
    response = client.post('/api/login/', data=login_data, content_type='application/json')
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("detail") == "Login successful"
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

def test_login_user_invalid_credentials(client, user_data):
    login_data = {"email": user_data["email"], "password": "wrongpassword"}
    response = client.post('/api/login/', data=login_data, content_type='application/json')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_logout_user_success(client, user_data):
    client.post('/api/register/', data=user_data, content_type='application/json')
    user = User.objects.get(email=user_data["email"])
    user.is_active = True
    user.save()
    login_data = {"email": user_data["email"], "password": user_data["password"]}
    client.post('/api/login/', data=login_data, content_type='application/json')
    
    response = client.post('/api/logout/', content_type='application/json')
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("detail") == "Logout successful! All tokens will be deleted. Refresh token is now invalid."
    assert "access_token" not in response.cookies or response.cookies["access_token"].value == ""
    assert "refresh_token" not in response.cookies or response.cookies["refresh_token"].value == ""

def test_logout_user_no_refresh_token(client):
    response = client.post('/api/logout/', content_type='application/json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_token_refresh_success(client, user_data):
    client.post('/api/register/', data=user_data, content_type='application/json')
    user = User.objects.get(email=user_data["email"])
    user.is_active = True
    user.save()
    login_data = {"email": user_data["email"], "password": user_data["password"]}
    client.post('/api/login/', data=login_data, content_type='application/json')
    
    response = client.post('/api/token/refresh/', content_type='application/json')
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("detail") == "Token refreshed"
    assert "access_token" in response.cookies

def test_token_refresh_no_refresh_token(client):
    response = client.post('/api/token/refresh/', content_type='application/json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_password_reset_success(client, user_data):
    client.post('/api/register/', data=user_data, content_type='application/json')
    response = client.post('/api/password_reset/', data={"email": user_data["email"]}, content_type='application/json')
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("detail") == "An email has been sent to reset your password."
    assert len(mail.outbox) == 2  

def test_password_reset_nonexistent_email(client):
    response = client.post('/api/password_reset/', data={"email": "nonexistent@example.com"}, content_type='application/json')
    assert response.status_code == status.HTTP_200_OK  
    assert len(mail.outbox) == 0  

def test_password_confirm_success(client, user_data):
    client.post('/api/register/', data=user_data, content_type='application/json')
    user = User.objects.get(email=user_data["email"])
    uidb64 = base64.urlsafe_b64encode(str(user.id).encode()).decode()
    token = "valid-token"  
    new_password_data = {
        "new_password": "newsecurepassword123",
        "confirm_password": "newsecurepassword123"
    }
    response = client.post(f'/api/password_confirm/{uidb64}/{token}/', data=new_password_data, content_type='application/json')
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("detail") == "Your Password has been successfully reset."
    user.refresh_from_db()
    assert user.check_password(new_password_data["new_password"])

def test_password_confirm_password_mismatch(client, user_data):
    client.post('/api/register/', data=user_data, content_type='application/json')
    user = User.objects.get(email=user_data["email"])
    uidb64 = base64.urlsafe_b64encode(str(user.id).encode()).decode()
    token = "valid-token"
    new_password_data = {
        "new_password": "newsecurepassword123",
        "confirm_password": "differentpassword"
    }
    response = client.post(f'/api/password_confirm/{uidb64}/{token}/', data=new_password_data, content_type='application/json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST