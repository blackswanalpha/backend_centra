# AssureHub Backend (`backend_centra`)

This directory contains the backend services for the AssureHub platform, built with Django and Django REST Framework. It provides the core API functionalities for managing audits, reports, users, and other critical business logic.

## Table of Contents
1.  [Overview](#overview)
2.  [Features](#features)
3.  [Getting Started](#getting-started)
    *   [Prerequisites](#prerequisites)
    *   [Local Development Setup](#local-development-setup)
    *   [Running with Docker Compose](#running-with-docker-compose)
4.  [Project Structure](#project-structure)
5.  [Key Technologies](#key-technologies)
6.  [Deployment](#deployment)
7.  [API Documentation](#api-documentation)
8.  [Contributing](#contributing)
9.  [License](#license)

## 1. Overview
`backend_centra` is the RESTful API service powering AssureHub. It handles data persistence, business logic execution, authentication, and integration with external services. The primary goal is to provide a scalable, secure, and maintainable backend for the frontend applications.

## 2. Features
*   **User Management**: Secure authentication, authorization, and user profile management.
*   **Audit & Compliance**: APIs for managing audit processes, checklists, and compliance requirements.
*   **Report Generation**: Dynamic generation of audit reports and certificates (PDF, DOCX).
*   **Template Management**: APIs for creating, updating, and managing various document templates.
*   **Task Scheduling**: Asynchronous task processing and scheduled jobs using Celery and Redis.
*   **Data Filtering & Search**: Advanced querying capabilities for API resources.

## 3. Getting Started

### Prerequisites
Before you begin, ensure you have the following installed:
*   Python 3.8+
*   pip (Python package installer)
*   PostgreSQL (or Docker for a containerized DB)
*   Redis (or Docker for a containerized Redis)
*   Docker and Docker Compose (recommended for development and production)

### Local Development Setup (without Docker)

1.  **Clone the repository**:
    ```bash
    git clone [repository-url]
    cd assurehub/backend_centra
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv backend_env
    source backend_env/bin/activate # On Windows: .\backend_env\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Create a `.env` file in the `backend_centra` directory based on `.env.example`.
    ```ini
    # .env example
    SECRET_KEY='your_secret_key_here'
    DEBUG=True
    DATABASE_URL='postgres://user:password@host:port/database_name'
    REDIS_URL='redis://localhost:6379/0'
    CELERY_BROKER_URL='redis://localhost:6379/0'
    CELERY_RESULT_BACKEND='redis://localhost:6379/0'
    # Add other necessary environment variables
    ```
    For local development, you might start with a SQLite database:
    `DATABASE_URL='sqlite:///db.sqlite3'`

5.  **Run Migrations**:
    ```bash
    python manage.py migrate
    ```

6.  **Create a Superuser**:
    ```bash
    python manage.py createsuperuser
    ```

7.  **Run the Development Server**:
    ```bash
    python manage.py runserver
    ```
    The API will be available at `http://127.0.0.1:8000/`.

8.  **Run Celery Worker (in a separate terminal)**:
    ```bash
    celery -A backend worker -l info
    ```

### Running with Docker Compose (Recommended)

Docker Compose provides a convenient way to run all services (Django, PostgreSQL, Redis, Celery) in isolated containers.

1.  **Ensure Docker and Docker Compose are installed.**

2.  **Configure Environment Variables**:
    Create a `.env` file in the `backend_centra` directory based on `.env.example`.
    Ensure `DATABASE_URL` and `REDIS_URL` point to the respective service names defined in `docker-compose.yml` (e.g., `postgres://user:password@db:5432/dbname`).

3.  **Build and run the services**:
    ```bash
    docker-compose build
    docker-compose up -d
    ```

4.  **Run Migrations (after services are up)**:
    ```bash
    docker-compose exec web python manage.py migrate
    ```

5.  **Create Superuser (optional)**:
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

6.  **Access the application**:
    The Django application will be accessible on `http://localhost:8000`.

## 4. Project Structure
(This section can be expanded with more details about specific app directories if known)
```
backend_centra/
├── apps/               # Django applications (e.g., users, audits, reports)
├── backend/            # Main project settings, URLs, etc.
├── media/              # User-uploaded media files
├── .env.example        # Example environment variables
├── .env                # Local environment variables (ignored by git)
├── Dockerfile          # Docker image definition for the Django app
├── docker-compose.yml  # Docker Compose configuration
├── manage.py           # Django's command-line utility
├── requirements.txt    # Python dependencies
└── ...
```

## 5. Key Technologies
*   **Django**: Web framework
*   **Django REST Framework**: For building APIs
*   **PostgreSQL**: Primary database
*   **Celery**: Asynchronous task queue
*   **Redis**: Message broker for Celery, caching
*   **Gunicorn**: WSGI HTTP Server
*   **Whitenoise**: Serving static files
*   **python-dotenv**: Environment variable management
*   **Pillow**: Image processing
*   **python-docx**: DOCX document generation
*   **reportlab**: PDF document generation

## 6. Deployment
Refer to `DEPLOYMENT.md` (if available) or project-specific documentation for production deployment strategies. Typically involves Docker, a reverse proxy (Nginx), and a process manager (Supervisor, systemd).

## 7. API Documentation
API endpoints are typically documented using tools like OpenAPI/Swagger. Once the server is running, you might find browsable API documentation at `/swagger/` or `/redoc/` if configured.

## 8. Contributing
(Details on how to contribute to the project, coding standards, pull request process, etc.)

## 9. License
(Specify the project's license)
