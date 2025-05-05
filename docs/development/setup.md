# Development Environment Setup

This guide will help you set up a local development environment for the Nibble platform. Follow these steps to get your environment ready for development.

## Prerequisites

Before you begin, make sure you have the following installed on your system:

- **Docker**: Version 20.10.0 or higher
  - [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose**: Version 2.0.0 or higher
  - [Install Docker Compose](https://docs.docker.com/compose/install/)
- **Git**: Version 2.30.0 or higher
  - [Install Git](https://git-scm.com/downloads)
- **Python**: Version 3.10 or higher (for local development outside containers)
  - [Install Python](https://www.python.org/downloads/)

## System Requirements

- **CPU**: 4 cores recommended (2 cores minimum)
- **RAM**: 8GB minimum, 16GB recommended
- **Disk Space**: At least 5GB free space
- **Operating System**: Linux, macOS, or Windows with WSL2

## Clone the Repository

```bash
git clone https://github.com/yourusername/nibble-platform.git
cd nibble-platform
```

## Environment Setup

### 1. Configure Environment Variables

Create a `.env` file in the root directory by copying the example:

```bash
cp .env.example .env
```

Edit the `.env` file to set appropriate values for your local environment. The most important variables to consider are:

- `POSTGRES_PASSWORD`: Password for the PostgreSQL database
- `JWT_SECRET`: Secret key for JWT token generation
- `YANDEX_MAP_API_KEY`: API key for Yandex Maps (optional for basic development)

### 2. Build and Start Services

Use Docker Compose to build and start all services:

```bash
docker-compose up -d
```

This command will:
- Build all service images
- Create and start containers
- Set up networks and volumes
- Initialize the database with sample data

The first build may take several minutes. Subsequent builds will be faster.

### 3. Verify Setup

Check that all services are running:

```bash
docker-compose ps
```

You should see all services in the "Up" state. If any service shows "Exit" or "Restarting", check the logs:

```bash
docker-compose logs <service-name>
```

### 4. Access Service Documentation

Once all services are running, you can access the API documentation for each service:

- API Gateway: http://localhost:8000/docs
- User Service: http://localhost:8001/docs
- Restaurant Service: http://localhost:8002/docs
- Driver Service: http://localhost:8003/docs
- Order Service: http://localhost:8004/docs
- Admin Service: http://localhost:8005/docs
- Analytics Service: http://localhost:8006/docs

## Local Development Workflow

### 1. Service Development

To develop a specific service:

1. Make changes to the service code
2. Rebuild and restart only that service:

```bash
docker-compose up -d --build <service-name>
```

For example, to rebuild the user service:

```bash
docker-compose up -d --build user-service
```

### 2. Database Migrations

When making database schema changes:

1. Create a new migration file in the appropriate service's migrations directory
2. Apply migrations:

```bash
docker-compose exec <service-name> alembic upgrade head
```

For example, to run migrations for the user service:

```bash
docker-compose exec user-service alembic upgrade head
```

### 3. Viewing Logs

To view logs for a specific service:

```bash
docker-compose logs -f <service-name>
```

To view logs for all services:

```bash
docker-compose logs -f
```

### 4. Testing

To run tests for a specific service:

```bash
docker-compose exec <service-name> pytest
```

For example, to run tests for the order service:

```bash
docker-compose exec order-service pytest
```

To run tests with coverage:

```bash
docker-compose exec <service-name> pytest --cov=app
```

### 5. Accessing PostgreSQL

To access the PostgreSQL database directly:

```bash
docker-compose exec postgres psql -U ubereats -d ubereats
```

### 6. Accessing Redis

To access the Redis CLI:

```bash
docker-compose exec redis redis-cli
```

### 7. Accessing Kafka

To list Kafka topics:

```bash
docker-compose exec kafka kafka-topics --list --bootstrap-server kafka:29092
```

## Development Tools

### Install Development Tools Locally

For better IDE integration, it's recommended to install development tools locally:

```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
```

### Code Formatting and Linting

Format your code with Black:

```bash
black .
```

Sort imports with isort:

```bash
isort .
```

Run linting checks:

```bash
flake8
```

Run type checking:

```bash
mypy .
```

### Pre-commit Hooks

We recommend setting up pre-commit hooks to automatically check your code before committing:

```bash
pre-commit install
```

## Demo Accounts

For testing purposes, you can use these demo accounts:

- **Admin**: See [admin_credentials.json](/services/user/admin_credentials.json)
- **Restaurant Owner**: See [restaurant_credentials.json](/services/user/restaurant_credentials.json)
- **Driver**: See [driver_credentials.json](/services/user/driver_credentials.json)

## Troubleshooting

### Common Issues

#### Services Fail to Start

**Problem**: Some services fail to start or keep restarting.

**Solution**: Check the logs for the failing service:

```bash
docker-compose logs <service-name>
```

Common causes include:
- Database connection issues
- Missing environment variables
- Port conflicts

#### Database Migration Errors

**Problem**: Database migrations fail to apply.

**Solution**: 
1. Check migration logs
2. If needed, reset the database:

```bash
docker-compose down -v
docker-compose up -d
```

#### Permission Issues on Linux

**Problem**: Permission issues when writing to mounted volumes.

**Solution**: Change ownership of the project directory:

```bash
sudo chown -R $(id -u):$(id -g) .
```

#### Memory Issues

**Problem**: Services crash due to insufficient memory.

**Solution**: Increase Docker's memory allocation in Docker Desktop settings or Docker daemon configuration.

### Getting Help

If you encounter issues not covered here:

1. Check existing GitHub issues
2. Ask in the development channel
3. Create a new issue on GitHub

## Next Steps

Now that your development environment is set up, you can:

1. Read the [Architecture Documentation](../architecture/README.md) to understand the system
2. Review the [API Documentation](../api/README.md) to understand the endpoints
3. Check the [Contribution Guidelines](./contributing.md) to learn how to contribute
4. Start working on your first feature or bug fix

## Advanced Configuration

### Custom Service Configuration

To override configuration for a specific service, create a `.env.<service-name>` file in the service directory.

### Remote Debugging

To enable remote debugging for a service:

1. Add debugging configuration to the service's Dockerfile
2. Update the docker-compose.yml to expose the debugging port
3. Configure your IDE to connect to the debugging port

### Performance Tuning

For better performance on development machines:

1. Disable non-essential services in docker-compose.yml
2. Reduce resource allocation for Kafka and Pinot
3. Use volume mounts for code directories to speed up development iterations

## Keeping Your Environment Updated

To update your development environment:

```bash
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

For a clean rebuild:

```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```