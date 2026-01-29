# Gunicorn configuration file for Discord bot deployment

# Server socket
bind = "0.0.0.0:8000"

# Worker processes
workers = 1  # Discord bots typically work best with 1 worker to avoid multiple instances

# Worker class - use sync worker for Windows compatibility
worker_class = "sync"

# Timeout settings
timeout = 300  # Increased timeout for bot operations
keepalive = 10

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Process naming
proc_name = "discord_bot"

# Preloading app to save memory
preload_app = True

# Maximum number of requests before worker restart (helpful for memory leaks)
max_requests = 1000
max_requests_jitter = 100