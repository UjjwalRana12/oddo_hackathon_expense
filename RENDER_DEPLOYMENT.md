# Render deployment configuration
# https://render.com/docs/deploy-fastapi

# Build Command
pip install -r requirements.txt

# Start Command  
python production_startup.py

# Environment Variables to set in Render Dashboard:
# ENVIRONMENT=production
# DATABASE_URL=postgresql://username:password@hostname:5432/database_name
# SECRET_KEY=your-super-secure-secret-key-here
# DEBUG=false
# ALLOWED_ORIGINS=https://your-frontend-domain.com
# ALLOWED_HOSTS=your-app-name.onrender.com
# EMAIL_USER=your-email@domain.com
# EMAIL_PASSWORD=your-app-specific-password
# LOG_LEVEL=WARNING
# PORT=10000
# WORKERS=4

# Health Check Path: /health

# Auto-Deploy: Yes (connected to GitHub)

# Instance Type: Starter (can upgrade to Standard later)

# Region: Choose closest to your users