# gunicorn.conf.py

# Set the number of workers (you requested 1 worker)
workers = 1

# Bind to host and port
bind = "0.0.0.0:8080"

# Log level (optional but recommended)
loglevel = "debug"

# Optionally, you can set timeout (default is 30s)
timeout = 300

# Enable automatic worker restarting (useful during development)
reload = True
capture_output = True
enable_stdio_inheritance = True

