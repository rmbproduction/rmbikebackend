# Port Configuration Guide

## Service Ports

| Service | Port | Environment | Description |
|---------|------|------------|-------------|
| API Gateway | 8080 | Production | Main API Gateway on Railway.app |
| Django Server | 8000 | Development | Local Django development server |
| Frontend (Vite) | 5173 | Development | Local Vite development server |
| Frontend (React) | 3000 | Development | Alternative React development server |
| PostgreSQL | 5432 | Both | Database server |
| Redis | 6379 | Both | Cache and message broker |
| Celery | 6379 | Both | Uses Redis port for broker |
| Celery Flower | 5555 | Development | Celery monitoring tool |

## Environment-Specific Configurations

### Development Environment
- Django runs on port 8000
- Frontend development servers on ports 5173 (Vite) or 3000 (React)
- PostgreSQL on port 5432
- Redis on port 6379
- Celery uses Redis port 6379
- Celery Flower dashboard on port 5555

### Production Environment (Railway.app)
- API Gateway runs on port 8080
- Application accessible at https://repairmybike.up.railway.app
- Database and Redis use Railway.app provided URLs
- Celery uses Railway.app Redis URL

## Port Conflict Prevention
1. Each service has a dedicated port in the `SERVICE_PORTS` configuration
2. Environment variables can override default ports
3. Railway.app automatically manages production ports
4. Celery shares Redis port but uses different database numbers

## Environment Variables
```env
PORT=8080                    # API Gateway port
DATABASE_PORT=5432           # PostgreSQL port
REDIS_PORT=6379             # Redis port
DJANGO_PORT=8000            # Django development server port
CELERY_FLOWER_PORT=5555     # Celery Flower monitoring
```

## Celery Configuration
```python
# Celery Broker URLs
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Development
CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'  # Different database number

# Production URLs (Railway.app)
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
```

## Common Issues and Solutions
1. Port Already in Use:
   - Check running processes: `lsof -i :<port>`
   - Kill process if needed: `kill -9 <PID>`

2. Port Conflicts:
   - Each service should use its designated port
   - Use environment variables to override default ports if needed
   - Check the `SERVICE_PORTS` dictionary in Django settings

3. Railway.app Deployment:
   - Railway.app automatically manages port 8080
   - No manual port configuration needed in production
   - Environment variables are managed through Railway.app dashboard

4. Celery-Specific Issues:
   - Ensure Redis is running on the correct port
   - Use different database numbers for broker and backend
   - Start Celery worker: `celery -A authback worker -l info`
   - Start Flower monitoring: `celery -A authback flower --port=5555` 