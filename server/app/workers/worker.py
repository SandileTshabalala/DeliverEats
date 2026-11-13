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
    },
    # each restaurant is only messaged once per stage, so running often is safe
    "subscription-reminders-every-6-hours": {
        "task": "app.workers.tasks.run_subscription_reminders",
        "schedule": 6 * 60 * 60.0,
    },
}
