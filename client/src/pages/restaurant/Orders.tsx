import { useState, useEffect, useCallback } from 'react';
import { InvoiceButton } from '../../components/ReportControls';
import {
    ShoppingBag,
    Clock,
    XCircle,
    User,
    Truck,
    RefreshCcw,
    AlertTriangle,
} from 'lucide-react';
import { orderService, orderRef, fullName, phoneHref } from '../../services/orders';
import { formatRand } from '../../context/CartContext';
import type { Order } from '../../services/orders';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { useOrderWebSocket } from '../../hooks/useOrderWebSocket';

import { itemCount, orderStatus, when } from '../../utils/orderDisplay';
type Tab = 'pending' | 'preparing' | 'ready' | 'delivered' | 'cancelled';

const TABS: { id: Tab; label: string }[] = [
    { id: 'pending', label: 'New' },
    { id: 'preparing', label: 'Preparing' },
    { id: 'ready', label: 'Ready' },
    { id: 'delivered', label: 'Delivered' },
    { id: 'cancelled', label: 'Cancelled' },
];
// Finished orders are loaded only when their tab is opened
const FINISHED: Tab[] = ['delivered', 'cancelled'];

// Which tab an active order belongs to. Every status maps to exactly one tab.
const tabFor = (order: Order): Tab | 'hidden' => {
    // Online payment not confirmed yet: nothing for the kitchen to do until it is paid
    const awaitingPayment = ['pending', 'failed', 'unpaid'].includes(order.payment_status ?? '');
    if (order.status === 'pending') return awaitingPayment ? 'hidden' : 'pending';
    if (['accepted', 'preparing', 'waiting_for_driver'].includes(order.status)) return 'preparing';
    if (['ready', 'picked_up'].includes(order.status)) return 'ready';
    return order.status === 'cancelled' ? 'cancelled' : 'delivered';
};

const RestaurantOrders = () => {
    const [active, setActive] = useState<Order[]>([]);
    const [finished, setFinished] = useState<Order[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<Tab>('pending');

    const fetchOrders = useCallback(async () => {
        try {
            setLoading(true);
            const showsFinished = FINISHED.includes(activeTab);
            const [current, done] = await Promise.all([
                orderService.getRestaurantOrders('active', 100),
                showsFinished ? orderService.getRestaurantOrders(activeTab as 'delivered' | 'cancelled', 50) : Promise.resolve([]),
            ]);
            setActive(current);
            setFinished(done);
        } catch {
            toast.error('Failed to fetch orders');
        } finally {
            setLoading(false);
        }
    }, [activeTab]);

    useEffect(() => {
        fetchOrders();
    }, [fetchOrders]);

    // Real-time updates
    useOrderWebSocket((message) => {
        if (message.type === 'new_order' || message.type === 'order_updated') fetchOrders();
    });

    const handleUpdateStatus = async (order: Order, newStatus: string) => {
        if (newStatus === 'cancelled') {
            const paidOnline = order.payment_status === 'completed';
            const sure = window.confirm(
                `Cancel order ${orderRef(order.id)}?` +
                (paidOnline ? `\n\nThe customer already paid ${formatRand(order.total || 0)} online. You will need to refund it from your payment account.` : '') +
                '\n\nThis cannot be undone.'
            );
            if (!sure) return;
        }
        try {
            if (newStatus === 'accepted') {
                await orderService.acceptOrder(order.id);
                toast.success('Order accepted!');
            } else {
                await orderService.updateStatus(order.id, newStatus);
                toast.success(newStatus === 'cancelled' ? 'Order cancelled' : `Order marked ${orderStatus(newStatus).label.toLowerCase()}`);
            }
            fetchOrders();
        } catch (error: any) {
            const detail = error.response?.data?.detail;
            toast.error(typeof detail === 'string' ? detail : 'Failed to update order status');
        }
    };

    const filteredOrders = FINISHED.includes(activeTab)
        ? finished
        : active.filter(order => tabFor(order) === activeTab);
    const countFor = (tab: Tab) => FINISHED.includes(tab) ? 0 : active.filter(o => tabFor(o) === tab).length;

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Order Management</h1>
                    <p className="text-gray-400 mt-1">Accept, track and manage incoming orders.</p>
                </div>
                <button
                    onClick={fetchOrders}
                    aria-label="Refresh orders"
                    className="p-2.5 bg-gray-900 border border-gray-800 text-gray-400 hover:text-white rounded-xl transition-all self-start md:self-auto"
                >
                    <RefreshCcw size={20} className={loading ? "animate-spin" : ""} />
                </button>
            </div>

            {/* Tabs */}
            <div className="flex space-x-2 bg-gray-900/50 border border-gray-800 p-1.5 rounded-2xl overflow-x-auto no-scrollbar">
                {TABS.map(({ id, label }) => (
                    <button
                        key={id}
                        onClick={() => setActiveTab(id)}
                        className={clsx(
                            "px-5 py-2.5 rounded-xl text-sm font-bold transition-all uppercase tracking-widest flex-shrink-0",
                            activeTab === id
                                ? id === 'cancelled' ? "bg-red-600 text-white shadow-lg shadow-red-600/20" : "bg-brand-600 text-white shadow-lg shadow-brand-600/20"
                                : "text-gray-500 hover:text-gray-300"
                        )}
                    >
                        {label}
                        {countFor(id) > 0 && (
                            <span className="ml-2 bg-white/20 px-1.5 rounded-md text-[10px]">{countFor(id)}</span>
                        )}
                    </button>
                ))}
            </div>

            {/* Orders List */}
            <div key={activeTab} className="grid gap-6">
                {loading && filteredOrders.length === 0 ? (
                        [1, 2].map(i => (
                            <div key={i} className="h-48 bg-gray-900/40 border border-gray-800 rounded-3xl animate-pulse"></div>
                        ))
                    ) : filteredOrders.length === 0 ? (
                        <div className="p-20 text-center bg-gray-900/40 border border-gray-800 rounded-3xl border-dashed">
                            <ShoppingBag size={48} className="text-gray-700 mx-auto mb-4" />
                            <p className="text-gray-500 font-bold">
                                {activeTab === 'cancelled' ? 'No cancelled orders.' : activeTab === 'delivered' ? 'No delivered orders yet.' : 'No orders here right now.'}
                            </p>
                        </div>
                    ) : (
                        filteredOrders.map((order) => {
                            const status = orderStatus(order.status);
                            const cancelled = order.status === 'cancelled';
                            return (
                                <div
                                    key={order.id}
                                    className={clsx(
                                        "animate-in fade-in duration-300 bg-gray-900/40 border rounded-3xl overflow-hidden transition-all group",
                                        cancelled ? "border-red-500/20" : "border-gray-800 hover:border-gray-700"
                                    )}
                                >
                                    <div className="p-6 border-b border-gray-800/50 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                        <div className="flex items-center gap-4 min-w-0">
                                            <div className={clsx(
                                                "w-12 h-12 shrink-0 rounded-2xl flex items-center justify-center",
                                                cancelled ? "bg-red-500/10 text-red-500" : "bg-brand-500/10 text-brand-500"
                                            )}>
                                                {cancelled ? <XCircle size={22} /> : <ShoppingBag size={22} />}
                                            </div>
                                            <div className="min-w-0">
                                                <div className="flex flex-wrap items-center gap-2">
                                                    <p className="text-lg font-bold text-white">
                                                        Order <span className="font-mono tracking-wide">{orderRef(order.id)}</span>
                                                    </p>
                                                    <span className={clsx("px-2 py-0.5 rounded-md border text-[10px] font-bold uppercase tracking-widest", status.style)}>
                                                        {status.label}
                                                    </span>
                                                </div>
                                                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 mt-1">
                                                    <span className="flex items-center gap-1"><Clock size={12} />{when(order.created_at)}</span>
                                                    <span className="flex items-center gap-1">
                                                        <User size={12} />
                                                        <span>{fullName(order.customer) || 'Customer'}</span>
                                                        {order.customer?.contact_number && (
                                                            <a href={phoneHref(order.customer.contact_number)} className="text-brand-500 font-bold hover:text-brand-400">
                                                                {order.customer.contact_number}
                                                            </a>
                                                        )}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <p className={clsx("text-xl font-black whitespace-nowrap", cancelled ? "text-gray-500 line-through" : "text-white")}>
                                                {formatRand(order.total || 0)}
                                            </p>
                                            {(order.status === 'pending' || ['accepted', 'preparing'].includes(order.status)) && (
                                                <div className="h-8 w-px bg-gray-800 hidden md:block"></div>
                                            )}
                                            <div className="flex items-center gap-2">
                                                {order.status === 'pending' && (
                                                    <button
                                                        onClick={() => handleUpdateStatus(order, 'accepted')}
                                                        className="px-6 py-2.5 bg-brand-600 hover:bg-brand-500 text-white font-bold rounded-xl shadow-lg shadow-brand-600/20 transition-all uppercase text-xs"
                                                    >
                                                        Accept Order
                                                    </button>
                                                )}
                                                {(order.status === 'accepted' || order.status === 'preparing') && (
                                                    <button
                                                        onClick={() => handleUpdateStatus(order, 'ready')}
                                                        className="px-6 py-2.5 bg-green-500 hover:bg-green-400 text-black font-bold rounded-xl shadow-lg shadow-green-500/20 transition-all uppercase text-xs"
                                                    >
                                                        Mark as Ready
                                                    </button>
                                                )}
                                                {order.status === 'pending' && (
                                                    <button
                                                        onClick={() => handleUpdateStatus(order, 'cancelled')}
                                                        aria-label="Cancel order"
                                                        title="Cancel order"
                                                        className="p-2.5 bg-gray-800 hover:bg-red-500/10 text-gray-400 hover:text-red-500 rounded-xl transition-all"
                                                    >
                                                        <XCircle size={20} />
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {order.refund_due && (
                                        <div className="px-6 py-3 bg-red-500/10 border-b border-red-500/20 flex items-start gap-2 text-sm text-red-500">
                                            <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                                            <span>
                                                <strong>Refund needed.</strong> The customer paid online. Refund {formatRand(order.total || 0)} from
                                                your payment account (PayFast, Ozow or Peach) and keep order {orderRef(order.id)} as the reference.
                                            </span>
                                        </div>
                                    )}

                                    {/* Order Items Summary */}
                                    <div className="p-6 bg-gray-950/20">
                                        <div className="flex items-center justify-between mb-4">
                                            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest">Ordered Items</h4>
                                            <span className="text-xs text-gray-600">{itemCount(order.items?.length)}</span>
                                        </div>
                                        <div className="space-y-2">
                                            {order.items && order.items.length > 0 ? (
                                                order.items.map((item: any, idx) => (
                                                    <div key={idx} className="flex justify-between items-center py-1">
                                                        <span className="text-sm text-gray-300"><span className="text-brand-500 font-bold mr-2">{item.quantity}x</span> {item.name || 'Menu Item'}</span>
                                                        <span className="text-sm font-bold text-white">{formatRand(Number(item.price) * item.quantity)}</span>
                                                    </div>
                                                ))
                                            ) : (
                                                <p className="text-sm text-gray-600 italic">No item details available.</p>
                                            )}
                                        </div>

                                        {!cancelled && (
                                            <div className="mt-4">
                                                <InvoiceButton path={`/manage/orders/${order.id}/invoice.pdf`} fallbackName={`invoice-${order.id.slice(0, 8).toUpperCase()}.pdf`} label="Download invoice" />
                                            </div>
                                        )}

                                        {order.delivery_address && (
                                            <p className="mt-4 text-xs text-gray-400">
                                                <span className="text-gray-500 font-bold uppercase tracking-widest">Deliver to: </span>
                                                {order.delivery_address}
                                            </p>
                                        )}

                                        {order.driver_id ? (
                                            <div className="mt-6 pt-4 border-t border-gray-800/50 flex flex-wrap items-center justify-between gap-2 text-xs">
                                                <div className="flex items-center space-x-2 text-gray-400">
                                                    <Truck size={14} className="text-brand-500" />
                                                    <span>Driver: </span>
                                                    <span className="text-white font-bold">{fullName(order.driver) || 'Assigned'}</span>
                                                    {order.driver?.vehicle_type && <span className="text-gray-500">({order.driver.vehicle_type})</span>}
                                                </div>
                                                {order.driver?.contact_number && !cancelled && (
                                                    <a href={phoneHref(order.driver.contact_number)} className="text-brand-500 font-bold bg-brand-500/10 hover:bg-brand-500/20 px-3 py-1.5 rounded">
                                                        Call {order.driver.contact_number}
                                                    </a>
                                                )}
                                            </div>
                                        ) : ['waiting_for_driver', 'accepted', 'preparing', 'ready'].includes(order.status) && (
                                            <p className="mt-6 pt-4 border-t border-gray-800/50 text-xs text-yellow-500 font-bold">
                                                No driver yet. The order is given to your next driver who goes online.
                                            </p>
                                        )}
                                    </div>
                                </div>
                            );
                        })
                    )}
            </div>
        </div>
    );
};

export default RestaurantOrders;
