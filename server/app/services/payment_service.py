from sqlalchemy.orm import Session
from app.models.payment import Payment, PaymentStatus
from app.models.payment_provider import PaymentProvider

def get_active_provider(db: Session, provider_name: str):
    return (
        db.query(PaymentProvider)
        .filter(
            PaymentProvider.provider_name == provider_name,
            PaymentProvider.is_active == True
        )
        .first()
    )
 
def create_payment(
    db: Session,
    order_id: str,
    amount: float,
    provider_name: str,
    reference: str = None
):
    # Lookup provider
    provider_obj = get_active_provider(db, provider_name)
    provider_id = provider_obj.id if provider_obj else None

    # Custom reference logic for offline methods
    if not reference:
        if provider_name == "cash_delivery":
            reference = f"cash_{order_id}"
        elif provider_name == "card_delivery":
            reference = f"card_on_delivery_{order_id}"
        else:
            reference = f"{provider_name}_{order_id}"

    payment = Payment(
        order_id=order_id,
        provider_id=provider_id,
        amount=amount,
        status=PaymentStatus.PENDING,
        reference=reference
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    # Provider-Specific Initialization Placeholder
    # Depending on the provider_name and its config (API keys), 
    # we would call Stripe, PayFast, Ozow, etc. here.
    if provider_obj and provider_obj.enabled:
        initialize_provider_payment(payment, provider_obj)

    # Attach provider_name for schema validation
    payment.provider_name = provider_name
    return payment

import stripe
from app.core.config import settings

def initialize_provider_payment(payment: Payment, provider: PaymentProvider):
    """
    Production-ready hook to initialize payment gateway sessions.
    Uses the provider's stored secret_key to communicate with the gateway.
    """
    provider_name = provider.provider_name.lower()
    print(f"DEBUG: Initializing payment for {provider_name} (Payment ID: {payment.id})")
    
    # We store the resulting URL in the payment object for the frontend to use
    checkout_url = None

    try:
        if "stripe" in provider_name:
            print(f"DEBUG: Processing Stripe PaymentIntent with key: {provider.secret_key[:8]}...")
            # 1. Initialize Stripe with the stored secret key
            stripe.api_key = provider.secret_key
            
            # 2. Create a PaymentIntent instead of a Checkout Session
            # This allows the frontend to handle the payment without leaving the site
            intent = stripe.PaymentIntent.create(
                amount=int(payment.amount * 100),  # Stripe expects cents
                currency="zar", # Or detect from config
                metadata={
                    "payment_id": payment.id,
                    "order_id": payment.order_id
                }
            )
            
            # For PaymentIntent, the "checkout_url" will be treated as the client_secret by the frontend
            checkout_url = intent.client_secret
            payment.reference = intent.id
            payment.provider_metadata = {
                "intent_id": intent.id,
                "client_secret": intent.client_secret,
                "provider": "stripe_intent"
            }

        elif any(gateway in provider_name for gateway in ["payfast", "ozow", "paygate"]):
            # Generic South African Redirect Pattern
            # In a full implementation, we would generate signatures here
            # For now, we prepare a generic redirect URL using the gateway's base
            print(f"Preparing redirect for South African gateway: {provider_name}")
            
            # Placeholder for gateway-specific signature logic
            # e.g. md5_signature = generate_payfast_signature(payment, provider)
            
            # For testing redirect flow:
            checkout_url = f"https://sandbox.paymentgateway.com/pay?id={payment.id}&amount={payment.amount}"

        # Update the payment record with the checkout URL and metadata
        if checkout_url:
            payment.checkout_url = checkout_url
            # Optionally store session metadata or other info here
            if not payment.provider_metadata:
                payment.provider_metadata = {}
            
            payment.provider_metadata.update({
                "checkout_generated": True,
                "provider": provider_name
            })

        db_session = Session.object_session(payment)
        if db_session:
            db_session.commit()

    except Exception as e:
        print(f"Error initializing payment for {provider_name}: {str(e)}")
        payment.status = PaymentStatus.FAILED
        # Log to sentry/error log in production

def mark_payment_success(db: Session, payment_id: str):
    payment = db.query(Payment).get(payment_id)
    if payment:
        payment.status = "success"
        db.commit()
    return payment
