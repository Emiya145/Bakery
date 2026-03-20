# PythonAnywhere Deployment Guide

Complete step-by-step guide for deploying the Bakery Inventory System to PythonAnywhere free tier.

## Prerequisites

- PythonAnywhere free account (sign up at https://www.pythonanywhere.com)
- Git repository with your code
- Email account for alerts (Gmail, etc.)

## Part 1: Database Setup

### 1.1 Initialize MySQL

1. Log into PythonAnywhere
2. Go to **Databases** tab
3. Click **Initialize MySQL** (if not already done)
4. Set a MySQL password and remember it

### 1.2 Create Database

In the Databases tab:
```sql
CREATE DATABASE yourusername$bakery CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Or use the web interface to create database named: `yourusername$bakery`

**Note**: Replace `yourusername` with your actual PythonAnywhere username.

## Part 2: Code Deployment

### 2.1 Clone Repository

Open a Bash console:
```bash
cd ~
git clone https://github.com/yourusername/Bakery.git bakery
cd bakery
```

### 2.2 Create Virtual Environment

```bash
mkvirtualenv --python=/usr/bin/python3.10 bakery-env
workon bakery-env
```

### 2.3 Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: If you encounter errors with `mysqlclient`, you may need to install system dependencies first (usually pre-installed on PythonAnywhere).

## Part 3: Configuration

### 3.1 Create Environment File

Create `.env` file in project root:
```bash
nano .env
```

Add the following (replace with your actual values):
```env
# Django Settings
SECRET_KEY=your-very-long-random-secret-key-here-change-this
DEBUG=False
DJANGO_SETTINGS_MODULE=bakery.settings.prod
ALLOWED_HOSTS=yourusername.pythonanywhere.com

# Database Configuration
DB_NAME=yourusername$bakery
DB_USER=yourusername
DB_PASSWORD=your-mysql-password-here
DB_HOST=yourusername.mysql.pythonanywhere-services.com

# Email Configuration (for alerts)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-specific-password
DEFAULT_FROM_EMAIL=noreply@yourbakery.com
INVENTORY_ALERT_EMAIL=manager@yourbakery.com
```

**Security Notes**:
- Generate a strong SECRET_KEY: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- For Gmail, use an App Password (not your regular password): https://support.google.com/accounts/answer/185833
- Never commit `.env` to version control

Save and exit: `Ctrl+X`, then `Y`, then `Enter`

### 3.2 Update Production Settings

Verify `bakery/settings/prod.py` has correct configuration:
```python
from .base import *
import os

DEBUG = False
ALLOWED_HOSTS = [os.environ.get('ALLOWED_HOSTS', 'yourusername.pythonanywhere.com')]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    }
}

STATIC_ROOT = '/home/yourusername/bakery/staticfiles'
MEDIA_ROOT = '/home/yourusername/bakery/media'
```

## Part 4: Database Migration

### 4.1 Run Migrations

```bash
python manage.py migrate
```

You should see output like:
```
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  ...
```

### 4.2 Create Cache Table

```bash
python manage.py createcachetable
```

### 4.3 Create Superuser

```bash
python manage.py createsuperuser
```

Enter username, email, and password when prompted.

### 4.4 Collect Static Files

```bash
mkdir -p staticfiles
python manage.py collectstatic --noinput
```

## Part 5: Web App Configuration

### 5.1 Create Web App

1. Go to **Web** tab
2. Click **Add a new web app**
3. Choose **Manual configuration** (NOT Django wizard)
4. Select **Python 3.10**

### 5.2 Configure WSGI File

Click on WSGI configuration file link (e.g., `/var/www/yourusername_pythonanywhere_com_wsgi.py`)

Replace entire content with:

```python
import os
import sys

# Add your project directory to the sys.path
path = '/home/yourusername/bakery'
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variable for Django settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'bakery.settings.prod'

# Load environment variables from .env file
from pathlib import Path
from dotenv import load_dotenv

env_file = Path(path) / '.env'
if env_file.exists():
    load_dotenv(env_file)

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**Important**: Replace `yourusername` with your actual username.

Save the file.

### 5.3 Configure Virtual Environment

In the Web tab, scroll to **Virtualenv** section:
- Enter: `/home/yourusername/.virtualenvs/bakery-env`

### 5.4 Configure Static Files

In the Web tab, scroll to **Static files** section:

Add entry:
- URL: `/static/`
- Directory: `/home/yourusername/bakery/staticfiles/`

Add another entry:
- URL: `/media/`
- Directory: `/home/yourusername/bakery/media/`

### 5.5 Reload Web App

Click the green **Reload** button at the top of the Web tab.

### 5.6 Test the Application

Visit: `https://yourusername.pythonanywhere.com/admin/`

You should see the Django admin login page. Log in with your superuser credentials.

## Part 6: Scheduled Tasks (Background Jobs)

### 6.1 Understanding Free Tier Limitations

PythonAnywhere free tier allows **only 1 scheduled task per day**.

Choose the most important task for your bakery:
- **Option A**: Low stock check (recommended)
- **Option B**: Expiring stock check
- **Option C**: Weekly summary

### 6.2 Configure Scheduled Task

Go to **Tasks** tab and add:

**Option A - Daily Low Stock Check (8:00 AM UTC)**
```bash
cd /home/yourusername/bakery && /home/yourusername/.virtualenvs/bakery-env/bin/python manage.py check_low_stock --send-email
```

**Option B - Daily Expiring Stock Check (7:00 AM UTC)**
```bash
cd /home/yourusername/bakery && /home/yourusername/.virtualenvs/bakery-env/bin/python manage.py check_expiring_stock --send-email
```

**Option C - Weekly Summary (Monday 9:00 AM UTC)**
```bash
cd /home/yourusername/bakery && /home/yourusername/.virtualenvs/bakery-env/bin/python manage.py weekly_summary --send-email
```

Set the time in UTC (convert from your local timezone).

**Note**: To run multiple tasks, upgrade to a paid PythonAnywhere account.

### 6.3 Manual Task Execution

You can manually run any command via Bash console:

```bash
cd ~/bakery
workon bakery-env
python manage.py check_low_stock --send-email
python manage.py check_expiring_stock --days 7 --send-email
python manage.py weekly_summary --send-email
```

## Part 7: Initial Data Setup

### 7.1 Create Locations

Via Django Admin (`/admin/inventory/location/`):
1. Add your bakery location(s)
   - Name: "Main Kitchen"
   - Address: Your address
   - Mark as active

### 7.2 Create User Accounts

Via Django Admin (`/admin/users/user/`):
1. Create Manager accounts
2. Create Staff accounts
3. Assign appropriate roles and locations

### 7.3 Add Ingredients

Via Django Admin (`/admin/inventory/ingredient/`):
1. Add common ingredients:
   - All-Purpose Flour (kg)
   - Sugar (kg)
   - Eggs (units)
   - Butter (kg)
   - etc.
2. Set reorder levels for each

### 7.4 Add Product Categories

Via Django Admin (`/admin/products/productcategory/`):
1. Bread
2. Pastries
3. Cakes
4. etc.

### 7.5 Add Products

Via Django Admin (`/admin/products/product/`):
1. Create products with pricing
2. Assign to categories

### 7.6 Create Recipes

Via Django Admin (`/admin/recipes/recipe/`):
1. Create recipe for each product
2. Add ingredients with quantities
3. Mark as active

## Part 8: Testing

### 8.1 Test Admin Interface

1. Log into admin
2. Navigate through all sections
3. Create test stock entry
4. Create test production batch

### 8.2 Test API

Using curl or Postman:

```bash
# Get ingredients (requires authentication)
curl -X GET https://yourusername.pythonanywhere.com/api/ingredients/ \
  -H "Authorization: Token your-api-token"

# Get low stock items
curl -X GET https://yourusername.pythonanywhere.com/api/ingredients/?low_stock=true \
  -H "Authorization: Token your-api-token"
```

### 8.3 Test Management Commands

```bash
cd ~/bakery
workon bakery-env
python manage.py check_low_stock
python manage.py check_expiring_stock --days 7
```

## Part 9: Maintenance

### 9.1 Updating Code

When you push changes to GitHub:

```bash
cd ~/bakery
git pull origin main
workon bakery-env
pip install -r requirements.txt  # If dependencies changed
python manage.py migrate  # If models changed
python manage.py collectstatic --noinput  # If static files changed
```

Then reload web app from Web tab.

### 9.2 Database Backups

PythonAnywhere doesn't provide automatic backups on free tier. Export manually:

```bash
mysqldump -u yourusername -h yourusername.mysql.pythonanywhere-services.com \
  -p yourusername$bakery > backup_$(date +%Y%m%d).sql
```

### 9.3 Viewing Logs

**Error Logs**: Web tab → Log files → Error log
**Server Logs**: Web tab → Log files → Server log
**Application Logs**: Check `~/bakery/logs/` directory

### 9.4 Monitoring

Check regularly:
- Error logs for issues
- Database size (free tier has 512MB limit)
- CPU usage (free tier has daily limit)

## Part 10: Troubleshooting

### Issue: "DisallowedHost" Error

**Solution**: Add your domain to `ALLOWED_HOSTS` in `.env`:
```env
ALLOWED_HOSTS=yourusername.pythonanywhere.com
```

### Issue: Static Files Not Loading

**Solution**:
1. Run `python manage.py collectstatic --noinput`
2. Verify static files mapping in Web tab
3. Check `STATIC_ROOT` in `prod.py`

### Issue: Database Connection Error

**Solution**:
1. Verify MySQL credentials in `.env`
2. Check database exists: `SHOW DATABASES;` in MySQL console
3. Ensure database name format: `yourusername$bakery`

### Issue: Import Errors

**Solution**:
1. Activate virtual environment: `workon bakery-env`
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Check WSGI file has correct path

### Issue: 500 Internal Server Error

**Solution**:
1. Check error log in Web tab
2. Verify `.env` file exists and has correct values
3. Check `DEBUG=False` in production
4. Ensure all migrations are applied

### Issue: Email Alerts Not Sending

**Solution**:
1. Verify email credentials in `.env`
2. For Gmail, use App Password
3. Check email settings in `base.py`
4. Test manually: `python manage.py check_low_stock --send-email`

## Part 11: Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` generated
- [ ] `.env` file not in version control (add to `.gitignore`)
- [ ] Database password is strong
- [ ] Email uses App Password (not regular password)
- [ ] HTTPS enabled (automatic on PythonAnywhere)
- [ ] Admin URL not exposed publicly (consider changing from `/admin/`)
- [ ] Regular backups scheduled
- [ ] User permissions properly configured

## Part 12: Going Live

### Pre-Launch Checklist

- [ ] All locations created
- [ ] All users created with correct roles
- [ ] All ingredients added with reorder levels
- [ ] All products and recipes created
- [ ] Initial stock entered
- [ ] Scheduled task configured
- [ ] Email alerts tested
- [ ] Admin interface tested
- [ ] API tested (if using)
- [ ] Backup procedure established

### Post-Launch

1. Monitor error logs daily for first week
2. Verify scheduled tasks are running
3. Check email alerts are being received
4. Train staff on using the system
5. Gather feedback and iterate

## Upgrading to Paid Tier

Benefits of upgrading:
- Multiple scheduled tasks (hourly cron jobs)
- More CPU time per day
- Larger database (1GB+)
- Custom domain support
- Always-on tasks
- SSH access

Cost: Starting at $5/month

## Support Resources

- PythonAnywhere Help: https://help.pythonanywhere.com/
- Django Documentation: https://docs.djangoproject.com/
- DRF Documentation: https://www.django-rest-framework.org/

## Conclusion

Your bakery inventory system is now deployed and ready to use! Access it at:
- **Admin**: https://yourusername.pythonanywhere.com/admin/
- **API**: https://yourusername.pythonanywhere.com/api/

For questions or issues, refer to the troubleshooting section or check the error logs.
