import { useEffect, useState } from 'react';
import { toast } from 'react-hot-toast';
import api from '../../services/api';
import { errorMessage, formatDate } from '../../services/billing';
import { formatRand } from '../../context/CartContext';
import { PERIODS } from '../../services/download';
import type { Period } from '../../services/download';
import { InvoiceButton, PeriodPicker, ReportButton } from '../../components/ReportControls';

interface PaidCharge {
    id: string;
    invoice_number: string;
    restaurant_name: string;
    plan_name: string | null;
    amount: string;
    method: string;
    created_at: string;
}

const card = "bg-gray-900 border border-gray-800 rounded-2xl p-6 md:p-8 space-y-5";

const Reports = () => {
    const [period, setPeriod] = useState<Period>(PERIODS[0].make());
    const [charges, setCharges] = useState<{ total: string; payments: PaidCharge[] } | null>(null);

    useEffect(() => {
        let active = true;
        api.get('/admin/reports/subscription-payments', { params: period })
            .then(response => { if (active) setCharges(response.data); })
            .catch(error => toast.error(errorMessage(error, 'Could not load the invoices')));
        return () => { active = false; };
    }, [period]);

    return (
        <div className="space-y-8 max-w-4xl animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">Reports</h1>
                <p className="text-gray-400 mt-1">Your subscription income and invoices, and how each restaurant is doing.</p>
            </div>

            <section className={card}>
                <h2 className="text-xl font-bold text-white">Period</h2>
                <PeriodPicker period={period} onChange={setPeriod} />
            </section>

            <section className={card}>
                <h2 className="text-xl font-bold text-white">Downloads</h2>
                <div className="space-y-3">
                    <ReportButton kind="pdf" title="Subscription income" path="/admin/reports/income.pdf" period={period}
                        fallbackName="subscription-income.pdf"
                        detail="Total income, per restaurant and every payment, ready to print or send to your accountant." />
                    <ReportButton kind="csv" title="Subscription payments" path="/admin/reports/subscriptions.csv" period={period}
                        fallbackName="subscription-payments.csv"
                        detail="Every paid invoice as a spreadsheet (opens in Excel or Google Sheets)." />
                    <ReportButton kind="csv" title="Restaurants" path="/admin/reports/restaurants.csv" period={period}
                        fallbackName="restaurants.csv"
                        detail="Each restaurant's owner, plan, payment standing and order count for the period." />
                </div>
            </section>

            <section className={card}>
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h2 className="text-xl font-bold text-white">Invoices</h2>
                    {charges && <p className="text-sm text-gray-400">{charges.payments.length} paid · {formatRand(charges.total)}</p>}
                </div>
                {!charges ? <p className="text-sm text-gray-500">Loading...</p> : charges.payments.length === 0 ? (
                    <p className="text-sm text-gray-500">No subscription payments in this period.</p>
                ) : (
                    <ul className="divide-y divide-gray-800">
                        {charges.payments.map(charge => (
                            <li key={charge.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                                <div className="min-w-0">
                                    <p className="font-bold text-white">{charge.restaurant_name}</p>
                                    <p className="text-xs text-gray-500">
                                        {charge.invoice_number} · {formatDate(charge.created_at)} · {charge.plan_name ?? 'Plan'} · {charge.method === 'payfast' ? 'PayFast' : 'EFT / cash'}
                                    </p>
                                </div>
                                <div className="flex items-center gap-3">
                                    <span className="font-bold text-white">{formatRand(charge.amount)}</span>
                                    <InvoiceButton path={`/admin/invoices/${charge.id}.pdf`} fallbackName={`${charge.invoice_number}.pdf`} />
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
