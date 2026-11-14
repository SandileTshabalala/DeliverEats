import { useEffect, useState } from 'react';
import { formatRand } from '../../context/CartContext';
import { formatDate, manage } from '../../services/billing';
import type { SubscriptionPayment } from '../../services/billing';
import { PERIODS } from '../../services/download';
import type { Period } from '../../services/download';
import { InvoiceButton, PeriodPicker, ReportButton } from '../../components/ReportControls';

const card = "bg-gray-900 border border-gray-800 rounded-2xl p-6 md:p-8 space-y-5";

const invoiceLabel = (payment: SubscriptionPayment) =>
    payment.invoice_number ? `INV-${String(payment.invoice_number).padStart(5, '0')}` : 'Invoice';

const Reports = () => {
    const [period, setPeriod] = useState<Period>(PERIODS[0].make());
    const [invoices, setInvoices] = useState<SubscriptionPayment[] | null>(null);

    useEffect(() => {
        // staff cannot see billing: show the list only when it loads
        manage.billingHistory().then(setInvoices).catch(() => setInvoices([]));
    }, []);

    return (
        <div className="space-y-8 max-w-4xl animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">Reports</h1>
                <p className="text-gray-400 mt-1">Download your sales for any period, and the invoices for your plan.</p>
            </div>

            <section className={card}>
                <h2 className="text-xl font-bold text-white">Sales</h2>
                <PeriodPicker period={period} onChange={setPeriod} />
                <div className="space-y-3">
                    <ReportButton kind="pdf" title="Sales report" path="/manage/reports/sales.pdf" period={period}
                        fallbackName="sales-report.pdf"
                        detail="Total sales, how customers paid, your best sellers and sales per day." />
                    <ReportButton kind="csv" title="All orders" path="/manage/reports/sales.csv" period={period}
                        fallbackName="orders.csv"
                        detail="Every order with customer, items, delivery fee, total and payment, as a spreadsheet." />
                </div>
                <p className="text-xs text-gray-600">Only the restaurant owner can download sales reports. An invoice for a single order is on the Orders page.</p>
            </section>

            <section className={card}>
                <h2 className="text-xl font-bold text-white">Plan invoices</h2>
                <p className="text-sm text-gray-500">What you paid us for your plan. Keep these for your records and tax.</p>
                {!invoices ? <p className="text-sm text-gray-500">Loading...</p> : invoices.length === 0 ? (
                    <p className="text-sm text-gray-500">No plan payments yet.</p>
                ) : (
                    <ul className="divide-y divide-gray-800">
                        {invoices.map(payment => (
                            <li key={payment.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                                <div>
                                    <p className="font-bold text-white">{invoiceLabel(payment)}</p>
                                    <p className="text-xs text-gray-500">{formatDate(payment.created_at)} · {payment.method === 'manual' ? 'EFT / cash' : 'PayFast'}</p>
                                </div>
                                <div className="flex items-center gap-3">
                                    <span className="font-bold text-white">{formatRand(payment.amount)}</span>
                                    <InvoiceButton path={`/manage/invoices/${payment.id}.pdf`} fallbackName={`${invoiceLabel(payment)}.pdf`} />
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </section>
        </div>
    );
};

export default Reports;
