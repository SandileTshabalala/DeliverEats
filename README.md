# Deliver Eats

A food delivery marketplace for local restaurants, shisanyamas and kota spots:
customers order, restaurants keep their order money and pay a monthly plan,
and each restaurant's own drivers deliver.

A full-stack food ordering platform with real-time order tracking, multi-role support (customers, restaurants, drivers, admins), and payment processing.

## Tech Stack

### Frontend
- **React 19** with TypeScript
- **Vite** for build tooling
- **TailwindCSS** for styling
- **React Router** for navigation
- **TanStack Query** for data fetching
- **Zustand** for state management
- **Stripe** for payment processing
- **Framer Motion** for animations
- **Lucide React** for icons

### Backend
- **FastAPI** for REST API
- **PostgreSQL** (Neon) for database
- **Redis** for caching and message broker
- **Celery** for background tasks
- **SQLAlchemy** for ORM
- **Alembic** for database migrations
- **WebSockets** for real-time updates
- **Stripe** for payment processing
- **JWT** for authentication

### Infrastructure
- **Docker Compose** for development
- **Nginx** as reverse proxy
- **pnpm** for package management

## Features

### Multi-Role System
- **Customers**: Browse restaurants, place orders, track deliveries
- **Restaurants**: Manage menus, receive orders, update status
- **Drivers**: Accept deliveries, track orders, update delivery status
- **Admins**: Platform management, payment oversight

### Core Functionality
- User authentication and authorization (JWT)
- Restaurant and menu management
- Order placement and real-time tracking
- Payment processing via Stripe
- Real-time notifications via WebSockets
- Address management
- Rate limiting and request logging
- Background job processing with Celery

## Project Structure

```
lvovo/
├── client/                 # React frontend
│   ├── src/
│   │   ├── pages/         # Page components (Landing, Admin, Customer, Driver, Restaurant)
│   │   ├── components/    # Reusable UI components
│   │   ├── services/      # API service layer
│   │   ├── hooks/         # Custom React hooks
│   │   ├── context/       # React context providers
│   │   └── router.tsx     # Route configuration
│   ├── package.json
│   └── vite.config.ts
├── server/                # FastAPI backend
│   ├── app/
│   │   ├── routers/       # API route handlers
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   ├── core/          # Core configuration (auth, redis, middleware)
│   │   ├── db/            # Database configuration
│   │   ├── realtime/      # WebSocket handlers
│   │   └── workers/       # Celery workers
│   ├── alembic/           # Database migrations
│   ├── requirements.txt
│   └── .env.dev
├── nginx.conf             # Nginx configuration
├── docker-compose.dev.yml # Development Docker setup
└── README.md
```

## Getting Started

### Prerequisites
- Docker and Docker Compose
- pnpm (for frontend)
- Python 3.11+ (for local development)

### Development Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd lvovo
```

2. **Configure environment variables**
```bash
# Server environment
cp server/.env.dev server/.env.local
# Edit server/.env.local with your configuration

# Client environment
cp client/.env.dev client/.env.local
# Edit client/.env.local with your configuration
```

3. **Start services with Docker Compose**
```bash
docker-compose -f docker-compose.dev.yml up --build
```

This will start:
- FastAPI server on port 8000
- React dev server on port 5173
- Redis on port 6379
- Celery worker
- Nginx on port 80

4. **Access the application**
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Local Development (without Docker)

**Backend:**
```bash
cd server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd client
pnpm install
pnpm dev
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout

### Restaurants
- `GET /api/v1/restaurant/` - List restaurants
- `POST /api/v1/restaurant/` - Create restaurant
- `GET /api/v1/restaurant/{id}` - Get restaurant details

### Menus
- `GET /api/v1/menus/` - List menu items
- `POST /api/v1/menus/` - Create menu item
- `GET /api/v1/menus/{restaurant_id}` - Get restaurant menu

### Orders
- `POST /api/v1/orders/` - Create order
- `GET /api/v1/orders/` - List orders
- `GET /api/v1/orders/{id}` - Get order details
- `PATCH /api/v1/orders/{id}` - Update order status

### Payments
- `POST /api/v1/payments/create-checkout-session` - Create Stripe checkout session
- `POST /api/v1/payments/webhook` - Stripe webhook handler

### WebSocket
- `WS /api/v1/ws/orders/{order_id}` - Real-time order updates

## Database Migrations

```bash
cd server
alembic revision --autogenerate -m "migration message"
alembic upgrade head
```

## Environment Variables

### Server (.env.dev)
```
ENV=development
DATABASE_URL=postgresql://...
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=60
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
CORS_ORIGINS=http://localhost:5173
```

### Client (.env.dev)
```
VITE_API_URL=http://localhost:8000
```

## Testing

```bash
# Backend tests
cd server
pytest

# Frontend tests
cd client
pnpm test
```

## Deployment

### Production Build
```bash
# Build frontend
cd client
pnpm build

# Build and start production containers
docker-compose -f docker-compose.prod.yml up --build
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Payments (PayFast)

Customers can pay online with PayFast (card, Instant EFT, SnapScan and more) or choose cash / card on delivery.

1. Copy `server/.env.example` to `server/.env.dev` and fill in `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY` and `PAYFAST_PASSPHRASE` (sandbox credentials come from https://sandbox.payfast.co.za). Keep `PAYFAST_SANDBOX=true` until you go live.
2. Set `FRONTEND_URL` to where the web app runs and `PUBLIC_API_URL` to an address PayFast can reach from the internet. In development start a tunnel (for example `ngrok http 8000`) and use its https URL.
3. Restart the server. A "PayFast" payment method is created and switched on automatically. It can also be configured in Admin > Payments (public key = merchant id, secret key = merchant key, config = `{"passphrase": "...", "sandbox": true}`).

How it works: the server creates the order and prices it from the menu, signs the PayFast form, and the browser posts it to PayFast. PayFast then calls `POST /api/v1/payments/payfast/notify`; the server checks the signature, the amount and confirms the notification with PayFast before marking the order as paid. Only paid orders (or pay-on-delivery orders) can be accepted by a restaurant.

Tests for the signing and validation logic: `cd server && python -m pytest tests/test_payfast.py`.

## Colours

The palette lives in `client/src/index.css` (`brand-*` = ember orange, `gray-*` = warm charcoal). Change the values there to re-theme the whole app.

## How the money works

- **Order money goes to the restaurant.** Each restaurant chooses its methods in Restaurant > Settings: cash on delivery, its own card machine on delivery, or its own PayFast account. The platform never holds order money.
- **Restaurants pay the platform a subscription.** The platform owner creates plans in Admin > Subscriptions (price, billing period, free trial, monthly order limit). Restaurants pay by PayFast recurring billing into the platform account (`PAYFAST_*` in the env file) or by EFT/cash that the admin records.
- Subscriptions only block anything once `SUBSCRIPTIONS_ENFORCED=true`.
- **Each restaurant sets its own delivery fee** in Restaurant > Settings: a base fee, an optional charge per km, optional free delivery from an order amount, and an optional maximum distance. Distance is measured from the shop's saved location to the customer's address (straight line x 1.3 to approximate roads). The cart shows the fee before the customer pays, and `POST /api/v1/orders/quote` returns it. `DELIVERY_FEE` in the env file is only the default for restaurants that have not set one.

## Notifications

SMS goes through Africa's Talking and email through Resend. Fill in `AT_*`, `RESEND_API_KEY` and `EMAIL_FROM` in the env file; with those empty, messages are only written to the log. After signing in as the platform admin, `POST /api/v1/notifications/test` sends a test SMS and email to yourself.

| Event | Who | SMS | Email |
|---|---|---|---|
| New paid / pay-on-delivery order | Restaurant owner | yes | yes |
| Order accepted | Customer | yes | |
| Delivery assigned | Driver | yes | |
| Order on its way | Customer | yes | |
| Order delivered | Customer | | receipt |
| Order cancelled | Customer (and driver) | yes | yes |
| Online payment received | Customer | | yes |
| Subscription paid | Restaurant owner | | yes |
| Plan ending / overdue / closed | Restaurant owner | yes | yes |
| Password reset | The user | | yes |

## Running in production

1. Copy `server/.env.example` to `server/.env.prod` and fill it in. Use new values for `JWT_SECRET_KEY` and the database password, set `ENCRYPTION_KEY`, and set `CORS_ORIGINS`, `FRONTEND_URL` and `PUBLIC_API_URL` to `https://your-domain`.
2. Point the domain's DNS at the server.
3. `DOMAIN=your-domain docker compose -f docker-compose.prod.yml up -d --build`

This starts the API (one process), the background worker with its scheduler, Redis, and Caddy, which serves the built web app, forwards `/api` to the API and manages the HTTPS certificate. Env files are no longer tracked by git; never commit them.

## Tests

`cd server && python -m pytest` runs the whole API against a temporary SQLite database and an in-memory Redis: no services or network needed.
