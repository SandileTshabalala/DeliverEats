"""
Production server:  ENV=production gunicorn -c gunicorn.conf.py app.main:app
(gunicorn does not run on Windows; there use:  uvicorn app.main:app --host 0.0.0.0 --port 8000)
"""
import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
worker_class = "uvicorn.workers.UvicornWorker"

# Keep this at 1. Live order updates are held in the memory of ONE process: with
# more workers, a restaurant connected to worker A would miss events raised on
# worker B. To scale past one worker, live updates must first be moved onto
# Redis pub/sub. One async worker comfortably serves a few hundred users.
workers = int(os.getenv("WEB_CONCURRENCY", "1"))

timeout = 60
graceful_timeout = 30
keepalive = 5
# nginx in front of this passes the real client address
forwarded_allow_ips = "*"
accesslog = "-"
errorlog = "-"
