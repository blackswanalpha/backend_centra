# Project Explanation: backend_centra

`backend_centra` is the core backend service for the AssureHub platform, built using the Django REST Framework. It provides a robust, scalable, and secure API layer to support various functionalities, including:

## Architecture Overview
The project follows a modular architecture, leveraging Django's MVT (Model-View-Template) pattern, adapted for an API-first approach using Django REST Framework. Key components include:
-   **Django Core**: Manages URL routing, middleware, and project settings.
-   **Django REST Framework**: Provides tools for building Web APIs, including serializers, viewsets, and authentication/permission classes.
-   **Database**: Primarily designed to work with PostgreSQL (via `psycopg2-binary`), though `db.sqlite3` is present for local development.
-   **Celery**: A distributed task queue system used for handling asynchronous tasks and scheduled jobs (e.g., report generation, email notifications).
-   **Redis**: Used as a message broker for Celery and potentially for caching.
-   **Gunicorn**: A WSGI HTTP server used to run the Django application in production.
-   **Whitenoise**: Serves static files efficiently in production.

## Key Features
-   **API Endpoints**: Exposes RESTful APIs for managing users, organizations, audit data, reports, templates, and other core business entities.
-   **Authentication & Authorization**: Secure user authentication (including OTP via `pyotp`) and role-based authorization to control access to resources.
-   **Data Filtering**: Integrates `django-filter` for advanced query capabilities on API endpoints.
-   **Document Generation**: Utilizes `python-docx` and `reportlab` for generating dynamic documents and PDFs, likely for audit reports and certificates.
-   **Rate Limiting**: Implements `django-ratelimit` to protect APIs from abuse.
-   **Environment Configuration**: Uses `python-dotenv` for managing environment-specific settings.

## Modules and Structure (Assumed based on typical Django projects and provided `requirements.txt`)
-   **`apps/`**: Contains various Django applications (e.g., `users`, `audits`, `reports`, `templates`, `certifications`), each encapsulating related models, views, serializers, and URLs.
-   **`backend/`**: Likely contains the main project settings, URL configurations, and potentially common utilities.
-   **`media/`**: Directory for user-uploaded media files.
-   **`db.sqlite3`**: Default SQLite database file, often used for development.

## Development Environment
-   **Python**: The project is built with Python.
-   **Virtual Environments**: Encourages the use of virtual environments (`backend_env/`) to manage dependencies.
-   **Docker**: The presence of `Dockerfile` and `docker-compose.yml` indicates support for containerized development and deployment, ensuring consistency across environments.

This project forms the backbone of the AssureHub system, providing the necessary data processing, storage, and API capabilities for its frontend applications.