# Backend Setup Guide

## ✅ Environment Setup Complete!

The backend virtual environment has been properly configured with all required packages.

---

## 📦 Virtual Environment Details

**Location:** `backend_centra/backend_env/`
**Python Version:** 3.12.3
**Django Version:** 5.1
**Package Manager:** pip 25.3

---

## 📚 Installed Packages

All packages from `requirements.txt` are installed:

| Package | Version | Purpose |
|---------|---------|---------|
| Django | 5.1 | Web framework |
| djangorestframework | 3.15.2 | REST API framework |
| django-cors-headers | 4.6.0 | CORS support |
| python-dotenv | 1.0.0 | Environment variables |
| psycopg2-binary | 2.9.10 | PostgreSQL adapter |
| celery | 5.4.0 | Task queue |
| redis | 5.2.0 | Cache/message broker |
| Pillow | 10.4.0 | Image processing |
| django-filter | 24.3 | Filtering support |
| dj-database-url | 2.2.0 | Database URL parsing |
| gunicorn | 23.0.0 | WSGI server |
| whitenoise | 6.8.2 | Static file serving |
| pyotp | 2.9.0 | 2FA/TOTP support |

---

## 🚀 Quick Start

### Activate Environment and Run Server

```bash
cd backend_centra
source backend_env/bin/activate
python manage.py runserver 8060
```

That's it! The server will start on port 8060.

---

## 🔧 Common Django Commands

All commands should be run from the `backend_centra` directory with the virtual environment activated.

### Activate Environment First

```bash
cd backend_centra
source backend_env/bin/activate
```

You'll see `(backend_env)` in your prompt:
```
(backend_env) user@machine:~/backend_centra$
```

### Then Run Django Commands

```bash
# Run server
python manage.py runserver 8060

# Run migrations
python manage.py migrate

# Create migrations
python manage.py makemigrations

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell

# Check for issues
python manage.py check

# Run tests
python manage.py test
```

---

## 📝 Environment Activation

### Activate Virtual Environment

```bash
cd backend_centra
source backend_env/bin/activate
```

**You'll see:**
```
(backend_env) user@machine:~/backend_centra$
```

### Deactivate Virtual Environment

When you're done working:
```bash
deactivate
```

---

## 🔍 Verify Installation

First, activate the environment:
```bash
cd backend_centra
source backend_env/bin/activate
```

### Check Python Version

```bash
python --version
# Output: Python 3.12.3
```

### Check Django Version

```bash
django-admin --version
# Output: 5.1
```

### List All Packages

```bash
pip list
```

### Check Django Installation

```bash
python manage.py check
# Output: System check identified no issues (0 silenced).
```

### Check Migrations Status

```bash
python manage.py showmigrations
```

---

## 🛠️ Package Management

First, activate the environment:
```bash
cd backend_centra
source backend_env/bin/activate
```

### Install New Package

```bash
pip install package-name
```

### Add to requirements.txt

```bash
pip freeze > requirements.txt
```

### Update Package

```bash
pip install --upgrade package-name
```

### Reinstall All Packages

```bash
pip install -r requirements.txt
```

### Reinstall Specific Package

```bash
pip install --force-reinstall package-name
```

---

## 🔄 Recreate Virtual Environment

If you need to recreate the environment:

```bash
cd backend_centra

# Backup old environment
mv backend_env backend_env_backup

# Create new environment
python3 -m venv backend_env

# Upgrade pip
./backend_env/bin/pip install --upgrade pip

# Install all packages
./backend_env/bin/pip install -r requirements.txt

# Verify installation
./backend_env/bin/python manage.py check

# Remove backup if everything works
rm -rf backend_env_backup
```

---

## 📊 Database Management

First, activate the environment:
```bash
cd backend_centra
source backend_env/bin/activate
```

### Run Migrations

```bash
python manage.py migrate
```

### Create Migrations

```bash
python manage.py makemigrations
```

### Show Migration Status

```bash
python manage.py showmigrations
```

### Migrate Specific App

```bash
python manage.py migrate authentication
```

---

## 👤 User Management

First, activate the environment:
```bash
cd backend_centra
source backend_env/bin/activate
```

### Create Admin User

```bash
# Interactive script
python create_admin.py

# Or Django's createsuperuser
python manage.py createsuperuser
```

### Django Shell

```bash
python manage.py shell
```

Then in the shell:

```python
from django.contrib.auth.models import User
from apps.authentication.models import UserProfile

# List all users
User.objects.all()

# Get specific user
user = User.objects.get(username='admin')

# Check user profile
user.profile.role
user.profile.email_verified
```

---

## 🧪 Testing

First, activate the environment:
```bash
cd backend_centra
source backend_env/bin/activate
```

### Run All Tests

```bash
python manage.py test
```

### Run Specific App Tests

```bash
python manage.py test apps.authentication
```

### Run with Verbosity

```bash
python manage.py test --verbosity=2
```

---

## 🐛 Troubleshooting

### Issue: Virtual environment not found

**Solution:**
```bash
python3 -m venv backend_env
./backend_env/bin/pip install -r requirements.txt
```

### Issue: Module not found

**Solution:**
```bash
./backend_env/bin/pip install -r requirements.txt
```

### Issue: Port already in use

**Solution:**
```bash
# Find process on port 8060
lsof -ti:8060

# Kill process
lsof -ti:8060 | xargs kill -9

# Or use different port
python manage.py runserver 8061
```

### Issue: Database locked

**Solution:**
```bash
# If using SQLite
rm db.sqlite3
./backend_env/bin/python manage.py migrate
```

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `backend_env/` | Virtual environment directory |
| `requirements.txt` | Python package dependencies |
| `manage.py` | Django management script |
| `create_admin.py` | Admin user creation script |
| `db.sqlite3` | SQLite database (development) |

---

## 🔐 Environment Variables

Create a `.env` file in `backend_centra/` for sensitive settings:

```bash
# .env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgresql://user:pass@localhost/dbname
FRONTEND_URL=http://localhost:30000
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password
```

---

## ✅ Verification Checklist

- [x] Virtual environment created
- [x] All packages installed from requirements.txt
- [x] Django 5.1 installed
- [x] DRF 3.15.2 installed
- [x] pyotp 2.9.0 installed (for 2FA)
- [x] Pillow 10.4.0 installed (for images)
- [x] All migrations applied
- [x] System check passes
- [x] Server runs successfully
- [x] Helper scripts created and executable

---

## 🎯 Next Steps

1. **Activate environment and start the server:**
   ```bash
   cd backend_centra
   source backend_env/bin/activate
   python manage.py runserver 8060
   ```

2. **Access the API:**
   - API: http://localhost:8060/api/v1
   - Admin: http://localhost:8060/admin/

3. **Test authentication:**
   - Login: POST http://localhost:8060/api/v1/auth/login/
   - Register: POST http://localhost:8060/api/v1/auth/register/

4. **Create test users:**
   ```bash
   python create_admin.py
   ```

---

**Setup completed successfully!** 🎉

All packages are installed in the virtual environment and Django is ready to use.

