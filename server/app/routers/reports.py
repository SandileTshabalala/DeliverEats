"""
Downloads: reports and invoices for the platform owner, restaurants and customers.

Every query here is scoped the same way as the rest of the API: a restaurant
only ever gets its own orders and invoices, a customer only their own orders.
"""
import re
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_db, require_role
from app.core.roles import Role
from app.core.tenancy import get_current_restaurant, is_owner
from app.models.order import Order
from app.models.restaurant import Restaurant
from app.models.subscription import SubscriptionPayment, utcnow
from app.services import documents
from app.services import subscription_service as subs
from app.services.order_service import ORDER_LOAD_OPTIONS, get_order
from app.utils.OrderStatus import OrderStatus

router = APIRouter(tags=["Reports"])

admin_only = require_role(Role.SUPER_ADMIN)
restaurant_user = require_role(Role.RESTAURANT_ADMIN)

MAX_DAYS = 366


def period(start: Optional[date], end: Optional[date]):
    """Default: from the 1st of this month to today (local time)."""
    today = documents.local(utcnow()).date()
    end = end or today
    start = start or end.replace(day=1)
    if start > end:
        raise HTTPException(status_code=400, detail="The start date must be before the end date")
    if (end - start).days >= MAX_DAYS:
        raise HTTPException(status_code=400, detail="Choose a period of at most one year")
    return start, end


def download(content: bytes, filename: str, media_type: str) -> Response:
    return Response(content=content, media_type=media_type, headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-store",  # financial documents: never cached by proxies
    })


def pdf(content: bytes, filename: str) -> Response:
    return download(content, filename, "application/pdf")


def csv(content: bytes, filename: str) -> Response:
    return download(content, filename, "text/csv; charset=utf-8")


def slug(text: str) -> str:
    """Plain ASCII for file names: HTTP headers cannot carry other characters (a name like '日本' crashed the download)."""
    cleaned = "".join(ch if ch.isascii() and ch.isalnum() else "-" for ch in (text or ""))
    return re.sub(r"-{2,}", "-", cleaned).strip("-").lower()[:40] or "restaurant"


def _completed_payments(db: Session, start: date, end: date, restaurant_id: Optional[str] = None):
    begin, until = documents.day_range_utc(start, end)
    query = db.query(SubscriptionPayment).options(joinedload(SubscriptionPayment.plan)).filter(
        SubscriptionPayment.status == "completed",
        SubscriptionPayment.created_at >= begin,
        SubscriptionPayment.created_at < until,
    )
    if restaurant_id:
        query = query.filter(SubscriptionPayment.restaurant_id == restaurant_id)
    payments = query.all()
    names = dict(db.query(Restaurant.id, Restaurant.name).all())
    for payment in payments:
        payment.restaurant_name = names.get(payment.restaurant_id, "Removed restaurant")
        subs.ensure_invoice_number(db, payment)
    return payments


def _invoice(db: Session, payment: SubscriptionPayment) -> Response:
    if payment.status != "completed":
        raise HTTPException(status_code=404, detail="There is no invoice for an unpaid charge")
    subs.ensure_invoice_number(db, payment)
    restaurant = db.query(Restaurant).filter(Restaurant.id == payment.restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    content = documents.subscription_invoice_pdf(payment, restaurant, restaurant.admin, payment.plan)
    return pdf(content, f"{documents.invoice_number_text(payment)}.pdf")


# ================================================================ platform owner
@router.get("/admin/reports/subscription-payments")
def admin_subscription_payments(
    start: Optional[date] = Query(None, alias="from"),
    end: Optional[date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    admin=Depends(admin_only),
):
    """Paid subscription charges in a period, for the invoice list on screen."""
    start, end = period(start, end)
    payments = sorted(_completed_payments(db, start, end), key=lambda p: p.created_at, reverse=True)
    return {
        "from": start, "to": end,
        "total": sum((p.amount for p in payments), 0),
        "payments": [
            {"id": p.id, "invoice_number": documents.invoice_number_text(p), "restaurant_name": p.restaurant_name,
             "plan_name": p.plan.name if p.plan else None, "amount": p.amount, "method": p.method,
             "created_at": p.created_at}
            for p in payments
        ],
    }


@router.get("/admin/reports/income.pdf")
def admin_income_pdf(
    start: Optional[date] = Query(None, alias="from"),
    end: Optional[date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    admin=Depends(admin_only),
):
    start, end = period(start, end)
    content = documents.income_report_pdf(_completed_payments(db, start, end), start, end)
    return pdf(content, f"subscription-income-{start}-to-{end}.pdf")


@router.get("/admin/reports/subscriptions.csv")
def admin_subscriptions_csv(
    start: Optional[date] = Query(None, alias="from"),
    end: Optional[date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    admin=Depends(admin_only),
):
    start, end = period(start, end)
    rows = documents.income_rows(_completed_payments(db, start, end))
    return csv(documents.csv_bytes(documents.INCOME_HEADINGS, rows), f"subscription-payments-{start}-to-{end}.csv")


@router.get("/admin/reports/restaurants.csv")
def admin_restaurants_csv(
    start: Optional[date] = Query(None, alias="from"),
    end: Optional[date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    admin=Depends(admin_only),
):
    """One line per restaurant: owner, plan, standing and activity in the period (counts, not their takings)."""
    start, end = period(start, end)
    begin, until = documents.day_range_utc(start, end)

    def counts(*conditions):
        return dict(db.query(Order.restaurant_id, func.count(Order.id)).filter(
            Order.created_at >= begin, Order.created_at < until, *conditions
        ).group_by(Order.restaurant_id).all())

    placed = counts(Order.status != OrderStatus.CANCELLED)
    delivered = counts(Order.status == OrderStatus.DELIVERED)
    paid = {}
    for payment in _completed_payments(db, start, end):
        paid[payment.restaurant_id] = paid.get(payment.restaurant_id, 0) + payment.amount

    rows = []
    for restaurant in db.query(Restaurant).order_by(Restaurant.name.asc()).all():
        owner = restaurant.admin
        state = subs.describe(db, restaurant)
        rows.append([
            restaurant.name, restaurant.category or "", restaurant.address,
            f"{owner.name} {owner.sur_name}" if owner else "", owner.contact_number if owner else "", owner.email if owner else "",
            state["plan"].name if state["plan"] else "", state["status"].replace("_", " "),
            documents.local(state["current_period_end"]).strftime("%Y-%m-%d") if state["current_period_end"] else "",
            "yes" if state["is_live"] else "no",
            placed.get(restaurant.id, 0), delivered.get(restaurant.id, 0), f"{paid.get(restaurant.id, 0):.2f}",
        ])
    headings = ["Restaurant", "Category", "Address", "Owner", "Owner phone", "Owner email", "Plan", "Subscription",
                "Paid until", "Visible to customers", f"Orders {start} to {end}", "Delivered", "Subscription paid (R)"]
    return csv(documents.csv_bytes(headings, rows), f"restaurants-{start}-to-{end}.csv")


@router.get("/admin/invoices/{payment_id}.pdf")
def admin_invoice(payment_id: str, db: Session = Depends(get_db), admin=Depends(admin_only)):
    payment = db.query(SubscriptionPayment).filter(SubscriptionPayment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _invoice(db, payment)


# ================================================================ restaurant
def _owner_only(restaurant: Restaurant, user) -> None:
    if not is_owner(restaurant, user):
        raise HTTPException(status_code=403, detail="Only the restaurant owner can download sales reports and plan invoices")


def _restaurant_orders(db: Session, restaurant: Restaurant, start: date, end: date):
    begin, until = documents.day_range_utc(start, end)
    return db.query(Order).options(*ORDER_LOAD_OPTIONS).filter(
        Order.restaurant_id == restaurant.id, Order.created_at >= begin, Order.created_at < until,
    ).all()


@router.get("/manage/reports/sales.pdf")
def restaurant_sales_pdf(
    start: Optional[date] = Query(None, alias="from"),
    end: Optional[date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
    user=Depends(restaurant_user),
):
    _owner_only(restaurant, user)
    start, end = period(start, end)
    content = documents.sales_report_pdf(restaurant, _restaurant_orders(db, restaurant, start, end), start, end)
    return pdf(content, f"sales-{slug(restaurant.name)}-{start}-to-{end}.pdf")


@router.get("/manage/reports/sales.csv")
def restaurant_sales_csv(
    start: Optional[date] = Query(None, alias="from"),
    end: Optional[date] = Query(None, alias="to"),
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
    user=Depends(restaurant_user),
):
    _owner_only(restaurant, user)
    start, end = period(start, end)
    rows = documents.sales_rows(_restaurant_orders(db, restaurant, start, end))
    return csv(documents.csv_bytes(documents.SALES_HEADINGS, rows), f"orders-{slug(restaurant.name)}-{start}-to-{end}.csv")


@router.get("/manage/invoices/{payment_id}.pdf")
def restaurant_plan_invoice(
    payment_id: str,
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
    user=Depends(restaurant_user),
):
    _owner_only(restaurant, user)
    payment = db.query(SubscriptionPayment).filter(
        SubscriptionPayment.id == payment_id, SubscriptionPayment.restaurant_id == restaurant.id
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _invoice(db, payment)


@router.get("/manage/orders/{order_id}/invoice.pdf")
def restaurant_order_invoice(
    order_id: str,
    db: Session = Depends(get_db),
    restaurant: Restaurant = Depends(get_current_restaurant),
):
    """Owner and staff can print an invoice for any of their own restaurant's orders."""
    order = get_order(db, order_id)
    if not order or order.restaurant_id != restaurant.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return pdf(documents.order_invoice_pdf(order, restaurant), f"invoice-{documents.short_ref(order.id)}.pdf")


# ================================================================ customer
@router.get("/orders/{order_id}/invoice.pdf")
def customer_order_invoice(order_id: str, db: Session = Depends(get_db), user=Depends(require_role(Role.CUSTOMER))):
    order = get_order(db, order_id)
    if not order or order.customer_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.payment_status != "completed" and documents._status(order) != "delivered":
        raise HTTPException(status_code=409, detail="The invoice is available once the order is paid or delivered")
    return pdf(documents.order_invoice_pdf(order, order.restaurant), f"invoice-{documents.short_ref(order.id)}.pdf")
