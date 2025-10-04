# Gunicorn configuration file for production deployment

import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', 8000)}"
backlog = 2048

# Worker processes
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2

# Restart workers after this many seconds
max_worker_memory = 300  # MB

# Logging
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
accesslog = "-"
errorlog = "-"
loglevel = os.getenv('LOG_LEVEL', 'info').lower()

# Process naming
proc_name = 'expense_system_api'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Server mechanics
preload_app = True
daemon = False
pidfile = '/tmp/gunicorn.pid'
user = None
group = None
tmp_upload_dir = '/tmp'

# SSL (if needed)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

def when_ready(server):
    server.log.info("🚀 Expense System API is ready to serve requests")

def worker_int(worker):
    worker.log.info("🔄 Worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("👷 Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("✅ Worker spawned (pid: %s)", worker.pid)

def worker_abort(worker):
    worker.log.info("❌ Worker received SIGABRT signal")