import { useState, useEffect } from 'react';
import {
    ShoppingBag,
    TrendingUp,
    Star,
    Clock,
    ArrowUpRight,
    UtensilsCrossed,
    CheckCircle2
} from 'lucide-react';
import { orderService } from '../../services/orders';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';

const RestaurantDashboard = () => {
    const [orders, setOrders] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        try {
            setLoading(true);
            const ordersData = await orderService.getRestaurantOrders();
            setOrders(ordersData);
        } catch (error) {
            toast.error('Failed to load restaurant data');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
        );
    }

    const stats = [
        { label: 'Total Orders', value: orders.length.toString(), icon: ShoppingBag, color: 'text-blue-500', bg: 'bg-blue-500/10' },
        { label: 'Revenue', value: 'R 8,240', icon: TrendingUp, color: 'text-green-500', bg: 'bg-green-500/10' },
        { label: 'Active Menus', value: '14', icon: UtensilsCrossed, color: 'text-gold-500', bg: 'bg-gold-500/10' },
        { label: 'Rating', value: '4.8', icon: Star, color: 'text-orange-500', bg: 'bg-orange-500/10' },
    ];

    const pendingOrders = orders.filter(o => o.status === 'pending');

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-4xl font-black text-white tracking-tighter">Kitchen Overview</h1>
                    <p className="text-gray-400 mt-1">Real-time status of your restaurant operations.</p>
                </div>
                <div className="flex items-center space-x-2 bg-gray-900 border border-gray-800 rounded-2xl p-1">
                    <div className="px-4 py-2 bg-blue-500 text-white font-bold rounded-xl text-sm transition-all shadow-lg shadow-blue-500/20">
                        Live Monitor
                    </div>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {stats.map((stat, i) => (
                    <motion.div
                        key={stat.label}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: i * 0.1 }}
                        className="p-6 bg-gray-900/40 backdrop-blur-xl border border-gray-800 rounded-3xl hover:border-gray-700 transition-all group"
                    >
                        <div className={clsx("w-12 h-12 rounded-2xl flex items-center justify-center mb-4 transition-transform group-hover:rotate-12", stat.bg, stat.color)}>
                            <stat.icon size={24} />
                        </div>
                        <p className="text-xs font-bold text-gray-500 uppercase tracking-widest">{stat.label}</p>
                        <p className="text-3xl font-bold text-white mt-1">{stat.value}</p>
                    </motion.div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Recent Orders */}
                <div className="lg:col-span-2 space-y-4">
                    <div className="flex items-center justify-between">
                        <h3 className="text-xl font-bold text-white flex items-center space-x-2">
                            <Clock size={20} className="text-blue-500" />
                            <span>Recent Orders</span>
                        </h3>
                        <button className="text-xs font-bold text-blue-400 hover:text-blue-300 transition-colors uppercase tracking-widest">See all orders</button>
                    </div>

                    {orders.length === 0 ? (
                        <div className="p-12 text-center bg-gray-900/40 border border-gray-800 rounded-3xl border-dashed">
                            <p className="text-gray-500 font-medium">No orders received yet.</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {orders.slice(0, 5).map((order) => (
                                <div key={order.id} className="p-4 bg-gray-900/40 hover:bg-gray-800/40 border border-gray-800 rounded-2xl flex items-center justify-between transition-all group">
                                    <div className="flex items-center space-x-4">
                                        <div className="w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500 font-bold text-sm">
                                            #{order.id.slice(-4)}
                                        </div>
                                        <div>
                                            <p className="text-sm font-bold text-white">Order from Customer</p>
                                            <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">{new Date(order.created_at).toLocaleTimeString()}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-6">
                                        <div className="text-right">
                                            <p className="text-sm font-bold text-white">R {order.total}</p>
                                            <span className={clsx(
                                                "text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full",
                                                order.status === 'pending' ? "bg-amber-500/10 text-amber-500" : "bg-green-500/10 text-green-500"
                                            )}>
                                                {order.status}
                                            </span>
                                        </div>
                                        <ArrowUpRight size={18} className="text-gray-600 group-hover:text-white transition-colors" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Quick Actions / Insights */}
                <div className="space-y-6">
                    <div className="p-6 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-3xl shadow-xl shadow-blue-500/10">
                        <h4 className="text-lg font-bold text-white mb-2">Kitchen Health</h4>
                        <p className="text-blue-100/70 text-sm leading-relaxed mb-4">You have {pendingOrders.length} pending orders that need action.</p>
                        <button className="w-full py-3 bg-white text-blue-600 font-black rounded-2xl text-sm transition-transform active:scale-95 shadow-lg uppercase tracking-wider">
                            Manage Current Orders
                        </button>
                    </div>

                    <div className="p-6 bg-gray-900/40 border border-gray-800 rounded-3xl space-y-4">
                        <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest">Platform Status</h4>
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-300">Visibility</span>
                                <span className="flex items-center text-green-500 text-xs font-bold">
                                    <CheckCircle2 size={12} className="mr-1" /> Public
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-300">New Reviews</span>
                                <span className="text-xs font-bold text-blue-400">+5 Today</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default RestaurantDashboard;
