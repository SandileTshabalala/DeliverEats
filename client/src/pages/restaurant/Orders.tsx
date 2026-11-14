import { useState, useEffect, useCallback } from 'react';
import { InvoiceButton } from '../../components/ReportControls';
import {
    ShoppingBag,
    Clock,
    XCircle,
    User,
    Truck,
    RefreshCcw,
} from 'lucide-react';
import { orderService, orderRef, fullName, phoneHref } from '../../services/orders';
import { formatRand } from '../../context/CartContext';
import type { Order } from '../../services/orders';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import { useOrderWebSocket } from '../../hooks/useOrderWebSocket';

const RestaurantOrders = () => {
    const [orders, setOrders] = useState<Order[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'pending' | 'preparing' | 'ready' | 'history'>('pending');

    const fetchOrders = useCallback(async () => {
        try {
            setLoading(true);
            const data = await orderService.getRestaurantOrders();
            setOrders(data);
        } catch (error) {
            toast.error('Failed to fetch orders');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchOrders();
    }, [fetchOrders]);

    // WebSocket integration for real-time updates
    useOrderWebSocket((message) => {
        console.log('WebSocket message received:', message);

        if (message.type === 'new_order' || message.type === 'order_updated') {
            // Refresh orders when we receive an update
            fetchOrders();
        }
    });

    const handleUpdateStatus = async (orderId: string, newStatus: string) => {
        try {
            if (newStatus === 'accepted') {
                await orderService.acceptOrder(orderId);
                toast.success('Order accepted!');
            } else {
                await orderService.updateStatus(orderId, newStatus);
                toast.success(`Order status updated to ${newStatus}`);
            }
            fetchOrders();
        } catch (error: any) {
            const detail = error.response?.data?.detail;
            toast.error(typeof detail === 'string' ? detail : 'Failed to update order status');
        }
    };

    // Which tab an order belongs to. Every status maps to exactly one tab: orders
    // waiting for a driver or out for delivery used to match no tab and vanished.
    const tabFor = (order: any): 'pending' | 'preparing' | 'ready' | 'history' | 'hidden' => {
        // Online payment not confirmed yet: nothing for the kitchen to do until it is paid
        const awaitingPayment = ['pending', 'failed', 'unpaid'].includes(order.payment_status);
        if (order.status === 'pending') return awaitingPayment ? 'hidden' : 'pending';
        if (['accepted', 'preparing', 'waiting_for_driver'].includes(order.status)) return 'preparing';
        if (['ready', 'picked_up'].includes(order.status)) return 'ready';
        return 'history';
    };

    const filteredOrders = orders.filter(order => tabFor(order) === activeTab);

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Order Management</h1>
                    <p className="text-gray-400 mt-1">Accept, track and manage incoming orders.</p>
                </div>
                <button
                    onClick={fetchOrders}
                    className="p-2.5 bg-gray-900 border border-gray-800 text-gray-400 hover:text-white rounded-xl transition-all"
                >
                    <RefreshCcw size={20} className={loading ? "animate-spin" : ""} />
                </button>
            </div>

            {/* Tabs */}
            <div className="flex space-x-2 bg-gray-900/50 border border-gray-800 p-1.5 rounded-2xl overflow-x-auto no-scrollbar">
                {(['pending', 'preparing', 'ready', 'history'] as const).map((tab) => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={clsx(
                            "px-6 py-2.5 rounded-xl text-sm font-bold transition-all uppercase tracking-widest flex-shrink-0",
                            activeTab === tab
                                ? "bg-brand-600 text-white shadow-lg shadow-brand-600/20"
                                : "text-gray-500 hover:text-gray-300"
                        )}
                    >
                        {tab}
                        {orders.filter(o => tab !== 'history' && tabFor(o) === tab).length > 0 && (
                                <span className="ml-2 bg-white/20 px-1.5 rounded-md text-[10px]">
                                    {orders.filter(o => tab !== 'history' && tabFor(o) === tab).length}
                                </span>
                            )}
                    </button>
                ))}
            </div>

            {/* Orders List */}
            <div className="grid gap-6">
                <AnimatePresence mode="popLayout">
                    {loading ? (
                        [1, 2].map(i => (
                            <div key={i} className="h-48 bg-gray-900/40 border border-gray-800 rounded-3xl animate-pulse"></div>
                        ))
                    ) : filteredOrders.length === 0 ? (
                        <div className="p-20 text-center bg-gray-900/40 border border-gray-800 rounded-3xl border-dashed">
                            <ShoppingBag size={48} className="text-gray-700 mx-auto mb-4" />
                            <p className="text-gray-500 font-bold">No orders found in this category.</p>
                        </div>
                    ) : (
                        filteredOrders.map((order) => (
                            <motion.div
                                layout
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                key={order.id}
                                className="bg-gray-900/40 border border-gray-800 rounded-3xl overflow-hidden hover:border-gray-700 transition-all group"
                            >
                                <div className="p-6 border-b border-gray-800/50 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                    <div className="flex items-center space-x-4">
                                        <div className="w-12 h-12 bg-brand-500/10 rounded-2xl flex items-center justify-center text-brand-500 font-black text-lg">
                                            {orderRef(order.id)}
                                        </div>
                                        <div>
                                            <p className="text-lg font-bold text-white">Order Details</p>
                                            <div className="flex items-center space-x-3 text-xs text-gray-500 mt-0.5">
                                                <div className="flex items-center space-x-1">
                                                    <Clock size={12} />
                                                    <span>{new Date(order.created_at).toLocaleTimeString()}</span>
                                                </div>
                                                <span>•</span>
                                                <div className="flex items-center space-x-1">
                                                    <User size={12} />
                                                    <span>{fullName(order.customer) || 'Customer'}</span>
                                                    {order.customer?.contact_number && (
                                                        <a href={phoneHref(order.customer.contact_number)} className="text-brand-500 font-bold hover:text-brand-400">
                                                            {order.customer.contact_number}
                                                        </a>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-4">
                                        <div className="text-right">
                                            <p className="text-xl font-black text-white">{formatRand(order.total || 0)}</p>
                                            <p className="text-[10px] text-gray-500 uppercase font-bold tracking-widest">{order.status}</p>
                                        </div>
                                        <div className="h-8 w-px bg-gray-800 hidden md:block"></div>
                                        <div className="flex items-center space-x-2">
                                            {order.status === 'pending' && (
                                                <button
                                                    onClick={() => handleUpdateStatus(order.id, 'accepted')}
                                                    className="px-6 py-2.5 bg-brand-600 hover:bg-brand-500 text-white font-bold rounded-xl shadow-lg shadow-brand-600/20 transition-all uppercase text-xs"
                                                >
                                                    Accept Order
                                                </button>
                                            )}
                                            {(order.status === 'accepted' || order.status === 'preparing') && (
                                                <button
                                                    onClick={() => handleUpdateStatus(order.id, 'ready')}
                                                    className="px-6 py-2.5 bg-green-500 hover:bg-green-400 text-black font-bold rounded-xl shadow-lg shadow-green-500/20 transition-all uppercase text-xs"
                                                >
                                                    Mark as Ready
                                                </button>
                                            )}
                                            {order.status === 'pending' && (
                                                <button
                                                    onClick={() => handleUpdateStatus(order.id, 'cancelled')}
                                                    className="p-2.5 bg-gray-800 hover:bg-red-500/10 text-gray-400 hover:text-red-500 rounded-xl transition-all"
                                                >
                                                    <XCircle size={20} />
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Order Items Summary */}
                                <div className="p-6 bg-gray-950/20">
                                    <div className="flex items-center justify-between mb-4">
                                        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest">Ordered Items</h4>
                                        <span className="text-xs text-gray-600">{order.items?.length || 0} items</span>
                                    </div>
                                    <div className="space-y-2">
                                        {/* Since items might be generic in the schema for now, we render a placeholder if they're empty or missing properties */}
                                        {order.items && order.items.length > 0 ? (
                                            order.items.map((item: any, idx) => (
                                                <div key={idx} className="flex justify-between items-center py-1">
                                                    <span className="text-sm text-gray-300"><span className="text-brand-500 font-bold mr-2">{item.quantity}x</span> {item.name || 'Menu Item'}</span>
                                                    <span className="text-sm font-bold text-white">{formatRand(Number(item.price) * item.quantity)}</span>
                                                </div>
                                            ))
                                        ) : (
                                            <p className="text-sm text-gray-600 italic">No item details available in simple view.</p>
                                        )}
                                    </div>

                                    <div className="mt-4">
                                        <InvoiceButton path={`/manage/orders/${order.id}/invoice.pdf`} fallbackName={`invoice-${order.id.slice(0, 8).toUpperCase()}.pdf`} label="Download invoice" />
                                    </div>

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
                                            {order.driver?.contact_number && (
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
                            </motion.div>
                        ))
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default RestaurantOrders;
