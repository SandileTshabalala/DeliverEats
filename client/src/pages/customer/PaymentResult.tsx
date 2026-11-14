import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import PaymentOutcome, { type Outcome } from '../../components/PaymentOutcome';
import api from '../../services/api';
import { orderRef, orderService, type Order } from '../../services/orders';

// Coming back from the payment page proves nothing by itself: the payment
// company confirms to our server separately, usually within seconds. So we ask
// again a few times before saying "still confirming".
const CHECK_AT_MS = [0, 2500, 5000, 9000, 15000, 25000, 40000];

const rand = (value?: number | string | null) => value == null ? '' : `R ${Number(value).toFixed(2)}`;

const PaymentResult = () => {
    const [params] = useSearchParams();
    const orderId = params.get('order');
    const returned = params.get('status') ?? 'returned';   // success | returned | cancelled
    const [outcome, setOutcome] = useState<Outcome>(returned === 'cancelled' ? 'failed' : 'checking');
    const [order, setOrder] = useState<Order | null>(null);

    useEffect(() => {
        if (!orderId) {
            setOutcome(returned === 'cancelled' ? 'failed' : 'waiting');
            return;
        }
        let stopped = false;
        const timers: ReturnType<typeof setTimeout>[] = [];

        const loadOrder = () => orderService.getMyOrders()
            .then(list => { if (!stopped) setOrder(list.find(o => o.id === orderId) ?? null); })
            .catch(() => undefined);

        const check = async (last: boolean) => {
            if (stopped) return;
            try {
                const { data } = await api.post(`/payments/order/${orderId}/check`);
                if (stopped) return;
                if (data.payment_status === 'completed') {
                    stopped = true;
                    timers.forEach(clearTimeout);
                    setOutcome('paid');
                    loadOrder();
                    return;
                }
                if (data.payment_status === 'failed') {
                    stopped = true;
                    timers.forEach(clearTimeout);
                    setOutcome('failed');
                    return;
                }
            } catch {
                // network hiccup: the next check will try again
            }
            if (last) setOutcome('waiting');
        };

        loadOrder();
        if (returned === 'cancelled') {
            // the customer pressed cancel; still check once in case it went through anyway
            check(false);
        } else {
            CHECK_AT_MS.forEach((ms, i) => timers.push(setTimeout(() => check(i === CHECK_AT_MS.length - 1), ms)));
        }
        return () => { stopped = true; timers.forEach(clearTimeout); };
    }, [orderId, returned]);

    const details = order ? [
        { label: 'Order', value: orderRef(order.id) },
        ...(order.restaurant_name ? [{ label: 'Restaurant', value: order.restaurant_name }] : []),
        ...(order.total_amount != null ? [{ label: outcome === 'paid' ? 'Paid' : 'Amount', value: rand(order.total_amount) }] : []),
    ] : [];
    const menu = order?.restaurant_id ? `/customer/menu/${order.restaurant_id}` : '/customer';

    if (outcome === 'paid') {
        return (
            <PaymentOutcome
                outcome="paid" title="Payment successful"
                message="Thank you! Your order is with the kitchen now. We'll keep you posted as it's prepared and on its way."
                details={details}
                actions={[{ label: 'Track my order', to: '/customer/orders', primary: true }, { label: 'Keep browsing', to: '/customer' }]}
            />
        );
    }
    if (outcome === 'failed') {
        return (
            <PaymentOutcome
                outcome="failed" title="Payment not completed"
                message="You were not charged, and the order was not sent to the kitchen."
                details={details}
                actions={[{ label: 'Order again', to: menu, primary: true }, { label: 'My orders', to: '/customer/orders' }]}
                note="If money did leave your account, it was not for this order. Contact your bank or the restaurant with the order number above."
            />
        );
    }
    if (outcome === 'waiting') {
        return (
            <PaymentOutcome
                outcome="waiting" title="Confirming your payment"
                message={<>The payment company has not confirmed yet. <span className="font-bold text-white">Please don't pay again.</span> We'll let you know the moment it comes through, usually within a few minutes.</>}
                details={details}
                actions={[{ label: 'My orders', to: '/customer/orders', primary: true }, { label: 'Keep browsing', to: '/customer' }]}
            />
        );
    }
    return (
        <PaymentOutcome
            outcome="checking" title="Checking your payment"
            message="One moment while we confirm it with the payment company. Please don't close this page or pay again."
            details={details}
        />
    );
};

export default PaymentResult;
