<img src="./assets/logo_icon.svg" alt="Videoflix Logo" width="320">

Videoflix is a Django-based backend application for a video streaming platform. It supports user registration, authentication with JWT (JSON Web Tokens), media uploads, and asynchronous task processing. The project uses PostgreSQL as the database, Redis for caching and asynchronous tasks, and Gunicorn as the WSGI server for production.

## ✨ Technologies
The following technologies are used in the project:

- Django: Python web framework for rapid development and clean design. It provides a robust foundation for the API, authentication, and database management.

- Django REST Framework (DRF): Enables the creation of RESTful APIs with Django, including serialization and authentication.

- djangorestframework-simplejwt: Implements JWT-based authentication with cookie support for secure and stateless user sessions.

- django-redis: Provides Redis as a cache backend for Django, enabling efficient caching and session management.

- django-rq: Facilitates asynchronous task processing with Redis Queue (RQ), used for tasks like sending emails.

- PostgreSQL: A reliable, open-source relational database for persistent data storage, chosen for its robustness and scalability.

- Redis: An in-memory data store used for caching and asynchronous task queues, chosen for its speed and simplicity.

- Gunicorn: A production-ready WSGI server for running Django applications, chosen for its performance and compatibility.

- python-dotenv: Loads environment variables from a .env file for secure configuration (e.g., secret key, database credentials).

- Whitenoise: Serves static files efficiently in Django without requiring a separate web server.

- Pillow: Handles image processing for media uploads, such as thumbnails.

- psycopg: PostgreSQL adapter for Django, used for database connectivity.

- pytest, pytest-django, pytest-cov, coverage: Testing tools for ensuring code quality and coverage.

---

## Prerequisites

Before setting up the project, ensure you have the following installed:

- Docker and Docker Compose: For running the application in containers.
- Git: For cloning the repository.
- A text editor (e.g., VS Code) for editing configuration files.

---

# Setup Instructions
### Follow these steps to set up the Videoflix backend locally.

## 1. Clone the Repository

Clone the project repository to your local machine:
``
git clone <repository-url>
cd videoflix_main
``

## 2. Create a .env File

# Notes:
- Generate a secure SECRET_KEY using Python:
``
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
``

- For EMAIL_HOST_USER and EMAIL_HOST_PASSWORD, use a service like Gmail with an App Password or another SMTP provider.

## 3. Build and Start the Containers

Use Docker Compose to build and start the services.
``
docker-compose down -v  # Remove existing containers and volumes (optional for fresh setup)
docker-compose build --no-cache
docker-compose up
``

This starts the following services:

- db: PostgreSQL database (container name: videoflix_database)
- redis: Redis server (container name: videoflix_redis)
- web: Django backend with Gunicorn (container name: videoflix_backend)
- worker: RQ worker for asynchronous tasks (container name: videoflix_worker)

### 4. Verify the Setup

Check the logs to ensure all services start correctly:
``
docker-compose logs
``

# Expected output includes:

- videoflix_database: database system is ready to accept connections
- videoflix_redis: Ready to accept connections tcp
- videoflix_backend: Starting gunicorn ... Listening at: http://0.0.0.0:8000
- videoflix_worker: Listening on default...

### 5. Test the Application

Test the API endpoints to verify functionality:
- Authentication:
``
curl -X POST http://localhost:8000/api/token/ -d "auth_email=admin@example.com&auth_password=adminpassword" -H "Content-Type: application/x-www-form-urlencoded"
``
- This should return access and refresh tokens.
- Admin Interface:
Open http://localhost:8000/admin/ in a browser and log in with admin / adminpassword.
- Registration:
``
curl -X POST http://localhost:8000/register/ -d "user_email=test@example.com&user_password=Test12345&password_repeat=Test12345&accept_privacy=on" -H "Content-Type: application/x-www-form-urlencoded"
``

### 6. Run Tests (Optional)
Run automated tests to verify code integrity:

> 🔗 **[Frontend Repository ](https://github.com/NoAltF4Dan/Videoflix_frontend)**

---

## 🛠 Installation & Setup
