from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "lvovo_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"]
)

celery_app.conf.task_routes = {
    "app.workers.tasks.*": {"queue": "lvovo_queue"},
}

celery_app.conf.beat_schedule = {
    "cancel-stale-orders-every-minute": {
        "task": "app.workers.tasks.run_stale_order_cancellation",
        "schedule": 60.0,
    }
}
