# Frontend Architecture Blueprint — Bakery Inventory Management System

> **Mode**: Architecture & Design Only — no full implementations, no scaffolding.
> **Backend**: Django 6.0 + Django REST Framework
> **Target Deployment**: Static build served via Django on PythonAnywhere free tier

---

## 1. Frontend Overview

### System Purpose
A single-page application that provides bakery staff, managers, and administrators with a responsive interface for managing inventory, production, orders, and suppliers. The frontend consumes the existing DRF API and renders role-appropriate views.

### Design Principles

| Principle | Implementation |
|---|---|
| **Modularity** | Feature-based folder structure; each domain (inventory, recipes, orders…) is self-contained |
| **Reusability** | Shared component library (`DataTable`, `FormField`, `StatusBadge`, `Modal`) used across all features |
| **Performance** | React Query handles caching, deduplication, and background refetch — no redundant network calls |
| **Simplicity** | No SSR, no edge functions, no WebSockets — a plain static build that Django can serve |
| **Role-Awareness** | Every route, action button, and menu item checks the user's role before rendering |

---

## 2. Architecture Decision: SPA (React) — Not Next.js

### Decision: **React SPA with Vite**

| Factor | React SPA (Vite) | Next.js |
|---|---|---|
| **PythonAnywhere compatibility** | ✅ Build → static files → Django serves them | ❌ Requires Node.js server process (unavailable on free tier) |
| **Build output** | Single `/dist` folder of HTML/JS/CSS | Requires `next start` or complex export |
| **Complexity** | Minimal — no server runtime | SSR/ISR adds deployment complexity |
| **SEO requirement** | None — this is an internal tool | SSR benefits irrelevant |
| **API integration** | Direct REST calls to same-origin Django | Same, but adds unnecessary abstraction |

### Conclusion
React SPA built with **Vite** produces a static `dist/` folder. Django serves it via `STATICFILES_DIRS` or a catch-all template view. No Node.js process needed on the server.

### Deployment Model
```
┌─────────────┐     ┌──────────────────────────────────────┐
│  Browser     │────▶│  PythonAnywhere (Django)              │
│              │     │                                      │
│  React SPA   │     │  /api/*         → DRF ViewSets       │
│  (static JS) │     │  /admin/        → Django Admin        │
│              │     │  /static/app/*  → React build files   │
│              │     │  /*             → index.html (SPA)    │
└─────────────┘     └──────────────────────────────────────┘
```

---

## 3. Project Structure

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── main.jsx                  # App entry point
│   ├── App.jsx                   # Root component, router setup
│   │
│   ├── api/                      # Centralized API layer
│   │   ├── client.js             # Axios instance, interceptors, base URL
│   │   ├── auth.js               # Login, logout, token refresh
│   │   ├── inventory.js          # Locations, ingredients, stock, movements
│   │   ├── products.js           # Products, categories
│   │   ├── recipes.js            # Recipes, recipe ingredients
│   │   ├── orders.js             # Customer orders
│   │   ├── suppliers.js          # Suppliers, supplier orders
│   │   └── production.js         # Production operations
│   │
│   ├── hooks/                    # Custom React hooks
│   │   ├── useAuth.js            # Auth context consumer
│   │   ├── useIngredients.js     # React Query wrapper for ingredients
│   │   ├── useStock.js           # React Query wrapper for stock
│   │   ├── useAlerts.js          # Low stock / expiration alert hook
│   │   ├── useDebounce.js        # Debounced input hook
│   │   └── usePagination.js      # Pagination state hook
│   │
│   ├── components/               # Shared, reusable UI components
│   │   ├── layout/
│   │   │   ├── AppShell.jsx      # Sidebar + header + main content
│   │   │   ├── Sidebar.jsx       # Role-aware navigation
│   │   │   ├── Header.jsx        # User menu, location selector, alerts
│   │   │   └── Breadcrumbs.jsx
│   │   ├── ui/
│   │   │   ├── DataTable.jsx     # Generic sortable/filterable table
│   │   │   ├── Modal.jsx         # Reusable modal wrapper
│   │   │   ├── StatusBadge.jsx   # Color-coded status indicator
│   │   │   ├── AlertBanner.jsx   # Warning/info/error banner
│   │   │   ├── LoadingSpinner.jsx
│   │   │   ├── EmptyState.jsx
│   │   │   ├── ConfirmDialog.jsx
│   │   │   └── Toast.jsx         # Notification toast
│   │   └── forms/
│   │       ├── FormField.jsx     # Label + input + error message
│   │       ├── SelectField.jsx   # Dropdown with search
│   │       ├── DatePicker.jsx
│   │       └── NumberInput.jsx   # Decimal-safe numeric input
│   │
│   ├── features/                 # Feature modules (smart components)
│   │   ├── auth/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── AuthProvider.jsx  # Context provider for auth state
│   │   │   └── ProtectedRoute.jsx
│   │   ├── dashboard/
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── KpiCards.jsx
│   │   │   ├── LowStockAlert.jsx
│   │   │   ├── ExpirationAlert.jsx
│   │   │   └── RecentActivity.jsx
│   │   ├── inventory/
│   │   │   ├── InventoryPage.jsx
│   │   │   ├── IngredientList.jsx
│   │   │   ├── IngredientDetail.jsx
│   │   │   ├── StockTable.jsx
│   │   │   ├── StockAdjustForm.jsx
│   │   │   ├── WasteReportForm.jsx
│   │   │   ├── LocationSelector.jsx
│   │   │   └── MovementHistory.jsx
│   │   ├── products/
│   │   │   ├── ProductsPage.jsx
│   │   │   ├── ProductList.jsx
│   │   │   ├── ProductForm.jsx
│   │   │   └── CategoryManager.jsx
│   │   ├── recipes/
│   │   │   ├── RecipesPage.jsx
│   │   │   ├── RecipeList.jsx
│   │   │   ├── RecipeBuilder.jsx      # Multi-ingredient form
│   │   │   ├── IngredientRow.jsx      # Single ingredient line in builder
│   │   │   └── RecipeCostPreview.jsx
│   │   ├── orders/
│   │   │   ├── OrdersPage.jsx
│   │   │   ├── OrderList.jsx
│   │   │   ├── OrderDetail.jsx
│   │   │   └── OrderStatusFlow.jsx
│   │   ├── suppliers/
│   │   │   ├── SuppliersPage.jsx
│   │   │   ├── SupplierList.jsx
│   │   │   ├── SupplierForm.jsx
│   │   │   ├── SupplierOrderForm.jsx
│   │   │   └── ReceiveDeliveryForm.jsx
│   │   ├── production/
│   │   │   ├── ProductionPage.jsx
│   │   │   ├── ProductionForm.jsx     # Recipe + qty + location → produce
│   │   │   └── ProductionLog.jsx
│   │   └── waste/
│   │       ├── WastePage.jsx
│   │       └── WasteLog.jsx
│   │
│   ├── store/                    # Minimal local state (NOT for server data)
│   │   └── uiStore.js            # Zustand: sidebar state, active location filter
│   │
│   ├── utils/
│   │   ├── constants.js          # Roles, movement types, units, status enums
│   │   ├── formatters.js         # Date, currency, quantity formatting
│   │   ├── validators.js         # Shared validation rules
│   │   └── roleGuards.js         # canAccess(role, action) helper
│   │
│   └── styles/
│       └── index.css             # Tailwind directives + custom utilities
│
├── index.html
├── tailwind.config.js
├── vite.config.js
├── package.json
└── .env.example                  # VITE_API_BASE_URL=/api
```

### Folder Responsibilities

| Folder | Responsibility |
|---|---|
| `api/` | All HTTP communication. One file per backend domain. Returns promises — no UI logic. |
| `hooks/` | React Query wrappers + utility hooks. Thin layer between `api/` and components. |
| `components/` | Stateless, reusable UI primitives. Zero business logic. Styled with Tailwind. |
| `features/` | Feature-specific smart components. Own their data fetching (via hooks), handle user actions. |
| `store/` | Client-only UI state (sidebar open, active filters). Server state lives in React Query cache. |
| `utils/` | Pure functions — formatting, validation, role checks. No side effects. |

---

## 4. Component Architecture

### 4.1 Component Hierarchy

```
App
├── AuthProvider
│   └── ProtectedRoute
│       └── AppShell
│           ├── Sidebar (role-aware links)
│           ├── Header (user info, location selector, alert bell)
│           └── <RouterOutlet>
│               ├── DashboardPage
│               │   ├── KpiCards
│               │   ├── LowStockAlert
│               │   ├── ExpirationAlert
│               │   └── RecentActivity
│               ├── InventoryPage
│               │   ├── LocationSelector
│               │   ├── IngredientList → DataTable
│               │   ├── StockTable → DataTable
│               │   ├── Modal → StockAdjustForm
│               │   ├── Modal → WasteReportForm
│               │   └── MovementHistory → DataTable
│               ├── RecipesPage
│               │   ├── RecipeList → DataTable
│               │   └── Modal → RecipeBuilder
│               │       ├── IngredientRow (repeatable)
│               │       └── RecipeCostPreview
│               ├── ProductionPage
│               │   ├── ProductionForm
│               │   └── ProductionLog → DataTable
│               ├── OrdersPage
│               │   ├── OrderList → DataTable
│               │   └── OrderDetail
│               ├── SuppliersPage
│               │   ├── SupplierList → DataTable
│               │   ├── Modal → SupplierOrderForm
│               │   └── Modal → ReceiveDeliveryForm
│               └── WastePage
│                   └── WasteLog → DataTable
```

### 4.2 Smart vs Presentational Components

| Type | Examples | Rules |
|---|---|---|
| **Smart (Feature)** | `InventoryPage`, `RecipeBuilder`, `ProductionForm` | Calls hooks, manages form state, dispatches mutations |
| **Presentational (UI)** | `DataTable`, `StatusBadge`, `FormField`, `Modal` | Receives props only, zero data fetching, fully reusable |

### 4.3 Reusability Strategy

The `DataTable` component is the backbone of most pages:

```
DataTable
  Props:
    - columns[]        → { key, label, render?, sortable? }
    - data[]           → Row objects
    - isLoading        → Show skeleton
    - onSort           → Sort callback
    - onRowClick?      → Navigate to detail
    - pagination       → { page, pageSize, total }
    - onPageChange     → Pagination callback
    - actions[]?       → Row-level action buttons (edit, delete)
    - bulkActions[]?   → Toolbar actions for selected rows
    - emptyMessage     → Custom empty state text
```

Used identically for ingredients, stock, orders, suppliers, movements, and production logs — only `columns` and `data` change.

---

## 5. State Management Strategy

### 5.1 Why React Query Over Redux

| Concern | React Query | Redux Toolkit |
|---|---|---|
| **Server state caching** | ✅ Built-in | Requires manual cache logic |
| **Background refetch** | ✅ Automatic (staleTime, refetchInterval) | Manual |
| **Optimistic updates** | ✅ Built-in `onMutate` | Manual |
| **Deduplication** | ✅ Same query key = 1 request | Manual |
| **Boilerplate** | Minimal — hook per resource | Slice + thunk + selector per resource |
| **DevTools** | ✅ React Query DevTools | Redux DevTools |

**Verdict**: The entire app is CRUD over REST. React Query handles 95% of the state. Redux adds unnecessary complexity.

### 5.2 State Boundaries

```
┌─────────────────────────────────────────────────────┐
│  React Query Cache (server state)                   │
│  ┌─────────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ ingredients  │ │ stock    │ │ movements        │  │
│  │ products     │ │ recipes  │ │ orders           │  │
│  │ suppliers    │ │ locations│ │ production       │  │
│  └─────────────┘ └──────────┘ └──────────────────┘  │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Zustand Store (client-only UI state)               │
│  ┌──────────────────────────────────────────┐       │
│  │ sidebarOpen, activeLocationId,           │       │
│  │ activeFilters, modalState, theme         │       │
│  └──────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  React Context (auth only)                          │
│  ┌──────────────────────────────────────────┐       │
│  │ currentUser, role, token, login, logout  │       │
│  └──────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
```

### 5.3 React Query Configuration

```
Query Defaults:
  staleTime:    5 minutes    (data considered fresh)
  cacheTime:    30 minutes   (kept in memory after unmount)
  retry:        2            (retry failed requests twice)
  refetchOnWindowFocus: true (re-validate when user returns)

Resource-Specific Overrides:
  stock:        staleTime: 1 minute   (changes frequently)
  locations:    staleTime: 30 minutes (rarely changes)
  movements:    staleTime: 0          (always fetch fresh audit data)
```

### 5.4 Example Hook Pattern

```jsx
// hooks/useIngredients.js — representative pattern

function useIngredients(filters) {
  return useQuery({
    queryKey: ['ingredients', filters],
    queryFn: () => api.inventory.getIngredients(filters),
    staleTime: 5 * 60 * 1000,
  });
}

function useCreateIngredient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => api.inventory.createIngredient(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ingredients'] });
      toast.success('Ingredient created');
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed'),
  });
}
```

---

## 6. API Integration Layer

### 6.1 Centralized HTTP Client

```
api/client.js responsibilities:
  - Create Axios instance with baseURL from VITE_API_BASE_URL
  - Attach auth token (cookie or header) via request interceptor
  - Handle 401 → redirect to login via response interceptor
  - Handle 403 → show "insufficient permissions" toast
  - Handle 500 → show "server error" toast
  - Handle network errors → show "offline" banner
  - Include CSRF token header for session auth (Django requirement)
```

### 6.2 Endpoint Mapping

Each file in `api/` maps directly to a DRF ViewSet:

```
api/inventory.js
  getLocations(params)           → GET    /api/locations/
  getLocation(id)                → GET    /api/locations/{id}/
  createLocation(data)           → POST   /api/locations/
  updateLocation(id, data)       → PUT    /api/locations/{id}/
  deleteLocation(id)             → DELETE /api/locations/{id}/

  getIngredients(params)         → GET    /api/ingredients/
  getIngredient(id)              → GET    /api/ingredients/{id}/
  createIngredient(data)         → POST   /api/ingredients/
  updateIngredient(id, data)     → PUT    /api/ingredients/{id}/
  getIngredientHistory(id)       → GET    /api/ingredients/{id}/stock_history/

  getStock(params)               → GET    /api/stock/
  createStock(data)              → POST   /api/stock/
  updateStock(id, data)          → PUT    /api/stock/{id}/
  adjustStock(data)              → POST   /api/stock/adjust/
  reportWaste(data)              → POST   /api/stock/report_waste/

  getMovements(params)           → GET    /api/movements/

api/production.js
  produce(data)                  → POST   /api/production/produce/

api/products.js          (when backend endpoints are added)
  getProducts(params)            → GET    /api/products/
  ...

api/recipes.js           (when backend endpoints are added)
  getRecipes(params)             → GET    /api/recipes/
  ...

api/orders.js            (when backend endpoints are added)
  getOrders(params)              → GET    /api/orders/
  ...

api/suppliers.js         (when backend endpoints are added)
  getSuppliers(params)           → GET    /api/suppliers/
  ...

api/auth.js
  login(username, password)      → POST   /api-auth/login/
  logout()                       → POST   /api-auth/logout/
  getCurrentUser()               → GET    /api/users/me/
```

### 6.3 Query Parameter Convention

All list endpoints accept standardized params:

```
{
  page:      number,       // Pagination (DRF PageNumberPagination)
  search:    string,       // SearchFilter
  ordering:  string,       // OrderingFilter (prefix with - for desc)
  ...filters               // DjangoFilterBackend fields
}
```

Specific filters per endpoint:

| Endpoint | Extra Params |
|---|---|
| `GET /api/ingredients/` | `low_stock=true`, `unit=kg`, `is_active=true` |
| `GET /api/stock/` | `low_stock=true`, `expiring_soon=true`, `expired=true`, `ingredient=id`, `location=id` |
| `GET /api/movements/` | `movement_type=WASTE`, `start_date=`, `end_date=`, `stock__ingredient=id`, `stock__location=id` |
| `GET /api/locations/` | `is_active=true` |

### 6.4 Error Handling Strategy

```
HTTP Status    →  Frontend Behavior
───────────────────────────────────────────────
400            →  Show field-level validation errors on form
401            →  Redirect to /login, clear auth state
403            →  Toast: "You don't have permission for this action"
404            →  Toast: "Resource not found" + redirect to list
422            →  Show validation errors on form
429            →  Toast: "Too many requests, please wait"
500            →  Toast: "Server error — please try again"
Network Error  →  Banner: "Connection lost — check your internet"
```

---

## 7. Authentication & Authorization

### 7.1 Auth Flow

```
1. User visits app → ProtectedRoute checks auth state
2. No token/session → redirect to /login
3. User submits credentials → POST /api-auth/login/
4. Django returns session cookie (+ optional CSRF token)
5. All subsequent requests include cookie automatically
6. GET /api/users/me/ → returns { username, role, location }
7. AuthProvider stores user in React Context
8. Logout → POST /api-auth/logout/ → clear context → redirect
```

**Session-based auth** is preferred because:
- Django session middleware is already configured
- No JWT token management needed
- CSRF protection built-in
- Same-origin deployment (React served by Django)

### 7.2 Role-Based UI Rendering

Three roles from the backend: **ADMIN**, **MANAGER**, **STAFF**

```
Feature/Action              │ ADMIN │ MANAGER │ STAFF
────────────────────────────┼───────┼─────────┼──────
View Dashboard              │  ✅   │   ✅    │  ✅
View Inventory              │  ✅   │   ✅    │  ✅ (own location)
Add/Edit Ingredients        │  ✅   │   ✅    │  ❌
Adjust Stock                │  ✅   │   ✅    │  ❌
Report Waste                │  ✅   │   ✅    │  ✅
Manage Products             │  ✅   │   ✅    │  ❌
Manage Recipes              │  ✅   │   ✅    │  ❌
Run Production              │  ✅   │   ✅    │  ✅
View Orders                 │  ✅   │   ✅    │  ✅ (own location)
Create/Edit Orders          │  ✅   │   ✅    │  ❌
Manage Suppliers            │  ✅   │   ✅    │  ❌
View Movement History       │  ✅   │   ✅    │  ✅ (own location)
Manage Users                │  ✅   │   ❌    │  ❌
Manage Locations            │  ✅   │   ❌    │  ❌
```

### 7.3 Implementation Pattern

```jsx
// utils/roleGuards.js
const PERMISSIONS = {
  'inventory.write':    ['ADMIN', 'MANAGER'],
  'inventory.read':     ['ADMIN', 'MANAGER', 'STAFF'],
  'stock.adjust':       ['ADMIN', 'MANAGER'],
  'waste.report':       ['ADMIN', 'MANAGER', 'STAFF'],
  'production.create':  ['ADMIN', 'MANAGER', 'STAFF'],
  'users.manage':       ['ADMIN'],
  'locations.manage':   ['ADMIN'],
  // ...
};

function canAccess(userRole, permission) {
  return PERMISSIONS[permission]?.includes(userRole) ?? false;
}
```

```jsx
// Usage in component
{canAccess(user.role, 'stock.adjust') && (
  <Button onClick={openAdjustModal}>Adjust Stock</Button>
)}
```

### 7.4 Route Protection

```jsx
// Three levels of route protection:

<Route element={<ProtectedRoute />}>              {/* Must be logged in */}
  <Route element={<AppShell />}>
    <Route path="/" element={<Dashboard />} />
    <Route path="/inventory" element={<InventoryPage />} />
    <Route path="/production" element={<ProductionPage />} />
    <Route path="/waste" element={<WastePage />} />

    <Route element={<ManagerRoute />}>             {/* Must be MANAGER+ */}
      <Route path="/products" element={<ProductsPage />} />
      <Route path="/recipes" element={<RecipesPage />} />
      <Route path="/orders" element={<OrdersPage />} />
      <Route path="/suppliers" element={<SuppliersPage />} />
    </Route>

    <Route element={<AdminRoute />}>               {/* Must be ADMIN */}
      <Route path="/users" element={<UsersPage />} />
      <Route path="/locations" element={<LocationsPage />} />
    </Route>
  </Route>
</Route>

<Route path="/login" element={<LoginPage />} />
```

---

## 8. UI/UX Design Considerations

### 8.1 Design System

| Element | Specification |
|---|---|
| **Color palette** | Amber/warm-brown primary (bakery theme), red for alerts, green for success, gray for neutral |
| **Typography** | Inter or system fonts — clean, high readability |
| **Spacing** | Tailwind default scale (4px base unit) |
| **Border radius** | `rounded-lg` (8px) for cards, `rounded-md` (6px) for inputs |
| **Shadows** | `shadow-sm` for cards, `shadow-lg` for modals |
| **Icons** | Lucide React — consistent, lightweight |

### 8.2 Bakery-Workflow Optimizations

- **Fast data entry**: Tab-navigable forms. Auto-focus first field on modal open. Keyboard shortcut `Ctrl+N` for "New" actions.
- **One-click waste reporting**: Right-click or swipe on a stock row → "Report Waste" context action.
- **Inline editing**: Double-click a quantity cell in the stock table → inline number input → Enter to save.
- **Quick produce**: Dropdown recipe selector + quantity input on the production page — no multi-step wizard.
- **Location memory**: Selected location persists in Zustand. Staff users auto-locked to their assigned location.

### 8.3 Alert System

```
┌─────────────────────────────────────────┐
│  🔴 3 items expired                     │  ← Red banner at top of dashboard
│  🟡 7 items expiring within 7 days      │  ← Amber banner
│  🟠 5 ingredients below reorder level   │  ← Orange banner
└─────────────────────────────────────────┘
```

Alerts fetch from:
- `GET /api/stock/?expired=true` → count
- `GET /api/stock/?expiring_soon=true` → count
- `GET /api/ingredients/?low_stock=true` → count

Polled every 5 minutes via React Query `refetchInterval`.

### 8.4 Table Standards

Every data table supports:
- **Column sorting** (click header to toggle asc/desc)
- **Search bar** (debounced 300ms, hits `?search=` param)
- **Filter dropdowns** (location, status, type)
- **Pagination** (20 per page, matching DRF `PAGE_SIZE`)
- **Row actions** (view, edit, delete — role-gated)
- **Bulk select** for manager+ actions (bulk waste, bulk deactivate)
- **Export CSV** button for managers+
- **Empty state** with helpful message + action button

---

## 9. Key Screens (Detailed)

### 9.1 Dashboard

```
┌──────────────────────────────────────────────────────────┐
│  Header: Bakery IMS    [Location ▼]  🔔 12   👤 Admin   │
├────────┬─────────────────────────────────────────────────┤
│        │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐ │
│ Side-  │  │Total    │ │Low Stock│ │Expiring │ │Today's│ │
│ bar    │  │Ingrednts│ │  Items  │ │ Soon    │ │Output │ │
│        │  │   42    │ │  🔴 5   │ │  🟡 7   │ │  156  │ │
│ • Dash │  └─────────┘ └─────────┘ └─────────┘ └───────┘ │
│ • Inv  │                                                 │
│ • Prod │  ┌─ Low Stock Alerts ───────────────────────┐   │
│ • Recip│  │ ⚠ Flour: 2.5 kg (reorder: 10 kg)        │   │
│ • Order│  │ ⚠ Sugar: 1.0 kg (reorder: 5 kg)         │   │
│ • Suppl│  │ ⚠ Eggs: 12 pcs (reorder: 48 pcs)        │   │
│ • Waste│  └──────────────────────────────────────────┘   │
│ • Users│                                                 │
│        │  ┌─ Expiring Soon ──────────────────────────┐   │
│        │  │ 🕐 Butter (Batch B-0412) — expires Mar 25│   │
│        │  │ 🕐 Cream (Batch C-0389) — expires Mar 26 │   │
│        │  └──────────────────────────────────────────┘   │
│        │                                                 │
│        │  ┌─ Recent Activity ────────────────────────┐   │
│        │  │ 14:30  Stock In: 50kg Flour (john)       │   │
│        │  │ 13:15  Production: 24 Croissants (sarah) │   │
│        │  │ 12:00  Waste: 2kg Butter expired (john)  │   │
│        │  └──────────────────────────────────────────┘   │
└────────┴─────────────────────────────────────────────────┘
```

**Data sources**:
- KPIs: aggregated from `/api/ingredients/`, `/api/stock/`
- Low stock: `GET /api/ingredients/?low_stock=true`
- Expiring: `GET /api/stock/?expiring_soon=true`
- Activity: `GET /api/movements/?ordering=-created_at&page_size=10`

### 9.2 Inventory Page

```
┌─ Inventory ──────────────────────────────────────────────┐
│                                                          │
│  [Location: All ▼]  [Search ingredients...]  [+ Add New] │
│                                                          │
│  ┌─ Tabs: [Ingredients] [Stock] [Movements] ───────────┐ │
│  │                                                      │ │
│  │  Name        │ Unit │ Total Stock │ Reorder │ Status │ │
│  │──────────────┼──────┼─────────────┼─────────┼────────│ │
│  │  Flour       │ kg   │ 45.00       │ 10.00   │ ✅ OK  │ │
│  │  Sugar       │ kg   │ 3.00        │ 5.00    │ 🔴 Low │ │
│  │  Butter      │ kg   │ 8.50        │ 5.00    │ ✅ OK  │ │
│  │  Eggs        │ pcs  │ 24          │ 48      │ 🔴 Low │ │
│  │                                                      │ │
│  │  ◄ Page 1 of 3 ►                                    │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                          │
│  Click row → expand to show stock by location:           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Location     │ Qty  │ Batch   │ Expires   │ Action │ │
│  │  Main Bakery  │ 30kg │ B-0501  │ Apr 15    │ [Adj]  │ │
│  │  Branch #2    │ 15kg │ B-0489  │ Mar 28 ⚠ │ [Adj]  │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 9.3 Production Page

```
┌─ Production ─────────────────────────────────────────────┐
│                                                          │
│  ┌─ New Production Run ────────────────────────────────┐ │
│  │  Recipe:   [Croissants ▼]                           │ │
│  │  Quantity: [24        ]                             │ │
│  │  Location: [Main Bakery ▼]                          │ │
│  │                                                     │ │
│  │  Required Ingredients:        Available:  Status:   │ │
│  │  • Flour: 2.4 kg              45.0 kg     ✅       │ │
│  │  • Butter: 1.2 kg             8.5 kg      ✅       │ │
│  │  • Eggs: 12 pcs               24 pcs      ✅       │ │
│  │                                                     │ │
│  │  [🏭 Start Production]                              │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─ Production Log ────────────────────────────────────┐ │
│  │  Date     │ Recipe      │ Qty │ By    │ Status      │ │
│  │  Mar 22   │ Croissants  │ 24  │ sarah │ ✅ Complete │ │
│  │  Mar 22   │ Baguettes   │ 30  │ john  │ ✅ Complete │ │
│  │  Mar 21   │ Sourdough   │ 12  │ sarah │ ✅ Complete │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 9.4 Recipe Builder

```
┌─ Recipe: Croissants (v2) ────────────────────────────────┐
│                                                          │
│  Name:     [Croissants         ]                         │
│  Product:  [Croissant ▼]                                 │
│  Yield:    [24] units                                    │
│                                                          │
│  ┌─ Ingredients ───────────────────────────────────────┐ │
│  │  Ingredient      │ Quantity │ Unit │ Cost    │      │ │
│  │  [Flour ▼]       │ [2.4   ] │ kg   │ $4.80   │ [✕] │ │
│  │  [Butter ▼]      │ [1.2   ] │ kg   │ $9.60   │ [✕] │ │
│  │  [Eggs ▼]        │ [12    ] │ pcs  │ $3.60   │ [✕] │ │
│  │  [Sugar ▼]       │ [0.3   ] │ kg   │ $0.45   │ [✕] │ │
│  │                                                     │ │
│  │  [+ Add Ingredient]                                 │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  Total Cost: $18.45    Cost per unit: $0.77              │
│                                                          │
│  [Save Recipe]  [Save as New Version]                    │
└──────────────────────────────────────────────────────────┘
```

### 9.5 Orders Page

```
┌─ Orders ─────────────────────────────────────────────────┐
│  [Filter: All ▼] [Status: All ▼] [Date range: ▼] [+ New]│
│                                                          │
│  Order #   │ Customer   │ Date    │ Total  │ Status      │
│  ORD-0142  │ Cafe Luna  │ Mar 22  │ $240   │ 🟡 Pending  │
│  ORD-0141  │ Hotel Rex  │ Mar 22  │ $580   │ 🔵 Producing│
│  ORD-0140  │ Walk-in    │ Mar 21  │ $45    │ 🟢 Complete │
│  ORD-0139  │ Cafe Luna  │ Mar 21  │ $180   │ 🟢 Complete │
│                                                          │
│  Click row → Order Detail with status progression:       │
│  [Pending] → [Confirmed] → [Producing] → [Ready] → [Done│]
└──────────────────────────────────────────────────────────┘
```

### 9.6 Supplier & Waste Pages

Follow the same table-based pattern. Suppliers page adds a "Receive Delivery" modal that maps to `InventoryService.receive_supplier_order()`. Waste page shows filtered movements where `movement_type=WASTE`.

---

## 10. Forms & Data Handling

### 10.1 Library: React Hook Form + Zod

| Library | Role |
|---|---|
| **React Hook Form** | Form state, submission, field registration. Uncontrolled by default → better performance. |
| **Zod** | Schema-based validation. Shares types with TypeScript (if adopted later). |

### 10.2 Form Patterns

**Simple form** (Ingredient):
```
Fields: name (required), unit (select), reorder_level (number), cost_per_unit (number)
Validation: Zod schema → required string, enum unit, min 0 numbers
Submit: POST /api/ingredients/ or PUT /api/ingredients/{id}/
```

**Complex form** (Recipe Builder):
```
Fixed fields: name, product (select), yield_quantity
Dynamic fields: ingredients[] — array of { ingredient_id, quantity }
  → useFieldArray from React Hook Form
  → Add/remove rows dynamically
  → Each row: ingredient dropdown (searchable) + quantity input
  → Cost preview computed client-side from ingredient.cost_per_unit
Validation: At least 1 ingredient, all quantities > 0
```

**Action form** (Stock Adjustment):
```
Fields: stock_id (hidden/preselected), new_quantity (number), reason (text)
Validation: new_quantity >= 0, reason required
Submit: POST /api/stock/adjust/
On success: invalidate ['stock'] + ['ingredients'] queries, close modal, show toast
```

### 10.3 Validation Rules

```
Ingredient:
  name:           required, 1-200 chars, unique (server-side)
  unit:           required, one of [kg, g, L, mL, units, pcs, boxes]
  reorder_level:  required, number >= 0
  cost_per_unit:  optional, number >= 0

Stock Adjustment:
  stock_id:       required, valid stock ID
  new_quantity:   required, number >= 0
  reason:         required, 1-500 chars

Waste Report:
  stock_id:       required, valid stock ID
  quantity:       required, number > 0, <= current stock quantity
  reason:         required, 1-500 chars

Production:
  recipe_id:      required, active recipe
  quantity:       required, number > 0
  location_id:    required, active location
```

---

## 11. Performance Optimization

| Technique | Implementation |
|---|---|
| **Code splitting** | `React.lazy()` per feature page. Only dashboard loads initially. |
| **React Query caching** | `staleTime: 5min` avoids refetches during navigation. `cacheTime: 30min` keeps data after unmount. |
| **Debounced search** | 300ms debounce on search inputs before hitting API. |
| **Pagination** | Server-side via DRF. 20 items per page. Never load entire dataset. |
| **Virtualized tables** | Use `@tanstack/react-virtual` only for movement history (potentially thousands of rows). Not needed for most tables. |
| **Optimistic updates** | Waste reports and stock adjustments update UI immediately, rollback on error. |
| **Image optimization** | Product images served via Django media with size limits (Pillow resize on upload). |
| **Bundle size** | Vite tree-shaking. Only import used Lucide icons. Tailwind purges unused CSS. |

**Expected bundle size**: < 200KB gzipped (React + React Query + React Router + React Hook Form + Tailwind).

---

## 12. Deployment Strategy (PythonAnywhere-Friendly)

### 12.1 Build Process

```bash
# Local machine (or GitHub Actions)
cd frontend
npm run build          # Vite → dist/

# Output:
# dist/
#   index.html
#   assets/
#     index-[hash].js
#     index-[hash].css
```

### 12.2 Serving via Django

**Option A — Recommended**: Copy `dist/` contents into Django's static files.

```python
# bakery/settings/base.py
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'frontend' / 'dist',   # React build output
]
```

Add a catch-all view for SPA routing:

```python
# bakery/views.py
from django.views.generic import TemplateView

class SPAView(TemplateView):
    template_name = 'index.html'  # The React app's index.html

# bakery/urls.py — add AFTER api/ and admin/ patterns
urlpatterns += [
    re_path(r'^(?!api/|admin/|static/|media/).*$', SPAView.as_view()),
]
```

**Option B — Simpler**: Serve React on a separate subdomain or static host (GitHub Pages, Netlify free tier) and configure CORS in Django.

### 12.3 Deployment Steps

```
1. npm run build                           (local)
2. Copy dist/ contents to Django project   (local or git)
3. python manage.py collectstatic          (PythonAnywhere)
4. Reload web app                          (PythonAnywhere)
```

### 12.4 Environment Variables

```
# frontend/.env.production
VITE_API_BASE_URL=/api          # Same-origin, no CORS issues
```

```
# frontend/.env.development
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

### 12.5 What to Avoid

- ❌ No Node.js server process (PythonAnywhere free tier can't run it)
- ❌ No SSR/ISR (requires Node runtime)
- ❌ No edge functions or serverless
- ❌ No complex CI/CD — manual build + deploy is fine for this scale

---

## 13. Error Handling & Notifications

### 13.1 Global Error Boundary

```
ErrorBoundary (React)
  → Catches render errors
  → Shows "Something went wrong" fallback UI
  → Offers "Reload" button
  → Logs error to console (no external service on free tier)
```

### 13.2 Toast Notification System

Use `react-hot-toast` (2KB, zero config):

| Event | Toast Type | Message Example |
|---|---|---|
| Create/update success | ✅ Success | "Ingredient 'Flour' updated" |
| Delete success | ✅ Success | "Stock entry deleted" |
| Production complete | ✅ Success | "Produced 24 Croissants" |
| Validation error | ❌ Error | "Quantity must be greater than 0" |
| Server error (500) | ❌ Error | "Server error — please try again" |
| Permission denied (403) | ⚠ Warning | "You don't have permission for this action" |
| Low stock detected | ⚠ Warning | "5 ingredients below reorder level" |
| Items expiring soon | ⚠ Warning | "7 items expiring within 7 days" |
| Network offline | 🔴 Persistent | "Connection lost — check your internet" |

### 13.3 Form Error Display

- Field-level: red border + inline error message below input
- Form-level: red AlertBanner above submit button for server validation errors
- Non-field errors from DRF (`detail` or `non_field_errors`) displayed in AlertBanner

---

## 14. Scalability Considerations

### 14.1 What Scales Without Changes

| Concern | How It's Handled |
|---|---|
| **More endpoints** | Add new file in `api/`, new hook in `hooks/`, new feature folder |
| **More roles** | Add to `PERMISSIONS` map in `roleGuards.js` |
| **More locations** | Already supported — location selector is global |
| **Larger datasets** | Server-side pagination already in place |
| **New features** | Feature-folder pattern keeps each domain isolated |

### 14.2 Migration Path to Larger Infrastructure

```
Current (PythonAnywhere free)     →  Future (AWS/Cloud)
──────────────────────────────────────────────────────
Django serves React static        →  CloudFront CDN for static
SQLite/MySQL                      →  RDS PostgreSQL
Management commands (cron)        →  Celery + Redis for async tasks
Session auth                      →  JWT + token refresh
No WebSocket                      →  Django Channels for real-time alerts
react-hot-toast                   →  Push notifications
```

### 14.3 API Abstraction Layer

The `api/` folder acts as an anti-corruption layer. If the backend changes (endpoint rename, response shape), only the corresponding `api/*.js` file needs updating. Components and hooks remain unchanged.

---

## 15. Key User Workflows

### Workflow 1: Creating a Product with Recipe

```
1. Manager navigates to Products → clicks [+ New Product]
2. Fills: name, category, selling price, image
3. Submits → POST /api/products/
4. Navigates to Recipes → clicks [+ New Recipe]
5. Selects the newly created product
6. Adds ingredient rows: Flour (2.4 kg), Butter (1.2 kg), Eggs (12 pcs)
7. RecipeCostPreview shows: Total $18.45, Per unit $0.77
8. Submits → POST /api/recipes/
9. Toast: "Recipe 'Croissants v1' created"
```

### Workflow 2: Production Run → Inventory Deduction

```
1. Staff navigates to Production
2. Selects recipe: "Croissants", quantity: 24, location: "Main Bakery"
3. UI shows ingredient availability check (green/red per ingredient)
4. Clicks [Start Production]
5. POST /api/production/produce/ → { recipe_id, quantity, location_id }
6. Backend atomically deducts ingredients via FIFO
7. Response shows deductions: Flour -2.4kg, Butter -1.2kg, Eggs -12
8. Toast: "Produced 24 Croissants"
9. Inventory page reflects updated quantities
10. Movement history shows OUT entries for each ingredient
```

### Workflow 3: Receiving a Supplier Delivery

```
1. Manager navigates to Suppliers → selects supplier order (status: ORDERED)
2. Clicks [Receive Delivery]
3. Modal shows ordered items with expected quantities
4. Manager enters received quantities (may differ from ordered)
5. Enters batch numbers and expiration dates per item
6. Submits → backend creates Stock entries + StockMovement (IN) per item
7. Order status updates to RECEIVED
8. Toast: "Delivery received — 5 items added to inventory"
9. Dashboard KPIs update on next refetch (staleTime expires)
```

### Workflow 4: Handling Expired Items

```
1. Staff sees "3 items expired" alert on dashboard (or header bell icon)
2. Clicks alert → navigates to Inventory → Stock tab filtered: expired=true
3. Table shows expired stock rows with red StatusBadge
4. Clicks [Report Waste] on each row (or bulk select)
5. Modal: quantity (pre-filled), reason: "Expired"
6. POST /api/stock/report_waste/
7. Stock quantity decremented, StockMovement (WASTE) created
8. Repeat for each expired item
9. Expired count on dashboard decreases
```

### Workflow 5: Monitoring Low Stock Alerts

```
1. Dashboard loads → React Query fetches /api/ingredients/?low_stock=true
2. KPI card shows "🔴 5 Low Stock Items"
3. LowStockAlert component lists each ingredient with:
   - Current total stock
   - Reorder level
   - Deficit (reorder_level - current)
4. Manager clicks an ingredient → navigates to Inventory detail
5. Reviews stock by location
6. Decides to create a supplier order → navigates to Suppliers
7. Creates new supplier order with needed quantities
8. After delivery is received, low stock alert clears automatically
```

---

## 16. Design Decisions & Trade-offs

### Decisions Made

| Decision | Rationale |
|---|---|
| **React SPA over Next.js** | PythonAnywhere can't run Node.js. Static build is the only option. Next.js `export` mode loses its core advantages. |
| **Vite over CRA** | Vite is faster (esbuild), smaller output, better DX. CRA is deprecated/unmaintained. |
| **React Query over Redux** | App is 100% CRUD. React Query eliminates all the boilerplate of slices, thunks, and selectors for server state. |
| **Zustand over Context for UI state** | Zustand avoids re-renders from Context changes. Minimal API for simple UI state. |
| **Session auth over JWT** | Same-origin deployment means cookies work natively. No token refresh logic needed. Django session middleware handles expiry. |
| **Tailwind over CSS Modules** | Faster development, consistent design tokens, tiny production CSS (purged). Better for a system with many similar pages (tables, forms). |
| **React Hook Form over Formik** | Uncontrolled inputs = better performance. Native integration with Zod. Smaller bundle. |
| **react-hot-toast** | 2KB, zero dependencies, works without a provider. Perfect for simple toast notifications. |
| **Feature folders over type folders** | Keeps related files together. Adding a new feature = add one folder. Deleting a feature = delete one folder. |

### Trade-offs Accepted

| Trade-off | Downside | Why It's Acceptable |
|---|---|---|
| **No SSR** | No SEO, slower first contentful paint | Internal tool — no SEO needed. Bundle < 200KB loads fast. |
| **No real-time updates** | Users must refresh or wait for refetch | React Query's `refetchInterval` (5min) + `refetchOnWindowFocus` is close enough. Real-time adds WebSocket complexity. |
| **No offline support** | App requires internet | Bakery staff are always in-shop with WiFi. Offline adds IndexedDB complexity. |
| **Session auth** | Can't use API from external clients | If external clients needed later, add JWT as a second auth class in DRF. |
| **Manual build+deploy** | No auto-deploy on git push | For a single-site bakery system, `npm run build` + `collectstatic` is fast enough. Can add GitHub Actions later. |
| **No TypeScript initially** | Less type safety | Reduces onboarding friction. Zod schemas provide runtime validation. Can migrate incrementally (rename `.jsx` → `.tsx`). |

### PythonAnywhere-Specific Constraints

| Constraint | Impact | Mitigation |
|---|---|---|
| No Node.js process | Can't run Next.js, Remix, or any SSR | React SPA with static build |
| Single web app | Frontend and backend on same domain | Same-origin requests, no CORS complexity |
| Limited CPU/RAM | Can't run heavy build on server | Build locally, upload `dist/` |
| No WebSocket | No real-time features | Polling via React Query `refetchInterval` |
| Free tier disk limits | Limited static file storage | Optimized build < 1MB total |

---

## Dependencies Summary

```json
{
  "dependencies": {
    "react": "^19.x",
    "react-dom": "^19.x",
    "react-router-dom": "^7.x",
    "@tanstack/react-query": "^5.x",
    "react-hook-form": "^7.x",
    "@hookform/resolvers": "^3.x",
    "zod": "^3.x",
    "zustand": "^5.x",
    "axios": "^1.x",
    "lucide-react": "^0.4x",
    "react-hot-toast": "^2.x",
    "clsx": "^2.x",
    "date-fns": "^4.x"
  },
  "devDependencies": {
    "vite": "^6.x",
    "@vitejs/plugin-react": "^4.x",
    "tailwindcss": "^4.x",
    "autoprefixer": "^10.x",
    "postcss": "^8.x",
    "@tanstack/react-query-devtools": "^5.x"
  }
}
```

**Total production bundle estimate**: ~180KB gzipped

---

*This blueprint is designed to be implemented incrementally: start with auth + dashboard + inventory, then add features one at a time. Each feature is self-contained in its folder and can be built and tested independently.*
