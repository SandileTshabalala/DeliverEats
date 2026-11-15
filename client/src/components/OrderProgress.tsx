import { lazy, Suspense, useEffect, useState } from 'react';
import { CheckCircle2, Circle, XCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import api from '../services/api';
import { errorMessage } from '../services/billing';
import { distanceKm, useFollowDriver } from '../hooks/useLiveLocation';
import { Stars } from './Stars';
// The map library is big: download it only when an order is actually on its way
const DriverMap = lazy(() => import('./DriverMap'));

const STEPS = [
    { key: 'placed', title: 'Order placed', detail: 'The restaurant has your order.' },
    { key: 'kitchen', title: 'Being prepared', detail: 'The kitchen accepted it and is cooking.' },
    { key: 'ready', title: 'Ready', detail: 'Packed and waiting for the driver.' },
    { key: 'on_the_way', title: 'On the way', detail: 'Your driver has it.' },
    { key: 'delivered', title: 'Delivered', detail: 'Enjoy!' },
];

const STEP_OF: Record<string, number> = {
    pending: 0, accepted: 1, waiting_for_driver: 1, preparing: 1, ready: 2, picked_up: 3, delivered: 4,
};

interface OrderLike {
    id: string;
    status: string;
    delivery_lat?: number | null;
    delivery_lng?: number | null;
    my_rating?: number | null;
}

/** Live driver position for an order that is on its way. */
const LiveTracking = ({ order }: { order: OrderLike }) => {
    const { position, available } = useFollowDriver(order.id, true);
    const [now, setNow] = useState(() => Date.now());
    useEffect(() => {
        const timer = setInterval(() => setNow(Date.now()), 15_000); // keep "updated x ago" fresh
        return () => clearInterval(timer);
    }, []);

    if (!available) return null;
    if (!position) {
        return <p className="text-sm text-gray-500">Waiting for your driver's location...</p>;
    }
    const hasDestination = order.delivery_lat != null && order.delivery_lng != null;
    const away = hasDestination ? distanceKm(position, { lat: order.delivery_lat!, lng: order.delivery_lng! }) : null;
    const secondsAgo = Math.max(0, Math.round((now - position.ts) / 1000));
    const when = secondsAgo < 60 ? 'just now' : `${Math.round(secondsAgo / 60)} min ago`;

    return (
        <div className="space-y-3" onClick={event => event.stopPropagation()}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="font-bold text-white">
                    {away == null ? 'Your driver is on the move' : away < 0.15 ? 'Your driver is arriving' : `Your driver is about ${away.toFixed(1)} km away`}
                </p>
                <p className="text-xs text-gray-400">Updated {when}</p>
            </div>
            <Suspense fallback={<div className="h-64 sm:h-72 rounded-2xl bg-gray-900 border border-gray-800 animate-pulse" />}>
                <DriverMap
                    driver={position}
                    destination={hasDestination ? { lat: order.delivery_lat!, lng: order.delivery_lng! } : null}
                    className="h-64 sm:h-72"
                />
            </Suspense>
        </div>
    );
};

/** Leave a 1-5 rating once the order is delivered. */
const RateOrder = ({ order, onRated }: { order: OrderLike; onRated: () => void }) => {
    const [rating, setRating] = useState(0);
    const [comment, setComment] = useState('');
    const [saving, setSaving] = useState(false);

    if (order.my_rating) {
        return (
            <div className="flex items-center space-x-3">
                <Stars value={order.my_rating} size={18} />
                <span className="text-sm text-gray-400">Thanks for rating this order.</span>
            </div>
        );
    }

    const submit = async () => {
        if (!rating) return;
        setSaving(true);
        try {
            await api.post(`/orders/${order.id}/review`, { rating, comment: comment.trim() || undefined });
            toast.success('Thanks for your rating!');
            onRated();
        } catch (error) {
            toast.error(errorMessage(error, 'Could not save your rating'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="space-y-3">
            <p className="text-sm font-bold text-white">How was it?</p>
            <Stars value={rating} onChange={setRating} />
            {rating > 0 && (
                <div className="space-y-3">
                    <textarea
                        value={comment}
                        onChange={event => setComment(event.target.value)}
                        maxLength={500}
                        rows={2}
                        placeholder="Anything to tell the restaurant? (optional)"
                        className="w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:border-brand-500 outline-none"
                    />
                    <button onClick={submit} disabled={saving} className="px-5 py-2.5 bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold rounded-xl text-sm">
                        {saving ? 'Saving...' : 'Send rating'}
                    </button>
                </div>
            )}
        </div>
    );
};

/** Where an order is, step by step, plus live tracking and rating when they apply. */
const OrderProgress = ({ order, onChanged }: { order: OrderLike; onChanged: () => void }) => {
    if (order.status === 'cancelled') {
        return (
            <div className="flex items-start space-x-3 text-red-400">
                <XCircle size={20} className="mt-0.5 flex-shrink-0" />
                <p className="text-sm font-bold">This order was cancelled.</p>
            </div>
        );
    }
    const current = STEP_OF[order.status] ?? 0;
    const waitingForDriver = order.status === 'waiting_for_driver';

    return (
        <div className="space-y-6">
            <ol className="space-y-4">
                {STEPS.map((step, index) => {
                    const done = index < current || (index === current && order.status === 'delivered');
                    const now = index === current && !done;
                    return (
                        <li key={step.key} className="flex items-start space-x-3">
                            {done
                                ? <CheckCircle2 size={20} className="text-green-500 mt-0.5 flex-shrink-0" />
                                : <Circle size={20} className={clsx("mt-0.5 flex-shrink-0", now ? "text-brand-500 fill-brand-500/20" : "text-gray-700")} />}
                            <div>
                                <p className={clsx("text-sm font-bold", done || now ? "text-white" : "text-gray-600")}>{step.title}</p>
                                {now && (
                                    <p className="text-xs text-gray-400">
                                        {waitingForDriver ? 'Being prepared. A driver will be assigned as soon as one is free.' : step.detail}
                                    </p>
                                )}
                            </div>
                        </li>
                    );
                })}
            </ol>
            {order.status === 'picked_up' && <LiveTracking order={order} />}
            {order.status === 'delivered' && <RateOrder order={order} onRated={onChanged} />}
        </div>
    );
};

export default OrderProgress;
