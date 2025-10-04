#!/bin/bash
# Production deployment script for Render, Railway, Heroku, etc.

set -e  # Exit on any error

echo "🚀 Starting production deployment..."

# Check environment
if [ "$ENVIRONMENT" != "production" ]; then
    echo "⚠️ Warning: ENVIRONMENT is not set to 'production'"
    echo "Current environment: $ENVIRONMENT"
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

# Run database migrations
echo "🗄️ Running database migrations..."
python migrate_production.py

# Start the application
echo "🌟 Starting Expense System API..."
if [ "$USE_GUNICORN" = "true" ]; then
    exec gunicorn -c gunicorn.conf.py app.main:app
else
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-4}
fi