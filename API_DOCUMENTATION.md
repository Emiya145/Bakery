# Bakery Inventory System - API Documentation

Complete REST API documentation for the Bakery Inventory Management System.

## Base URL

- **Development**: `http://localhost:8000/api/`
- **Production**: `https://yourusername.pythonanywhere.com/api/`

## Authentication

All API endpoints require authentication. Two methods are supported:

### 1. Session Authentication (Web Browsers)
Login via Django admin and use session cookies.

### 2. Token Authentication (API Clients)

First, obtain a token:
```bash
POST /api/auth/token/
{
  "username": "your_username",
  "password": "your_password"
}

Response:
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

Then include in headers:
```
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

## Inventory Endpoints

### Locations

#### List Locations
```http
GET /api/locations/
```

**Query Parameters**:
- `is_active` (boolean): Filter by active status

**Response**:
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Main Kitchen",
      "address": "123 Baker Street",
      "phone": "+1234567890",
      "is_active": true,
      "total_ingredients": 45,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### Get Location Details
```http
GET /api/locations/{id}/
```

#### Create Location
```http
POST /api/locations/
Content-Type: application/json

{
  "name": "Downtown Branch",
  "address": "456 Main St",
  "phone": "+1987654321",
  "is_active": true
}
```

**Permissions**: Manager or Admin

### Ingredients

#### List Ingredients
```http
GET /api/ingredients/
```

**Query Parameters**:
- `unit` (string): Filter by unit (kg, g, L, mL, units, pcs, boxes)
- `is_active` (boolean): Filter by active status
- `low_stock` (boolean): Filter low stock items
- `search` (string): Search by name

**Response**:
```json
{
  "count": 50,
  "results": [
    {
      "id": 1,
      "name": "All-Purpose Flour",
      "unit": "kg",
      "reorder_level": 50.0,
      "cost_per_unit": 2.50,
      "is_active": true,
      "total_stock": 35.5,
      "is_low_stock": true,
      "stock_by_location": [
        {
          "location_id": 1,
          "location_name": "Main Kitchen",
          "quantity": 35.5,
          "batch_number": "BATCH-2024-001",
          "expiration_date": "2024-12-31"
        }
      ],
      "created_at": "2024-01-10T08:00:00Z",
      "updated_at": "2024-03-15T14:30:00Z"
    }
  ]
}
```

#### Get Ingredient Details
```http
GET /api/ingredients/{id}/
```

#### Get Stock History
```http
GET /api/ingredients/{id}/stock_history/
```

**Response**: List of last 50 stock movements for this ingredient.

#### Create Ingredient
```http
POST /api/ingredients/
Content-Type: application/json

{
  "name": "Organic Sugar",
  "unit": "kg",
  "reorder_level": 25.0,
  "cost_per_unit": 3.75,
  "is_active": true
}
```

**Permissions**: Manager or Admin

### Stock

#### List Stock
```http
GET /api/stock/
```

**Query Parameters**:
- `ingredient` (int): Filter by ingredient ID
- `location` (int): Filter by location ID
- `low_stock` (boolean): Filter low stock items
- `expiring_soon` (boolean): Filter items expiring within 7 days
- `expired` (boolean): Filter expired items

**Response**:
```json
{
  "count": 120,
  "results": [
    {
      "id": 1,
      "ingredient": 1,
      "ingredient_name": "All-Purpose Flour",
      "ingredient_unit": "kg",
      "location": 1,
      "location_name": "Main Kitchen",
      "quantity": 35.5,
      "expiration_date": "2024-12-31",
      "batch_number": "BATCH-2024-001",
      "is_low_stock": false,
      "is_expiring_soon": false,
      "is_expired": false,
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-03-19T15:30:00Z"
    }
  ]
}
```

#### Adjust Stock
```http
POST /api/stock/adjust/
Content-Type: application/json

{
  "stock_id": 1,
  "new_quantity": 50.0,
  "reason": "Physical inventory count adjustment"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Stock adjusted from 35.5 to 50.0",
  "movement": {
    "id": 123,
    "movement_type": "ADJUSTMENT",
    "quantity": 14.5,
    "quantity_before": 35.5,
    "quantity_after": 50.0,
    "reason": "Physical inventory count adjustment",
    "created_at": "2024-03-19T16:00:00Z"
  }
}
```

**Permissions**: Manager or Admin

#### Report Waste
```http
POST /api/stock/report_waste/
Content-Type: application/json

{
  "stock_id": 1,
  "quantity": 5.0,
  "reason": "Expired - past use-by date"
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Waste reported: 5.0 kg",
  "movement": {
    "id": 124,
    "movement_type": "WASTE",
    "quantity": 5.0,
    "quantity_before": 50.0,
    "quantity_after": 45.0,
    "reason": "Expired - past use-by date",
    "created_at": "2024-03-19T16:05:00Z"
  }
}
```

**Permissions**: Staff or above

### Stock Movements (Audit Trail)

#### List Movements
```http
GET /api/movements/
```

**Query Parameters**:
- `movement_type` (string): IN, OUT, WASTE, TRANSFER, ADJUSTMENT
- `stock__ingredient` (int): Filter by ingredient ID
- `stock__location` (int): Filter by location ID
- `created_by` (int): Filter by user ID
- `start_date` (date): Filter from date (YYYY-MM-DD)
- `end_date` (date): Filter to date (YYYY-MM-DD)

**Response**:
```json
{
  "count": 500,
  "results": [
    {
      "id": 124,
      "stock": 1,
      "ingredient_name": "All-Purpose Flour",
      "location_name": "Main Kitchen",
      "movement_type": "WASTE",
      "movement_type_display": "Waste",
      "quantity": 5.0,
      "quantity_before": 50.0,
      "quantity_after": 45.0,
      "reason": "Expired - past use-by date",
      "reference": "",
      "created_by": 2,
      "created_by_username": "manager1",
      "created_at": "2024-03-19T16:05:00Z"
    }
  ]
}
```

**Note**: Read-only endpoint. Movements are created automatically by other operations.

### Production

#### Produce Items
```http
POST /api/production/produce/
Content-Type: application/json

{
  "recipe_id": 5,
  "quantity": 20,
  "location_id": 1
}
```

**Description**: Produces items and automatically deducts ingredients using FIFO (oldest stock first).

**Response**:
```json
{
  "status": "success",
  "message": "Produced 20 Sourdough Bread",
  "deductions": [
    {
      "ingredient": "All-Purpose Flour",
      "quantity_used": 10.0,
      "unit": "kg",
      "batch": "BATCH-2024-001"
    },
    {
      "ingredient": "Active Dry Yeast",
      "quantity_used": 0.2,
      "unit": "kg",
      "batch": "BATCH-2024-015"
    }
  ]
}
```

**Error Response** (Insufficient Stock):
```json
{
  "status": "error",
  "message": "Not enough All-Purpose Flour at Main Kitchen. Required: 10.0 kg, Available: 5.0 kg"
}
```

**Permissions**: Staff or above

## Products Endpoints

### Products

#### List Products
```http
GET /api/products/
```

**Query Parameters**:
- `category` (int): Filter by category ID
- `is_active` (boolean): Filter by active status
- `search` (string): Search by name

**Response**:
```json
{
  "count": 25,
  "results": [
    {
      "id": 1,
      "name": "Sourdough Bread",
      "category": 1,
      "category_name": "Bread",
      "unit": "loaves",
      "selling_price": 8.50,
      "cost_price": 3.25,
      "profit_margin": 161.54,
      "is_active": true,
      "description": "Traditional sourdough bread",
      "image": "/media/products/sourdough.jpg",
      "created_at": "2024-01-10T09:00:00Z"
    }
  ]
}
```

## Orders Endpoints

### Customer Orders

#### List Orders
```http
GET /api/orders/
```

**Query Parameters**:
- `status` (string): DRAFT, CONFIRMED, IN_PROGRESS, READY, COMPLETED, CANCELLED
- `priority` (string): LOW, NORMAL, HIGH, URGENT
- `customer` (int): Filter by customer ID

**Response**:
```json
{
  "count": 50,
  "results": [
    {
      "id": 1,
      "order_number": "ORD-2024-001",
      "customer": {
        "id": 1,
        "name": "ABC Cafe",
        "email": "orders@abccafe.com"
      },
      "status": "CONFIRMED",
      "priority": "NORMAL",
      "order_date": "2024-03-19T10:00:00Z",
      "requested_delivery_date": "2024-03-21T08:00:00Z",
      "total_amount": 125.50,
      "items": [
        {
          "product": "Sourdough Bread",
          "quantity": 10,
          "unit_price": 8.50,
          "total_price": 85.00
        }
      ]
    }
  ]
}
```

#### Start Production for Order
```http
POST /api/orders/{id}/start_production/
Content-Type: application/json

{
  "location_id": 1
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Production started for 3 items",
  "batches_created": [
    {
      "batch_number": "ORD-2024-001-1",
      "product": "Sourdough Bread",
      "quantity": 10
    }
  ]
}
```

## Suppliers Endpoints

### Supplier Orders

#### List Supplier Orders
```http
GET /api/supplier-orders/
```

**Query Parameters**:
- `supplier` (int): Filter by supplier ID
- `status` (string): DRAFT, SENT, CONFIRMED, SHIPPED, RECEIVED, CANCELLED

**Response**:
```json
{
  "count": 30,
  "results": [
    {
      "id": 1,
      "order_number": "PO-2024-001",
      "supplier": {
        "id": 1,
        "name": "Flour Mills Inc."
      },
      "status": "CONFIRMED",
      "order_date": "2024-03-15",
      "expected_delivery_date": "2024-03-22",
      "total_amount": 450.00,
      "items": [
        {
          "ingredient": "All-Purpose Flour",
          "quantity": 100.0,
          "unit_price": 2.50,
          "total_price": 250.00
        }
      ]
    }
  ]
}
```

#### Mark Order as Received
```http
POST /api/supplier-orders/{id}/receive/
Content-Type: application/json

{
  "location_id": 1,
  "actual_delivery_date": "2024-03-20"
}
```

**Description**: Marks order as received and automatically adds stock to inventory.

## Error Responses

### 400 Bad Request
```json
{
  "status": "error",
  "message": "Validation error message"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
  "status": "error",
  "message": "Internal server error occurred"
}
```

## Rate Limiting

No rate limiting on free tier. For production, consider implementing rate limiting based on your needs.

## Pagination

All list endpoints support pagination:

**Query Parameters**:
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 20, max: 100)

**Response Format**:
```json
{
  "count": 150,
  "next": "http://api.example.com/api/ingredients/?page=2",
  "previous": null,
  "results": [...]
}
```

## Filtering and Searching

### Search
Use `search` parameter on supported endpoints:
```http
GET /api/ingredients/?search=flour
```

### Ordering
Use `ordering` parameter:
```http
GET /api/ingredients/?ordering=-created_at
GET /api/ingredients/?ordering=name
```

Prefix with `-` for descending order.

## Best Practices

1. **Always use HTTPS in production**
2. **Store tokens securely** - Never commit to version control
3. **Handle errors gracefully** - Check status codes and error messages
4. **Use pagination** - Don't fetch all records at once
5. **Cache responses** - Where appropriate to reduce API calls
6. **Validate input** - Before sending to API
7. **Use atomic operations** - Production endpoint handles transactions automatically
8. **Monitor rate limits** - If implemented in production

## Code Examples

### Python (requests)
```python
import requests

# Authentication
response = requests.post(
    'https://yourusername.pythonanywhere.com/api/auth/token/',
    json={'username': 'admin', 'password': 'password'}
)
token = response.json()['token']

# Get low stock ingredients
headers = {'Authorization': f'Token {token}'}
response = requests.get(
    'https://yourusername.pythonanywhere.com/api/ingredients/?low_stock=true',
    headers=headers
)
ingredients = response.json()['results']

# Produce items
response = requests.post(
    'https://yourusername.pythonanywhere.com/api/production/produce/',
    headers=headers,
    json={
        'recipe_id': 5,
        'quantity': 20,
        'location_id': 1
    }
)
result = response.json()
```

### JavaScript (fetch)
```javascript
// Authentication
const response = await fetch('https://yourusername.pythonanywhere.com/api/auth/token/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({username: 'admin', password: 'password'})
});
const {token} = await response.json();

// Get ingredients
const ingredientsResponse = await fetch(
  'https://yourusername.pythonanywhere.com/api/ingredients/',
  {headers: {'Authorization': `Token ${token}`}}
);
const ingredients = await ingredientsResponse.json();

// Report waste
const wasteResponse = await fetch(
  'https://yourusername.pythonanywhere.com/api/stock/report_waste/',
  {
    method: 'POST',
    headers: {
      'Authorization': `Token ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      stock_id: 1,
      quantity: 5.0,
      reason: 'Expired'
    })
  }
);
```

## Webhooks

Not currently supported. Consider implementing if needed for real-time notifications.

## API Versioning

Current version: v1 (implicit)

Future versions will use URL versioning:
- `/api/v1/ingredients/`
- `/api/v2/ingredients/`

## Support

For API issues or questions:
- Check error logs
- Review this documentation
- Contact system administrator
