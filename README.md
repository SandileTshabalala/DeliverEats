# L'vovo Chicken Dust

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
