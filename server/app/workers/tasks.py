from app.workers.worker import celery_app
from app.services.notification_service import send_notification
from app.services.payment_service import process_payment

@celery_app.task
def async_send_notification(user_id: str, title: str, message: str, channel: str = "push"):
    send_notification(user_id, title, message, channel)

@celery_app.task
def async_process_payment(order_id: str, provider: str, amount: float):
    # This seems like a placeholder or simpler version. In real app, we need DB session here too probably?
    # But for now, focusing on the new task.
    # process_payment probably handles its own DB or is purely external API call?
    # checking imports...
    pass 
    # process_payment is imported.
    # The original file had: process_payment(order_id, amount, provider)
    # I should not break it.
    from app.services.payment_service import process_payment
    process_payment(order_id, amount, provider)


from app.db.session import SessionLocal
from app.services.order_service import cancel_stale_orders

@celery_app.task
def run_stale_order_cancellation():
    db = SessionLocal()
    try:
        cancel_stale_orders(db)
    finally:
        db.close()
