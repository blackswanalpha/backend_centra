# Use an official Python runtime as a parent image
FROM python:3.10-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# These are often needed for psycopg2-binary to build correctly
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app/

# Collect static files (for production)
# This assumes you have a 'static' directory in your Django project and
# have configured STATIC_ROOT in settings.py
RUN python manage.py collectstatic --noinput

# Expose the port that Gunicorn will listen on
EXPOSE 8000

# Define the command to run the application
# This uses Gunicorn to serve the Django application.
# The `backend.wsgi:application` assumes your project's wsgi.py is in a directory named 'backend'
# If your wsgi.py is directly in 'backend_centra' or another directory, adjust accordingly.
# Workers are typically set to (2 * CPU_CORES) + 1. Here we use 3 for example.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "backend.wsgi:application"]