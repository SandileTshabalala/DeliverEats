"""
Downloadable documents: PDF invoices and reports, CSV exports.

- Subscription invoice: from the platform to a restaurant (what it paid for its plan)
- Order invoice: from a restaurant to its customer
- Sales report: a restaurant's own orders for a period (PDF summary + CSV detail)
- Income report: the platform's subscription income for a period (PDF + CSV)

A document is a "Tax invoice" only when the seller has a VAT number on file
(the platform's VAT number in Admin > Settings, the VAT number in a
restaurant's settings); prices are VAT-inclusive, so the VAT shown is the 15/115 share.

PDFs use the built-in Helvetica font, which only covers Latin-1: other
characters are replaced so a name in another script cannot break a download.
"""
import csv
import io
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Iterable, List, Optional, Sequence

from fpdf import FPDF

from app.core.config import settings
from app.services import business

VAT_RATE = Decimal("0.15")
CENT = Decimal("0.01")
BRAND = (217, 74, 11)       # brand-600
INK = (27, 24, 22)          # gray-900
MUTED = (125, 116, 107)     # gray-500
LINE = (230, 225, 219)      # gray-200


# ---------------------------------------------------------------- formatting

def _item_label(item) -> str:
    """'Kota (Hot, Extra chips)': the dish with what the customer picked."""
    from app.services.menu_options import describe
    picked = describe(getattr(item, "options", None))
    return f"{item.name} ({picked})" if picked else item.name

def local(moment: Optional[datetime]) -> Optional[datetime]:
    """Stored times are UTC; documents show the restaurants' local time."""
    return moment + timedelta(hours=settings.LOCAL_UTC_OFFSET_HOURS) if moment else None


def day_range_utc(start: date, end: date):
    """Local calendar days [start, end] as naive UTC datetimes [from, until)."""
    offset = timedelta(hours=settings.LOCAL_UTC_OFFSET_HOURS)
    begin = datetime(start.year, start.month, start.day) - offset
    until = datetime(end.year, end.month, end.day) + timedelta(days=1) - offset
    return begin, until


def money(value) -> str:
    amount = Decimal(str(value or 0)).quantize(CENT)
    sign = "-" if amount < 0 else ""
    return f"{sign}R {abs(amount):,.2f}".replace(",", " ")


def vat_included(total) -> Decimal:
    total = Decimal(str(total or 0))
    return (total * VAT_RATE / (1 + VAT_RATE)).quantize(CENT)


def safe(text) -> str:
    return str(text if text is not None else "").encode("latin-1", "replace").decode("latin-1")


def short_ref(order_id: str) -> str:
    return order_id[:8].upper()


def payment_method_label(name: Optional[str]) -> str:
    from app.services.restaurant_payment_service import DISPLAY_NAMES
    return DISPLAY_NAMES.get(name or "", (name or "Not chosen").replace("_", " ").title())


def platform_name() -> str:
    return business.display_name()


# ---------------------------------------------------------------- PDF building blocks
class Document(FPDF):
    def __init__(self, title: str, subtitle: str = ""):
        super().__init__(format="A4")
        self.doc_title, self.doc_subtitle = title, subtitle
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(16, 16, 16)
        self.alias_nb_pages()
        self.add_page()

    def header(self):
        self.set_text_color(*BRAND)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 6, safe(settings.APP_NAME.upper()), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*INK)
        self.set_font("Helvetica", "B", 20)
        self.cell(0, 10, safe(self.doc_title), new_x="LMARGIN", new_y="NEXT")
        if self.doc_subtitle:
            self.set_font("Helvetica", "", 10)
            self.set_text_color(*MUTED)
            self.cell(0, 5, safe(self.doc_subtitle), new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_text_color(*INK)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED)
        generated = local(datetime.utcnow()).strftime("%d %b %Y %H:%M")
        self.cell(0, 5, safe(f"Generated {generated}   ·   Page {self.page_no()} of {{nb}}"), align="R")

    # -- pieces
    def label(self, text: str):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 5, safe(text.upper()), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*INK)

    def parties(self, left_title: str, left: Sequence[str], right_title: str, right: Sequence[str]):
        """Two address blocks side by side (seller / buyer)."""
        top = self.get_y()
        width = (self.w - self.l_margin - self.r_margin) / 2 - 4
        for index, (title, lines) in enumerate(((left_title, left), (right_title, right))):
            x = self.l_margin + index * (width + 8)
            self.set_xy(x, top)
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*MUTED)
            self.cell(width, 5, safe(title.upper()), new_x="LEFT", new_y="NEXT")
            self.set_text_color(*INK)
            for number, line in enumerate(l for l in lines if l):
                self.set_x(x)
                self.set_font("Helvetica", "B" if number == 0 else "", 10)
                self.multi_cell(width, 5, safe(line), new_x="LEFT", new_y="NEXT")
            if index == 0:
                left_bottom = self.get_y()
        self.set_y(max(left_bottom, self.get_y()) + 6)

    def facts(self, pairs: Sequence[tuple]):
        """A row of small "label: value" facts (invoice no, date, ...)."""
        width = (self.w - self.l_margin - self.r_margin) / max(1, len(pairs))
        top = self.get_y()
        for index, (name, value) in enumerate(pairs):
            self.set_xy(self.l_margin + index * width, top)
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(*MUTED)
            self.cell(width, 5, safe(name.upper()), new_x="LEFT", new_y="NEXT")
            self.set_text_color(*INK)
            self.set_font("Helvetica", "", 10)
            self.cell(width, 6, safe(value))
        self.set_y(top + 14)

    def table(self, headings: Sequence[str], rows: Iterable[Sequence], widths: Sequence[float], align: Sequence[str]):
        def draw_head():
            self.set_font("Helvetica", "B", 9)
            self.set_fill_color(243, 240, 236)
            for heading, width, side in zip(headings, widths, align):
                self.cell(width, 7, safe(heading), align=side, fill=True)
            self.ln()

        draw_head()
        self.set_font("Helvetica", "", 9)
        for row in rows:
            if self.get_y() > self.h - 28:
                self.add_page()
                draw_head()
                self.set_font("Helvetica", "", 9)
            for value, width, side in zip(row, widths, align):
                text = safe(value)
                # keep long text (item lists, names) inside its column
                while text and self.get_string_width(text) > width - 2:
                    text = text[:-2]
                    if self.get_string_width(text + "...") <= width - 2:
                        text += "..."
                        break
                self.cell(width, 6.5, text, align=side, border="B")
            self.ln()
        self.ln(3)

    def totals(self, lines: Sequence[tuple]):
        """Right-aligned money lines; the last one is bold."""
        right_edge = self.w - self.r_margin
        for index, (name, value) in enumerate(lines):
            last = index == len(lines) - 1
            self.set_font("Helvetica", "B" if last else "", 11 if last else 10)
            self.set_x(right_edge - 90)
            self.cell(55, 7, safe(name), align="R")
            self.cell(35, 7, safe(value), align="R", new_x="LMARGIN", new_y="NEXT")

    def note(self, text: str):
        self.ln(4)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*MUTED)
        self.multi_cell(0, 5, safe(text))
        self.set_text_color(*INK)

    def stat_row(self, stats: Sequence[tuple]):
        width = (self.w - self.l_margin - self.r_margin) / len(stats)
        top = self.get_y()
        for index, (name, value) in enumerate(stats):
            x = self.l_margin + index * width
            self.set_draw_color(*LINE)
            self.rect(x + 1, top, width - 2, 18)
            self.set_xy(x + 4, top + 2)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*MUTED)
            self.cell(width - 8, 5, safe(name))
            self.set_xy(x + 4, top + 8)
            self.set_font("Helvetica", "B", 13)
            self.set_text_color(*INK)
            self.cell(width - 8, 8, safe(value))
        self.set_y(top + 24)

    def output_bytes(self) -> bytes:
        return bytes(self.output())


# ---------------------------------------------------------------- invoices
def subscription_invoice_pdf(payment, restaurant, owner, plan) -> bytes:
    """Invoice from the platform to a restaurant for one subscription payment."""
    details = business.current()
    tax_invoice = bool(details["vat_number"])
    pdf = Document("Tax Invoice" if tax_invoice else "Invoice", "Subscription")
    pdf.parties(
        "From", [business.display_name(details), details["business_address"], details["support_email"], details["support_phone"],
                 f"VAT no. {details['vat_number']}" if tax_invoice else None],
        "Bill to", [restaurant.name, restaurant.address,
                    f"{owner.name} {owner.sur_name}" if owner else None, owner.email if owner else None,
                    f"VAT no. {restaurant.vat_number}" if getattr(restaurant, "vat_number", None) else None],
    )
    method = "PayFast" if payment.method == "payfast" else "EFT / cash"
    pdf.facts([
        ("Invoice no.", invoice_number_text(payment)),
        ("Date", local(payment.created_at).strftime("%d %B %Y")),
        ("Paid with", method),
        ("Status", "Paid" if payment.status == "completed" else payment.status.title()),
    ])
    months = plan.interval_months if plan else 1
    period = "month" if months == 1 else ("year" if months == 12 else f"{months} months")
    pdf.table(
        ["Description", "Qty", "Amount"],
        [[f"{plan.name if plan else 'Subscription'} plan, billed per {period}", "1", money(payment.amount)]],
        widths=[118, 20, 40], align=["L", "C", "R"],
    )
    lines = [("Total", money(payment.amount))]
    if tax_invoice:
        lines.insert(0, ("Of which VAT (15%)", money(vat_included(payment.amount))))
    pdf.totals(lines)
    if payment.reference:
        pdf.note(f"Payment reference: {payment.reference}")
    return pdf.output_bytes()


def order_invoice_pdf(order, restaurant) -> bytes:
    """Invoice from a restaurant to its customer for one order."""
    vat_number = getattr(restaurant, "vat_number", None)
    pdf = Document("Tax Invoice" if vat_number else "Invoice", f"Order {short_ref(order.id)}")
    customer = order.customer
    pdf.parties(
        "From", [restaurant.name, restaurant.address, f"VAT no. {vat_number}" if vat_number else None,
                 f"Ordered through {settings.APP_NAME}"],
        "Bill to", [f"{customer.name} {customer.sur_name}" if customer else "Customer",
                    customer.contact_number if customer else None, order.delivery_address],
    )
    pdf.facts([
        ("Invoice no.", short_ref(order.id)),
        ("Date", local(order.created_at).strftime("%d %B %Y %H:%M")),
        ("Payment", payment_method_label(order.payment_method)),
        ("Status", {"completed": "Paid", "pay_on_delivery": "Pay on delivery", "pending": "Awaiting payment",
                    "failed": "Payment failed", "unpaid": "Unpaid"}.get(order.payment_status, order.payment_status)),
    ])
    rows = [[_item_label(item), str(item.quantity), money(item.price), money(Decimal(str(item.price)) * item.quantity)]
            for item in order.items]
    pdf.table(["Item", "Qty", "Price", "Amount"], rows, widths=[98, 20, 30, 30], align=["L", "C", "R", "R"])
    food = sum((Decimal(str(i.price)) * i.quantity for i in order.items), Decimal("0"))
    lines = [("Food", money(food)), ("Delivery", money(order.delivery_fee or 0))]
    if vat_number:
        lines.append(("Of which VAT (15%)", money(vat_included(order.total_amount))))
    lines.append(("Total", money(order.total_amount)))
    pdf.totals(lines)
    if _status(order) == "cancelled":
        pdf.note("This order was cancelled.")
    return pdf.output_bytes()


def invoice_number_text(payment) -> str:
    return f"INV-{payment.invoice_number:05d}" if getattr(payment, "invoice_number", None) else f"SUB-{payment.id[:8].upper()}"


# ---------------------------------------------------------------- restaurant sales
def _status(order) -> str:
    return getattr(order.status, "value", str(order.status))


def sales_rows(orders) -> List[list]:
    rows = []
    for order in sorted(orders, key=lambda o: o.created_at or datetime.min):
        when = local(order.created_at)
        food = sum((Decimal(str(i.price)) * i.quantity for i in order.items), Decimal("0"))
        rows.append([
            when.strftime("%Y-%m-%d"), when.strftime("%H:%M"), short_ref(order.id), _status(order).replace("_", " "),
            f"{order.customer.name} {order.customer.sur_name}" if order.customer else "",
            "; ".join(f"{i.quantity} x {_item_label(i)}" for i in order.items),
            f"{food:.2f}", f"{Decimal(str(order.delivery_fee or 0)):.2f}", f"{Decimal(str(order.total_amount)):.2f}",
            payment_method_label(order.payment_method), order.payment_status.replace("_", " "),
        ])
    return rows


SALES_HEADINGS = ["Date", "Time", "Order no.", "Status", "Customer", "Items", "Food (R)", "Delivery (R)",
                  "Total (R)", "Payment method", "Payment status"]


def sales_report_pdf(restaurant, orders, start: date, end: date) -> bytes:
    delivered = [o for o in orders if _status(o) == "delivered"]
    cancelled = [o for o in orders if _status(o) == "cancelled"]
    food = sum((Decimal(str(i.price)) * i.quantity for o in delivered for i in o.items), Decimal("0"))
    fees = sum((Decimal(str(o.delivery_fee or 0)) for o in delivered), Decimal("0"))
    total = sum((Decimal(str(o.total_amount)) for o in delivered), Decimal("0"))

    pdf = Document("Sales report", f"{restaurant.name}   ·   {start:%d %b %Y} to {end:%d %b %Y}")
    pdf.stat_row([
        ("Orders delivered", str(len(delivered))),
        ("Sales (delivered)", money(total)),
        ("Average order", money(total / len(delivered) if delivered else 0)),
        ("Cancelled", str(len(cancelled))),
    ])
    pdf.label("Sales")
    pdf.totals([("Food", money(food)), ("Delivery fees", money(fees)), ("Total sales", money(total))])
    pdf.ln(4)

    by_method = defaultdict(lambda: [0, Decimal("0")])
    for order in delivered:
        entry = by_method[payment_method_label(order.payment_method)]
        entry[0] += 1
        entry[1] += Decimal(str(order.total_amount))
    pdf.label("How customers paid (delivered orders)")
    pdf.table(["Payment method", "Orders", "Amount"],
              [[name, str(count), money(amount)] for name, (count, amount) in sorted(by_method.items())] or [["No delivered orders", "", ""]],
              widths=[118, 25, 35], align=["L", "C", "R"])

    items = Counter()
    item_sales = defaultdict(Decimal)
    for order in delivered:
        for item in order.items:
            items[item.name] += item.quantity
            item_sales[item.name] += Decimal(str(item.price)) * item.quantity
    pdf.label("Best sellers")
    pdf.table(["Item", "Sold", "Amount"],
              [[name, str(qty), money(item_sales[name])] for name, qty in items.most_common(10)] or [["Nothing sold", "", ""]],
              widths=[118, 25, 35], align=["L", "C", "R"])

    per_day = defaultdict(lambda: [0, Decimal("0")])
    for order in delivered:
        key = local(order.created_at).date()
        per_day[key][0] += 1
        per_day[key][1] += Decimal(str(order.total_amount))
    pdf.label("Per day")
    pdf.table(["Day", "Orders", "Sales"],
              [[day.strftime("%a %d %b %Y"), str(count), money(amount)] for day, (count, amount) in sorted(per_day.items())] or [["No sales in this period", "", ""]],
              widths=[118, 25, 35], align=["L", "C", "R"])
    pdf.note("Sales count delivered orders only. The full order list, including cancelled and unpaid orders, is in the CSV download.")
    return pdf.output_bytes()


# ---------------------------------------------------------------- platform income
INCOME_HEADINGS = ["Date", "Invoice no.", "Restaurant", "Plan", "Paid with", "Reference", "Amount (R)"]


def income_rows(payments) -> List[list]:
    return [[
        local(p.created_at).strftime("%Y-%m-%d"), invoice_number_text(p), p.restaurant_name, p.plan.name if p.plan else "",
        "PayFast" if p.method == "payfast" else "EFT / cash", p.reference or "", f"{Decimal(str(p.amount)):.2f}",
    ] for p in sorted(payments, key=lambda p: p.created_at or datetime.min)]


def income_report_pdf(payments, start: date, end: date) -> bytes:
    total = sum((Decimal(str(p.amount)) for p in payments), Decimal("0"))
    pdf = Document("Subscription income", f"{platform_name()}   ·   {start:%d %b %Y} to {end:%d %b %Y}")
    restaurants = {p.restaurant_name for p in payments}
    pdf.stat_row([("Income", money(total)), ("Payments", str(len(payments))), ("Restaurants that paid", str(len(restaurants)))])
    if business.current()["vat_number"]:
        pdf.totals([("Income", money(total)), ("Of which VAT (15%)", money(vat_included(total))),
                    ("Income excluding VAT", money(total - vat_included(total)))])
        pdf.ln(4)

    per_restaurant = defaultdict(lambda: [0, Decimal("0")])
    for payment in payments:
        per_restaurant[payment.restaurant_name][0] += 1
        per_restaurant[payment.restaurant_name][1] += Decimal(str(payment.amount))
    pdf.label("By restaurant")
    pdf.table(["Restaurant", "Payments", "Amount"],
              [[name, str(count), money(amount)] for name, (count, amount) in sorted(per_restaurant.items())] or [["No payments in this period", "", ""]],
              widths=[118, 25, 35], align=["L", "C", "R"])
    pdf.label("Payments")
    pdf.table(["Date", "Invoice", "Restaurant", "Paid with", "Amount"],
              [[r[0], r[1], r[2], r[4], money(r[6])] for r in income_rows(payments)] or [["", "", "None", "", ""]],
              widths=[24, 28, 68, 28, 30], align=["L", "L", "L", "L", "R"])
    return pdf.output_bytes()


# ---------------------------------------------------------------- CSV
def csv_bytes(headings: Sequence[str], rows: Iterable[Sequence]) -> bytes:
    """UTF-8 with a byte-order mark so Excel shows names and the R sign correctly."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headings)
    writer.writerows(rows)
    return ("﻿" + buffer.getvalue()).encode("utf-8")
