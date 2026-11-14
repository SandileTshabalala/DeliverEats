import { Link } from 'react-router-dom';
import { CheckCircle2, Clock, Loader2, XCircle } from 'lucide-react';
import { clsx } from 'clsx';

export type Outcome = 'checking' | 'paid' | 'waiting' | 'failed';

const LOOK: Record<Outcome, { icon: React.ReactNode; ring: string }> = {
    checking: { icon: <Loader2 size={44} className="text-brand-500 animate-spin" />, ring: 'bg-brand-500/10 border-brand-500/20' },
    paid: { icon: <CheckCircle2 size={48} className="text-green-500" />, ring: 'bg-green-500/10 border-green-500/25' },
    waiting: { icon: <Clock size={44} className="text-yellow-500" />, ring: 'bg-yellow-500/10 border-yellow-500/25' },
    failed: { icon: <XCircle size={48} className="text-red-500" />, ring: 'bg-red-500/10 border-red-500/25' },
};

export interface OutcomeAction { label: string; to: string; primary?: boolean }

/** The big result card shown after coming back from a payment page. */
const PaymentOutcome = ({ outcome, title, message, details = [], actions = [], note }: {
    outcome: Outcome;
    title: string;
    message: React.ReactNode;
    details?: { label: string; value: React.ReactNode }[];
    actions?: OutcomeAction[];
    note?: React.ReactNode;
}) => (
    <div className="min-h-[70vh] flex items-center justify-center px-4 py-10">
        <div role="status" aria-live="polite" className="w-full max-w-md text-center space-y-6 animate-in fade-in zoom-in-95 duration-500">
            <div className={clsx('mx-auto w-24 h-24 rounded-full border-2 flex items-center justify-center', LOOK[outcome].ring)}>
                {LOOK[outcome].icon}
            </div>
            <div className="space-y-2">
                <h1 className="text-3xl font-black tracking-tight text-white">{title}</h1>
                <p className="text-gray-400 font-medium leading-relaxed">{message}</p>
            </div>

            {details.length > 0 && (
                <dl className="bg-gray-900 border border-gray-800 rounded-2xl divide-y divide-gray-800 text-left">
                    {details.map(row => (
                        <div key={row.label} className="flex items-center justify-between gap-4 px-5 py-3.5">
                            <dt className="text-sm text-gray-500">{row.label}</dt>
                            <dd className="text-sm font-bold text-white text-right">{row.value}</dd>
                        </div>
                    ))}
                </dl>
            )}

            {note && <p className="text-sm text-gray-500 leading-relaxed">{note}</p>}

            {actions.length > 0 && (
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                    {actions.map(action => (
                        <Link key={action.label} to={action.to}
                            className={action.primary
                                ? 'px-6 py-3.5 rounded-2xl bg-brand-600 hover:bg-brand-700 text-white font-bold shadow-lg shadow-brand-600/25'
                                : 'px-6 py-3.5 rounded-2xl bg-gray-900 border border-gray-800 hover:border-gray-700 text-white font-bold'}>
                            {action.label}
                        </Link>
                    ))}
                </div>
            )}
        </div>
    </div>
);

export default PaymentOutcome;
