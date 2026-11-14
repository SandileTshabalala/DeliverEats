import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import PaymentOutcome, { type Outcome } from '../../components/PaymentOutcome';
import { formatDate, manage, type BillingOverview, type SubscriptionPayment } from '../../services/billing';

import { serverDate } from '../../utils/orderDisplay';
// Back from paying the plan on PayFast. PayFast confirms to our server
// separately, so the latest payment is checked a few times.
const CHECK_AT_MS = [0, 3000, 7000, 12000, 20000, 35000];
const RECENT_MS = 2 * 60 * 60 * 1000; // a payment from the last 2 hours is this one

const SubscriptionPaymentResult = () => {
    const [params] = useSearchParams();
    const cancelled = params.get('status') === 'cancelled';
    const [outcome, setOutcome] = useState<Outcome>(cancelled ? 'failed' : 'checking');
    const [billing, setBilling] = useState<BillingOverview | null>(null);
    const [payment, setPayment] = useState<SubscriptionPayment | null>(null);

    useEffect(() => {
        let stopped = false;
        const timers: ReturnType<typeof setTimeout>[] = [];
        const check = async (last: boolean) => {
            if (stopped) return;
            try {
                const [overview, history] = await Promise.all([manage.billing(), manage.billingHistory()]);
                if (stopped) return;
                setBilling(overview);
                const recent = history.find(p => p.status === 'completed' && Date.now() - serverDate(p.created_at).getTime() < RECENT_MS);
                if (recent && !cancelled) {
                    stopped = true;
                    timers.forEach(clearTimeout);
                    setPayment(recent);
                    setOutcome('paid');
                    return;
                }
            } catch {
                // try again at the next check
            }
            if (last && !cancelled) setOutcome('waiting');
        };
        if (cancelled) check(false);
        else CHECK_AT_MS.forEach((ms, i) => timers.push(setTimeout(() => check(i === CHECK_AT_MS.length - 1), ms)));
        return () => { stopped = true; timers.forEach(clearTimeout); };
    }, [cancelled]);

    const subscription = billing?.subscription;
    const details = [
        ...(subscription?.plan ? [{ label: 'Plan', value: subscription.plan.name }] : []),
        ...(payment ? [{ label: 'Paid', value: `R ${Number(payment.amount).toFixed(2)}` }] : []),
        ...(outcome === 'paid' && subscription?.current_period_end
            ? [{ label: subscription.auto_renews ? 'Renews on' : 'Paid until', value: formatDate(subscription.current_period_end) }] : []),
    ];
    const settings = { label: 'Back to settings', to: '/restaurant/settings' };

    if (outcome === 'paid') {
        return (
            <PaymentOutcome outcome="paid" title="Payment successful"
                message="Thank you! Your plan is paid and your restaurant stays open to customers."
                details={details}
                actions={[{ label: 'Go to dashboard', to: '/restaurant/dashboard', primary: true }, settings]}
                note={subscription?.auto_renews ? 'PayFast will charge the plan automatically each period. Your invoices are in Reports.' : 'Your invoice is in Reports.'} />
        );
    }
    if (outcome === 'failed') {
        return (
            <PaymentOutcome outcome="failed" title="Payment cancelled"
                message="Nothing was charged and your plan has not changed."
                details={details}
                actions={[{ ...settings, label: 'Try again', primary: true }, { label: 'Go to dashboard', to: '/restaurant/dashboard' }]} />
        );
    }
    if (outcome === 'waiting') {
        return (
            <PaymentOutcome outcome="waiting" title="Confirming your payment"
                message={<>PayFast has not confirmed yet. <span className="font-bold text-white">Please don't pay again.</span> Your plan updates as soon as it does, usually within a few minutes.</>}
                details={details}
                actions={[{ ...settings, primary: true }]} />
        );
    }
    return (
        <PaymentOutcome outcome="checking" title="Checking your payment"
            message="One moment while we confirm it with PayFast. Please don't close this page or pay again." />
    );
};

export default SubscriptionPaymentResult;
