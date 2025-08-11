#!/bin/sh

set -e

echo "Starting Django Polls Application..."

# Wait for database to be ready
if [ "$DATABASE_URL" ]; then
    echo "Waiting for database..."
    while ! nc -z db 5432; do
      sleep 0.1
    done
    echo "Database is ready!"
fi

# Change to the Django project directory
cd /app/mysite

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist
echo "Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('Superuser created: admin/admin')
else:
    print('Superuser already exists')
"

# Load initial data if exists
if [ -f "polls/fixtures/initial_data.json" ]; then
    echo "Loading initial data..."
    python manage.py loaddata initial_data || true
fi

echo "Django Polls Application is ready!"

# Execute the main command
exec "$@"