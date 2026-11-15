import { useEffect } from 'react';
import { X, MapPin, Store, User, Phone, Navigation, Banknote, CheckCircle2 } from 'lucide-react';
import { formatRand } from '../context/CartContext';
import { orderRef, fullName, phoneHref } from '../services/orders';
import type { OrderPerson } from '../services/orders';

import { serverDate } from '../utils/orderDisplay';
import { describePicks, type PickedOption } from '../utils/menu';
export interface OrderDetails {
    id: string;
    status: string;
    created_at: string;
    total_amount: number | string;
    delivery_fee?: number | string | null;
    restaurant_name?: string;
    restaurant?: { name: string; address: string } | null;
    customer?: OrderPerson | null;
    driver?: OrderPerson | null;
    delivery_address?: string | null;
    delivery_lat?: number | null;
    delivery_lng?: number | null;
    payment_status?: string;
    payment_method?: string | null;
    items: { id?: string; name: string; quantity: number; price: number | string; options?: PickedOption[] | null }[];
}

interface Props {
    order: OrderDetails | null;
    onClose: () => void;
    /** Extra buttons for the person viewing (e.g. the driver's "Pick up" / "Complete") */
    actions?: React.ReactNode;
}

const row = "flex items-start space-x-3";
const heading = "text-[10px] font-black uppercase tracking-widest text-gray-500";

/** What the driver must do about money at the door. */
const paymentInstruction = (order: OrderDetails) => {
    const total = formatRand(order.total_amount);
    if (order.payment_status === 'completed') {
        return { paid: true, text: 'Already paid. Do not collect any money.' };
    }
    if (order.payment_method === 'card_delivery') {
        return { paid: false, text: `Collect ${total} with the card machine.` };
    }
    if (order.payment_method === 'cash_delivery') {
        return { paid: false, text: `Collect ${total} in cash.` };
    }
    return { paid: false, text: `Payment not confirmed yet (${total}).` };
};

const OrderDetailsModal = ({ order, onClose, actions }: Props) => {
    useEffect(() => {
        if (!order) return;
        const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [order, onClose]);

    if (!order) return null;

    const payment = paymentInstruction(order);
    const subtotal = order.items.reduce((sum, item) => sum + Number(item.price) * item.quantity, 0);
    const deliveryFee = Number(order.delivery_fee ?? 0);
    const hasPin = order.delivery_lat != null && order.delivery_lng != null;
    // Opens the phone's maps app with directions to the customer
    const directions = hasPin
        ? `https://www.google.com/maps/dir/?api=1&destination=${order.delivery_lat},${order.delivery_lng}`
        : order.delivery_address
            ? `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(order.delivery_address)}`
            : null;

    return (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-end sm:items-center justify-center sm:p-4" onClick={onClose}>
            <div
                role="dialog"
                aria-modal="true"
                aria-label={`Order ${orderRef(order.id)}`}
                onClick={event => event.stopPropagation()}
                className="bg-gray-900 border border-gray-800 rounded-t-3xl sm:rounded-3xl w-full max-w-lg max-h-[92vh] overflow-y-auto"
            >
                <div className="sticky top-0 bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
                    <div>
                        <h3 className="text-xl font-bold text-white">Order {orderRef(order.id)}</h3>
                        <p className="text-xs text-gray-500">
                            {serverDate(order.created_at).toLocaleString('en-ZA', { dateStyle: 'medium', timeStyle: 'short' })}
                            <span className="mx-2">·</span>
                            <span className="uppercase font-bold text-brand-500">{order.status.replace(/_/g, ' ')}</span>
                        </p>
                    </div>
                    <button aria-label="Close" onClick={onClose} className="p-2 text-gray-500 hover:text-white rounded-lg"><X size={20} /></button>
                </div>

                <div className="p-6 space-y-6">
                    {/* Money first: it is what the driver most needs to get right */}
                    <div className={`${row} rounded-2xl border px-4 py-3 ${payment.paid ? 'bg-green-500/10 border-green-500/20 text-green-500' : 'bg-yellow-500/10 border-yellow-500/20 text-yellow-500'}`}>
                        {payment.paid ? <CheckCircle2 size={20} className="mt-0.5 flex-shrink-0" /> : <Banknote size={20} className="mt-0.5 flex-shrink-0" />}
                        <p className="font-bold text-sm">{payment.text}</p>
                    </div>

                    <section className="space-y-3">
                        <p className={heading}>Collect from</p>
                        <div className={row}>
                            <Store size={18} className="text-brand-500 mt-0.5 flex-shrink-0" />
                            <div>
                                <p className="font-bold text-white">{order.restaurant?.name || order.restaurant_name || 'Restaurant'}</p>
                                {order.restaurant?.address && <p className="text-sm text-gray-400">{order.restaurant.address}</p>}
                            </div>
                        </div>
                    </section>

                    <section className="space-y-3">
                        <p className={heading}>Deliver to</p>
                        <div className={row}>
                            <User size={18} className="text-brand-500 mt-0.5 flex-shrink-0" />
                            <p className="font-bold text-white">{fullName(order.customer) || 'Customer'}</p>
                        </div>
                        <div className={row}>
                            <MapPin size={18} className="text-brand-500 mt-0.5 flex-shrink-0" />
                            <p className="text-sm text-gray-300">{order.delivery_address || 'No delivery address was given for this order.'}</p>
                        </div>
                        <div className="flex flex-wrap gap-2 pt-1">
                            {order.customer?.contact_number && (
                                <a href={phoneHref(order.customer.contact_number)} className="flex items-center space-x-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-xl text-sm">
                                    <Phone size={16} /><span>Call {order.customer.contact_number}</span>
                                </a>
                            )}
                            {directions && (
                                <a href={directions} target="_blank" rel="noopener noreferrer" className="flex items-center space-x-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-xl text-sm">
                                    <Navigation size={16} /><span>Directions</span>
                                </a>
                            )}
                        </div>
                    </section>

                    <section className="space-y-3">
                        <p className={heading}>Items ({order.items.reduce((sum, item) => sum + item.quantity, 0)})</p>
                        <ul className="divide-y divide-gray-800">
                            {order.items.map((item, index) => (
                                <li key={item.id ?? index} className="flex justify-between py-2 text-sm">
                                    <span className="text-gray-300">
                                        <span className="text-brand-500 font-bold mr-2">{item.quantity} x</span>{item.name}
                                        {item.options && item.options.length > 0 && (
                                            <span className="block pl-7 text-xs text-gray-500">{describePicks(item.options)}</span>
                                        )}
                                    </span>
                                    <span className="text-white font-bold">{formatRand(Number(item.price) * item.quantity)}</span>
                                </li>
                            ))}
                        </ul>
                        <dl className="text-sm space-y-1 border-t border-gray-800 pt-3">
                            <div className="flex justify-between text-gray-400"><dt>Food</dt><dd>{formatRand(subtotal)}</dd></div>
                            <div className="flex justify-between text-gray-400"><dt>Delivery</dt><dd>{deliveryFee > 0 ? formatRand(deliveryFee) : 'Free'}</dd></div>
                            <div className="flex justify-between text-white font-bold text-base pt-1"><dt>Total</dt><dd>{formatRand(order.total_amount)}</dd></div>
                        </dl>
                    </section>

                    {actions && <div className="flex flex-wrap gap-3 pt-2">{actions}</div>}
                </div>
            </div>
        </div>
    );
};

export default OrderDetailsModal;
