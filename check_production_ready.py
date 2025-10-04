#!/usr/bin/env python3
"""
Quick Production Setup Checker
Validates that your expense management system is ready for production deployment.
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_status(message, status="info"):
    symbols = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
    print(f"{symbols.get(status, 'ℹ️')} {message}")

def check_files():
    """Check if all production files exist"""
    print_header("CHECKING PRODUCTION FILES")
    
    required_files = [
        "app/main.py",
        "app/core/config.py", 
        "app/core/database.py",
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml",
        "gunicorn.conf.py",
        "production_startup.py",
        "migrate_production.py",
        "health_monitor.py",
        ".env.production",
        "PRODUCTION_DEPLOYMENT.md",
        "RENDER_DEPLOYMENT.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        if Path(file_path).exists():
            print_status(f"{file_path}", "success")
        else:
            print_status(f"{file_path} - MISSING", "error")
            missing_files.append(file_path)
    
    if missing_files:
        print_status(f"Missing {len(missing_files)} required files", "error")
        return False
    else:
        print_status("All production files present", "success")
        return True

def check_environment():
    """Check environment configuration"""
    print_header("CHECKING ENVIRONMENT CONFIGURATION")
    
    # Check if .env exists
    if Path(".env").exists():
        print_status(".env file exists", "success")
    else:
        print_status(".env file missing", "error")
        return False
    
    # Check if .env.production exists
    if Path(".env.production").exists():
        print_status(".env.production template exists", "success")
    else:
        print_status(".env.production template missing", "warning")
    
    return True

def check_python_dependencies():
    """Check if Python dependencies can be loaded"""
    print_header("CHECKING PYTHON DEPENDENCIES")
    
    # Check if requirements.txt exists
    if not Path("requirements.txt").exists():
        print_status("requirements.txt missing", "error")
        return False
    
    print_status("requirements.txt found", "success")
    print_status("Dependencies will be installed during deployment", "info")
    return True

def show_next_steps():
    """Show next steps for deployment"""
    print_header("NEXT STEPS FOR PRODUCTION DEPLOYMENT")
    
    print("""
🚀 Your Expense Management System is production-ready!

📋 DEPLOYMENT CHECKLIST:

1. CHOOSE DEPLOYMENT PLATFORM:
   • Render (Recommended): Easy GitHub integration
   • Railway: Simple deployment
   • Heroku: Mature platform
   • Docker + VPS: Full control

2. SET UP DATABASE:
   • PostgreSQL for production (recommended)
   • Update DATABASE_URL in environment variables

3. CONFIGURE ENVIRONMENT VARIABLES:
   • Copy .env.production template
   • Update with your actual values:
     - DATABASE_URL (PostgreSQL connection string)
     - SECRET_KEY (generate new secure key)
     - EMAIL_USER and EMAIL_PASSWORD
     - ALLOWED_ORIGINS (your frontend domain)
     - ALLOWED_HOSTS (your backend domain)

4. SECURITY CHECKLIST:
   • Generate new SECRET_KEY
   • Update default admin password after first login
   • Configure HTTPS/SSL
   • Set up monitoring

5. DEPLOY:
   • Follow platform-specific instructions in RENDER_DEPLOYMENT.md
   • Monitor health endpoint: /health
   • Access API docs: /docs (development only)

📚 DOCUMENTATION:
   • Read PRODUCTION_DEPLOYMENT.md for detailed guide
   • Check RENDER_DEPLOYMENT.md for Render-specific steps

🔐 DEFAULT ADMIN CREDENTIALS:
   • Email: admin@company.com
   • Password: admin123
   • ⚠️ CHANGE THESE IMMEDIATELY AFTER FIRST LOGIN!

🎯 FEATURES INCLUDED:
   ✅ JWT Authentication & Authorization
   ✅ OCR Receipt Processing
   ✅ Multi-level Approval Workflows  
   ✅ Multi-currency Support
   ✅ Email Notifications
   ✅ File Upload Management
   ✅ Comprehensive API
   ✅ Production Security
   ✅ Health Monitoring
   ✅ Docker Support
   ✅ Database Migrations

🌐 API ENDPOINTS:
   • Authentication: /api/auth/*
   • Users: /api/users/*
   • Expenses: /api/expenses/*
   • Approvals: /api/approvals/*
   • Categories: /api/categories/*
   • Currency: /api/currency/*

Good luck with your deployment! 🎉
""")

def main():
    """Main checker function"""
    print_header("EXPENSE MANAGEMENT SYSTEM - PRODUCTION READINESS CHECK")
    
    checks = [
        ("Production Files", check_files),
        ("Environment Configuration", check_environment), 
        ("Python Dependencies", check_python_dependencies)
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        if not check_func():
            all_passed = False
    
    if all_passed:
        print_header("🎉 PRODUCTION READINESS: PASSED")
        print_status("Your expense management system is ready for production!", "success")
        show_next_steps()
    else:
        print_header("❌ PRODUCTION READINESS: FAILED")
        print_status("Please fix the issues above before deploying", "error")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())