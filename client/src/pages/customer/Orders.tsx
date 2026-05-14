import { useState, useEffect, useCallback } from 'react';
import {
    Clock,
    CheckCircle2,
    Truck,
    ShoppingBag,
    ArrowRight,
    ChevronDown,
    MapPin,
    AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import { toast } from 'react-hot-toast';
import { useOrderWebSocket } from '../../hooks/useOrderWebSocket';

interface OrderItem {
    id: string;
    description: string | null;
    quantity: number;
    price: number;
    name: string;
}

interface Order {
    id: string;
    restaurant_id: string;
    customer_id: string;
    status: string;
    total_amount: number;
    created_at: string;
    items: OrderItem[];
    // restaurant: { name: string }; // Assuming backend expands restaurant relation
}

const Orders = () => {
    const [activeFilter, setActiveFilter] = useState('All');
    const [expandedOrder, setExpandedOrder] = useState<string | null>(null);
    const [orders, setOrders] = useState<Order[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchOrders = useCallback(async () => {
        try {
            const response = await api.get('/orders/my');
            setOrders(response.data);
        } catch (error) {
            console.error('Failed to fetch orders:', error);
            toast.error('Could not load your orders');
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

    const getStatusStyles = (status: string) => {
        const s = status.toLowerCase();
        switch (s) {
            case 'preparing': return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
            case 'delivered':
            case 'completed': return 'bg-green-500/10 text-green-500 border-green-500/20';
            case 'cancelled': return 'bg-red-500/10 text-red-500 border-red-500/20';
            case 'pending': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
            case 'ready':
            case 'picked_up': return 'bg-purple-500/10 text-purple-500 border-purple-500/20';
            default: return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
        }
    };

    const getStatusIcon = (status: string) => {
        const s = status.toLowerCase();
        switch (s) {
            case 'preparing': return <Clock size={14} />;
            case 'delivered':
            case 'completed': return <CheckCircle2 size={14} />;
            case 'cancelled': return <AlertCircle size={14} />;
            case 'pending': return <Clock size={14} />;
            default: return <Truck size={14} />;
        }
    };

    const filteredOrders = orders.filter(order => {
        if (activeFilter === 'All') return true;
        return order.status.toLowerCase() === activeFilter.toLowerCase();
    });

    if (loading) {
        return (
            <div className="max-w-5xl mx-auto space-y-6 pt-20 animate-pulse">
                {[1, 2, 3].map(i => (
                    <div key={i} className="h-32 bg-gray-900 rounded-[32px] border border-gray-800"></div>
                ))}
            </div>
        );
    }

    return (
        <div className="max-w-5xl mx-auto space-y-12 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                    <h1 className="text-4xl font-black uppercase tracking-tighter italic">Your Journey</h1>
                    <p className="text-gray-500 font-medium">Track your current cravings and past delights.</p>
                </div>

                <div className="flex items-center space-x-2 bg-gray-900 border border-gray-800 rounded-2xl p-1.5 overflow-x-auto no-scrollbar">
                    {['All', 'Pending', 'Preparing', 'Delivered', 'Cancelled'].map(filter => (
                        <button
                            key={filter}
                            onClick={() => setActiveFilter(filter)}
                            className={clsx(
                                "px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all whitespace-nowrap",
                                activeFilter === filter
                                    ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                                    : "text-gray-500 hover:text-white"
                            )}
                        >
                            {filter}
                        </button>
                    ))}
                </div>
            </div>

            {/* Orders List */}
            <div className="space-y-6">
                {filteredOrders.length === 0 ? (
                    <div className="text-center py-20 bg-gray-900/50 rounded-[40px] border border-gray-800 border-dashed">
                        <ShoppingBag size={48} className="mx-auto text-gray-700 mb-4" />
                        <p className="text-gray-500 font-black uppercase tracking-widest">No orders found</p>
                    </div>
                ) : (
                    filteredOrders.map((order, index) => (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            key={order.id}
                            className="bg-gray-900/50 border border-gray-800 rounded-[32px] overflow-hidden hover:border-blue-500/30 transition-all group"
                        >
                            <div
                                className="p-6 md:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 cursor-pointer"
                                onClick={() => setExpandedOrder(expandedOrder === order.id ? null : order.id)}
                            >
                                <div className="flex items-center space-x-6">
                                    <div className={clsx(
                                        "w-16 h-16 rounded-2xl flex items-center justify-center border transition-colors group-hover:scale-110",
                                        getStatusStyles(order.status)
                                    )}>
                                        <ShoppingBag size={28} />
                                    </div>
                                    <div className="space-y-1">
                                        <div className="flex items-center space-x-3">
                                            <h3 className="text-xl font-black uppercase tracking-tight italic group-hover:text-blue-500 transition-colors">
                                                Order #{order.id?.slice(0, 8) || 'N/A'}
                                            </h3>
                                            <span className={clsx(
                                                "px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border flex items-center space-x-2",
                                                getStatusStyles(order.status)
                                            )}>
                                                {getStatusIcon(order.status)}
                                                <span>{order.status}</span>
                                            </span>
                                        </div>
                                        <div className="flex items-center space-x-4 text-gray-500 text-sm font-bold">
                                            <span>{order.items.length} Items</span>
                                            <span className="w-1 h-1 rounded-full bg-gray-800 font-normal">•</span>
                                            <span className="font-normal">{new Date(order.created_at || Date.now()).toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between md:justify-end md:space-x-8">
                                    <div className="text-right">
                                        <p className="text-xs font-black text-gray-500 uppercase tracking-widest mb-1">Total</p>
                                        <p className="text-2xl font-black text-white italic">R {Number(order.total_amount).toFixed(2)}</p>
                                    </div>
                                    <div className={clsx(
                                        "p-3 rounded-xl bg-gray-950 border border-gray-800 text-gray-400 group-hover:text-white transition-all",
                                        expandedOrder === order.id && "rotate-180 text-blue-500 border-blue-500/20"
                                    )}>
                                        <ChevronDown size={20} />
                                    </div>
                                </div>
                            </div>

                            <AnimatePresence>
                                {expandedOrder === order.id && (
                                    <motion.div
                                        initial={{ height: 0 }}
                                        animate={{ height: 'auto' }}
                                        exit={{ height: 0 }}
                                        className="overflow-hidden border-t border-gray-800"
                                    >
                                        <div className="p-8 bg-gray-950/50 space-y-8">
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                                                {/* Order Details */}
                                                <div className="space-y-4">
                                                    <h4 className="text-xs font-black text-gray-500 uppercase tracking-widest">Selected Items</h4>
                                                    <ul className="space-y-3">
                                                        {order.items.map((item, i) => (
                                                            <li key={i} className="flex items-center justify-between p-4 bg-gray-900 border border-gray-800 rounded-2xl">
                                                                <div className="flex items-center space-x-3">
                                                                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                                                    <span className="font-bold text-sm text-gray-300 uppercase italic tracking-tight">{item.name}</span>
                                                                </div>
                                                                <div className="text-right">
                                                                    <span className="text-xs font-black text-white block">x{item.quantity}</span>
                                                                    <span className="text-[10px] text-gray-500 font-bold">R {item.price}</span>
                                                                </div>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>

                                                {/* Tracking UI (Simplified for now) */}
                                                <div className="space-y-6">
                                                    <h4 className="text-xs font-black text-gray-500 uppercase tracking-widest">Status Updates</h4>
                                                    <div className="relative pl-8 space-y-12">
                                                        <div className="absolute left-1.5 top-0 bottom-0 w-0.5 bg-gray-800"></div>

                                                        <div className="relative flex items-start space-x-4">
                                                            <div className="absolute -left-[30px] p-1.5 bg-green-500 text-black rounded-full shadow-lg shadow-green-500/20"><CheckCircle2 size={12} /></div>
                                                            <div>
                                                                <p className="font-black uppercase italic text-sm text-white">Order Placed</p>
                                                                <p className="text-xs text-gray-500 font-medium">We've received your order.</p>
                                                            </div>
                                                        </div>

                                                        {['preparing', 'ready', 'picked_up', 'delivered'].includes(order.status.toLowerCase()) && (
                                                            <div className="relative flex items-start space-x-4">
                                                                <div className="absolute -left-[30px] p-1.5 bg-blue-500 text-white rounded-full shadow-lg shadow-blue-500/20"><Clock size={12} /></div>
                                                                <div>
                                                                    <p className="font-black uppercase italic text-sm text-white">Processing</p>
                                                                    <p className="text-xs text-gray-500 font-medium">The kitchen is working on it.</p>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="flex flex-col sm:flex-row gap-4 pt-6 border-t border-gray-800">
                                                <button className="flex-1 py-4 bg-gray-900 hover:bg-gray-800 text-white font-black uppercase tracking-widest text-xs rounded-2xl transition-all border border-gray-800">
                                                    Close Details
                                                </button>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </motion.div>
                    )))}
            </div>

            {/* Empty State Link */}
            <div className="pt-12 text-center">
                <p className="text-gray-600 font-bold mb-6 italic italic uppercase tracking-widest">Hungry for more?</p>
                <Link
                    to="/customer"
                    className="inline-flex items-center space-x-4 px-10 py-5 bg-gray-900 border border-gray-800 rounded-3xl hover:border-blue-500 transition-all group"
                >
                    <div className="w-12 h-12 bg-blue-600 rounded-2xl flex items-center justify-center group-hover:rotate-12 transition-transform shadow-xl shadow-blue-600/20 text-white">
                        <ShoppingBag size={24} />
                    </div>
                    <div className="text-left">
                        <p className="text-xs font-black uppercase tracking-widest text-gray-500 mb-1">Explore</p>
                        <div className="flex items-center space-x-2">
                            <span className="text-xl font-black text-white italic uppercase tracking-tighter">New Restaurants</span>
                            <ArrowRight size={20} className="text-blue-500" />
                        </div>
                    </div>
                </Link>
            </div>
        </div>
    );
};

export default Orders;
