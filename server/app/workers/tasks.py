from app.db.session import SessionLocal
from app.services.order_service import cancel_stale_orders
from app.services.subscription_service import send_subscription_reminders
from app.workers.worker import celery_app


@celery_app.task
def run_stale_order_cancellation():
    """Cancels orders that waited too long for a driver or were never paid for."""
    db = SessionLocal()
    try:
        cancel_stale_orders(db)
    finally:
        db.close()


@celery_app.task
def run_subscription_reminders():
    """Tells restaurant owners when their plan is ending, overdue or has closed them."""
    db = SessionLocal()
    try:
        return send_subscription_reminders(db)
    finally:
        db.close()


@celery_app.task
def run_ozow_payment_checks():
    """Confirms recent Ozow payments with Ozow even if their notification did not arrive or match."""
    from app.services.payment_service import check_pending_ozow_payments
    db = SessionLocal()
    try:
        return check_pending_ozow_payments(db)
    finally:
        db.close()
