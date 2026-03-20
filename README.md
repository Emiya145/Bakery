# Bakery Inventory Management System

A comprehensive Django-based inventory management system for bakeries, designed for deployment on PythonAnywhere free tier with WSGI-only architecture.

## Features

- **Ingredient Inventory Tracking** - Track flour, sugar, eggs, and all ingredients with expiration dates
- **Product Recipes** - Define ingredient-to-product mappings with automatic cost calculations
- **Automatic Inventory Deduction** - Deduct ingredients when products are produced/sold
- **Low-Stock Alerts** - Automated alerts and restocking recommendations
- **Supplier Management** - Track vendors, pricing history, and delivery times
- **Order Tracking** - Manage customer and supplier orders
- **Expiration Tracking** - FIFO-based expiration management for perishable ingredients
- **Production Logs** - Daily production batch tracking
- **Waste Tracking** - Track expired/discarded inventory
- **Multi-Location Support** - Manage inventory across multiple bakery locations
- **Role-Based Access Control** - Admin, Manager, and Staff roles with appropriate permissions
- **RESTful API** - Full DRF API for external integrations
- **Audit Logging** - Complete audit trail for all inventory movements

## Tech Stack

- **Backend**: Django 4.2.7
- **API**: Django REST Framework
- **Database**: SQLite (dev) / MySQL (production)
- **Deployment**: PythonAnywhere (WSGI-compatible)
- **Architecture**: Modular Monolith

## Project Structure

```
bakery/
├── bakery/              # Project settings
│   ├── settings/
│   │   ├── base.py      # Shared settings
│   │   ├── dev.py       # Development settings
│   │   └── prod.py      # Production settings
│   ├── urls.py
│   └── wsgi.py
├── inventory/           # Ingredient stock management
│   ├── models.py        # Location, Ingredient, Stock, StockMovement
│   ├── services.py      # Atomic transaction services
│   ├── admin.py         # Admin customizations
│   ├── serializers.py   # DRF serializers
│   ├── views.py         # API viewsets
│   └── management/
│       └── commands/    # Background task commands
├── products/            # Finished goods
│   ├── models.py        # Product, ProductCategory, ProductStock
│   └── admin.py
├── recipes/             # Recipe management
│   ├── models.py        # Recipe, RecipeIngredient, ProductionBatch
│   └── admin.py
├── orders/              # Customer orders
│   ├── models.py        # Customer, CustomerOrder, CustomerOrderItem
│   └── admin.py
├── suppliers/           # Supplier management
│   ├── models.py        # Supplier, SupplierPrice, SupplierOrder
│   └── admin.py
├── users/               # User management
│   ├── models.py        # Custom User with roles
│   ├── permissions.py   # RBAC permissions
│   └── serializers.py
└── audit/               # Audit logging
    └── models.py        # AuditLog
```

## Installation

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Bakery
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create .env file**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your settings:
   ```
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   DJANGO_SETTINGS_MODULE=bakery.settings.dev
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Create cache table** (for database-backed caching)
   ```bash
   python manage.py createcachetable
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

9. **Access the application**
   - Admin: http://localhost:8000/admin/
   - API: http://localhost:8000/api/

## PythonAnywhere Deployment

### Prerequisites
- PythonAnywhere free account
- Git repository with your code

### Step-by-Step Deployment

1. **Create MySQL Database**
   - Go to PythonAnywhere Dashboard → Databases
   - Initialize MySQL (if not already done)
   - Create database: `yourusername$bakery`
   - Note the database credentials

2. **Clone Repository**
   ```bash
   cd ~
   git clone <your-repo-url> bakery
   cd bakery
   ```

3. **Create Virtual Environment**
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 bakery-env
   workon bakery-env
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Create `.env` file in project root:
   ```bash
   nano .env
   ```
   
   Add:
   ```
   SECRET_KEY=your-production-secret-key
   DEBUG=False
   DJANGO_SETTINGS_MODULE=bakery.settings.prod
   DB_NAME=yourusername$bakery
   DB_USER=yourusername
   DB_PASSWORD=your-mysql-password
   DB_HOST=yourusername.mysql.pythonanywhere-services.com
   ```

5. **Run Migrations**
   ```bash
   python manage.py migrate
   python manage.py createcachetable
   python manage.py createsuperuser
   ```

6. **Collect Static Files**
   ```bash
   python manage.py collectstatic --noinput
   ```

7. **Configure Web App**
   - Go to Web tab → Add a new web app
   - Choose "Manual configuration" (not Django wizard)
   - Python version: 3.10
   
   **WSGI Configuration** (`/var/www/yourusername_pythonanywhere_com_wsgi.py`):
   ```python
   import os
   import sys
   
   # Add project directory to path
   path = '/home/yourusername/bakery'
   if path not in sys.path:
       sys.path.insert(0, path)
   
   # Set environment variables
   os.environ['DJANGO_SETTINGS_MODULE'] = 'bakery.settings.prod'
   
   # Load environment variables from .env
   from pathlib import Path
   env_file = Path(path) / '.env'
   if env_file.exists():
       with open(env_file) as f:
           for line in f:
               if line.strip() and not line.startswith('#'):
                   key, value = line.strip().split('=', 1)
                   os.environ.setdefault(key, value)
   
   # Import Django WSGI application
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```

8. **Configure Static Files**
   In Web tab → Static files section:
   - URL: `/static/`
   - Directory: `/home/yourusername/bakery/staticfiles/`

9. **Configure Virtual Environment**
   In Web tab → Virtualenv section:
   - Enter: `/home/yourusername/.virtualenvs/bakery-env`

10. **Reload Web App**
    - Click "Reload" button in Web tab

### Schedule Background Tasks

Go to Tasks tab and add:

```bash
# Daily at 8:00 AM - Check low stock
0 8 * * * cd /home/yourusername/bakery && /home/yourusername/.virtualenvs/bakery-env/bin/python manage.py check_low_stock --send-email

# Daily at 7:00 AM - Check expiring stock
0 7 * * * cd /home/yourusername/bakery && /home/yourusername/.virtualenvs/bakery-env/bin/python manage.py check_expiring_stock --send-email

# Weekly on Monday at 9:00 AM - Weekly summary
0 9 * * 1 cd /home/yourusername/bakery && /home/yourusername/.virtualenvs/bakery-env/bin/python manage.py weekly_summary --send-email
```

**Note**: PythonAnywhere free tier allows only 1 scheduled task per day. Upgrade to paid tier for multiple tasks.

## API Documentation

### Authentication

All API endpoints require authentication. Use one of:
- Session Authentication (for web browsers)
- Token Authentication (for API clients)

### Endpoints

#### Inventory

- `GET /api/ingredients/` - List all ingredients
- `GET /api/ingredients/?low_stock=true` - Filter low stock items
- `GET /api/ingredients/{id}/` - Get ingredient details
- `POST /api/ingredients/` - Create ingredient (Manager+)
- `GET /api/ingredients/{id}/stock_history/` - Get stock movement history

- `GET /api/stock/` - List all stock
- `GET /api/stock/?expiring_soon=true` - Filter expiring stock
- `GET /api/stock/?expired=true` - Filter expired stock
- `POST /api/stock/adjust/` - Adjust stock quantity (Manager+)
- `POST /api/stock/report_waste/` - Report waste

- `GET /api/movements/` - List stock movements (audit trail)
- `GET /api/movements/?start_date=2024-01-01&end_date=2024-12-31` - Filter by date

- `POST /api/production/produce/` - Produce items and deduct ingredients

#### Example: Production Request

```json
POST /api/production/produce/
{
  "recipe_id": 5,
  "quantity": 20,
  "location_id": 1
}

Response:
{
  "status": "success",
  "message": "Produced 20 Sourdough Bread",
  "deductions": [
    {
      "ingredient": "All-Purpose Flour",
      "quantity_used": 10.0,
      "unit": "kg",
      "batch": "BATCH-2024-001"
    }
  ]
}
```

## Management Commands

### Check Low Stock
```bash
python manage.py check_low_stock --send-email
```

### Check Expiring Stock
```bash
python manage.py check_expiring_stock --days 7 --send-email
```

### Weekly Summary
```bash
python manage.py weekly_summary --send-email
```

## User Roles & Permissions

| Action | Admin | Manager | Staff |
|--------|-------|---------|-------|
| View inventory | ✓ | ✓ | ✓ (own location) |
| Deduct stock (production) | ✓ | ✓ | ✓ |
| Adjust stock | ✓ | ✓ | ✗ |
| Manage suppliers | ✓ | ✓ | ✗ |
| Manage users | ✓ | ✗ | ✗ |
| View audit logs | ✓ | ✓ (own location) | ✗ |
| Create/edit recipes | ✓ | ✓ | ✗ |
| Manage orders | ✓ | ✓ | ✓ (view only) |

## Key Features Explained

### Atomic Inventory Operations

All inventory operations use Django's `@transaction.atomic` decorator with `select_for_update()` to prevent race conditions:

```python
@transaction.atomic
def deduct_for_production(self, recipe, quantity_produced, location, user):
    stock_batches = Stock.objects.select_for_update().filter(
        ingredient=recipe_ingredient.ingredient,
        location=location
    ).order_by('expiration_date')  # FIFO
    
    # Atomic update using F() expressions
    stock.quantity = F('quantity') - qty_to_deduct
    stock.save(update_fields=['quantity'])
```

### FIFO Expiration Management

Stock is automatically deducted from oldest batches first (First In, First Out):
- Batches ordered by `expiration_date`, then `created_at`
- Prevents waste by using soon-to-expire items first

### Audit Trail

Every stock movement is logged in `StockMovement` with:
- Quantity before and after
- Movement type (IN, OUT, WASTE, TRANSFER, ADJUSTMENT)
- Reason and reference
- User who performed the action
- Timestamp

## Database Schema Highlights

### Key Indexes
- `ingredient` + `location` (for fast stock lookups)
- `expiration_date` (for expiration queries)
- `created_at` (for audit logs)
- `movement_type` + `created_at` (for reporting)

### Constraints
- Unique together: `ingredient` + `location` + `batch_number`
- Minimum validators on quantities (prevent negative stock)
- Foreign key protection (PROTECT on critical relations)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Required |
| `DEBUG` | Debug mode | `False` |
| `DJANGO_SETTINGS_MODULE` | Settings module | `bakery.settings.dev` |
| `DB_NAME` | Database name | `bakery` |
| `DB_USER` | Database user | `root` |
| `DB_PASSWORD` | Database password | - |
| `DB_HOST` | Database host | `localhost` |
| `EMAIL_HOST` | SMTP host | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | SMTP username | - |
| `EMAIL_HOST_PASSWORD` | SMTP password | - |

## Troubleshooting

### Issue: Migrations fail on PythonAnywhere
**Solution**: Ensure MySQL database is created and credentials in `.env` are correct.

### Issue: Static files not loading
**Solution**: Run `python manage.py collectstatic` and verify static files mapping in Web tab.

### Issue: "No module named 'decouple'"
**Solution**: Activate virtual environment and run `pip install -r requirements.txt`.

### Issue: Permission denied errors
**Solution**: Check file permissions. PythonAnywhere requires specific permissions for certain directories.

## Development Workflow

1. Create feature branch
2. Make changes locally
3. Test with SQLite: `python manage.py test`
4. Test with MySQL (if possible)
5. Commit and push
6. Pull on PythonAnywhere: `git pull origin main`
7. Run migrations: `python manage.py migrate`
8. Collect static: `python manage.py collectstatic --noinput`
9. Reload web app

## Future Enhancements

- **Celery Integration**: Upgrade to paid tier and add Celery for real-time background tasks
- **Redis Caching**: Add Redis for improved performance
- **Mobile App**: React Native app using the DRF API
- **Advanced Reporting**: Sales analytics, profit margins, ingredient usage trends
- **Barcode Scanning**: Mobile barcode scanning for inventory management
- **Multi-Currency**: Support for multiple currencies in pricing

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub or contact [your-email@example.com].
