# Django Backend Quick Reference

## 🚀 Start Server

```bash
cd backend_centra
source backend_env/bin/activate
python manage.py runserver 8060
```

---

## 🔧 Common Commands

**First, activate the environment:**
```bash
cd backend_centra
source backend_env/bin/activate
```

You'll see: `(backend_env) user@machine:~/backend_centra$`

### Server Management
```bash
# Start server
python manage.py runserver 8060

# Start on different port
python manage.py runserver 8000

# Check for issues
python manage.py check
```

### Database
```bash
# Run migrations
python manage.py migrate

# Create migrations
python manage.py makemigrations

# Show migration status
python manage.py showmigrations
```

### User Management
```bash
# Create admin user (interactive)
python create_admin.py

# Django superuser
python manage.py createsuperuser

# Django shell
python manage.py shell
```

### Package Management
```bash
# Install package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt

# Install from requirements
pip install -r requirements.txt

# List packages
pip list
```

---

## 🌐 URLs

- **API Base:** http://localhost:8060/api/v1
- **Admin Panel:** http://localhost:8060/admin/
- **Auth Login:** http://localhost:8060/api/v1/auth/login/
- **Auth Register:** http://localhost:8060/api/v1/auth/register/

---

## 🔐 Admin Credentials

```
Username: admin
Password: Admin@123
Email: admin@assurehub.com
```

---

## 📦 Environment

```
Location: backend_centra/backend_env/
Python: 3.12.3
Django: 5.1
Packages: 31 installed
```

---

## 🧪 Quick API Test

```bash
# Login
curl -X POST http://localhost:8060/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123"}'

# Get current user (replace TOKEN)
curl -X GET http://localhost:8060/api/v1/auth/me/ \
  -H "Authorization: Token TOKEN"
```

---

## 🛠️ Troubleshooting

```bash
# Port in use
lsof -ti:8060 | xargs kill -9

# Reinstall packages (with environment activated)
pip install -r requirements.txt

# Deactivate environment
deactivate
```

---

## 📚 Documentation

- **SETUP_GUIDE.md** - Complete setup instructions
- **QUICK_REFERENCE.md** - This file

---

## 💡 Remember

Always activate the environment before running Django commands:
```bash
source backend_env/bin/activate
```

When done, deactivate:
```bash
deactivate
```

