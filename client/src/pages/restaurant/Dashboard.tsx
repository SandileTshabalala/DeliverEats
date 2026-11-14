import { useState, useEffect } from 'react';
import { formatClock } from '../../utils/clock';
import { Link } from 'react-router-dom';
import type { RestaurantProfile, RestaurantReviews } from '../../services/platform';
import { RatingBadge, Stars } from '../../components/Stars';
import { timeAgo } from '../../services/site';
import {
    ShoppingBag,
    TrendingUp,
    Star,
    Clock,
    ArrowUpRight,
    UtensilsCrossed,
} from 'lucide-react';
import { orderService, orderRef, fullName } from '../../services/orders';
import { platform } from '../../services/platform';
import type { RestaurantStats } from '../../services/platform';
import { formatRand } from '../../context/CartContext';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';

import { orderStatus, when } from '../../utils/orderDisplay';
const RestaurantDashboard = () => {
    const [orders, setOrders] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [numbers, setNumbers] = useState<RestaurantStats | null>(null);

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        try {
            setLoading(true);
            const [ordersData, statsData] = await Promise.all([orderService.getRestaurantOrders(), platform.restaurantStats()]);
            setOrders(ordersData);
            setNumbers(statsData);
        } catch (error) {
            toast.error('Failed to load restaurant data');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
            </div>
        );
    }

    const stats = [
        { label: 'Orders today', value: String(numbers?.orders_today ?? 0), icon: ShoppingBag, color: 'text-brand-500', bg: 'bg-brand-500/10' },
        { label: 'Sales today', value: formatRand(numbers?.sales_today ?? 0), icon: TrendingUp, color: 'text-green-500', bg: 'bg-green-500/10' },
        { label: 'Sales this month', value: formatRand(numbers?.sales_this_month ?? 0), icon: Star, color: 'text-green-500', bg: 'bg-green-500/10' },
        { label: 'Items on the menu', value: String(numbers?.menu_items_available ?? 0), icon: UtensilsCrossed, color: 'text-brand-500', bg: 'bg-brand-500/10' },
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
                    <div className="px-4 py-2 bg-brand-500 text-white font-bold rounded-xl text-sm transition-all shadow-lg shadow-brand-500/20">
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
                            <Clock size={20} className="text-brand-500" />
                            <span>Recent Orders</span>
                        </h3>
                        <Link to="/restaurant/orders" className="text-xs font-bold text-brand-400 hover:text-brand-300 transition-colors uppercase tracking-widest">See all orders</Link>
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
                                        <div className="min-w-0">
                                            <p className="text-sm font-bold text-white truncate">
                                                {fullName(order.customer) || 'Customer'} <span className="font-mono text-xs text-brand-500">{orderRef(order.id)}</span>
                                            </p>
                                            <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">{when(order.created_at)}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-6">
                                        <div className="text-right">
                                            <p className="text-sm font-bold text-white whitespace-nowrap">{formatRand(order.total || 0)}</p>
                                            <span className={clsx(
                                                "text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full border",
                                                orderStatus(order.status).style
                                            )}>
                                                {orderStatus(order.status).label}
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
                    <div className="p-6 bg-gradient-to-br from-brand-600 to-brand-700 rounded-3xl shadow-xl shadow-brand-500/10">
                        <h4 className="text-lg font-bold text-white mb-2">Kitchen Health</h4>
                        <p className="text-brand-100/70 text-sm leading-relaxed mb-4">You have {pendingOrders.length} pending orders that need action.</p>
                        <Link to="/restaurant/orders" className="block text-center w-full py-3 bg-white text-brand-600 font-black rounded-2xl text-sm transition-transform active:scale-95 shadow-lg uppercase tracking-wider">
                            Manage Current Orders
                        </Link>
                    </div>

                    <KitchenCard />
                </div>
            </div>
        </div>
    );
};

export default RestaurantDashboard;


/** Open / close the kitchen and see what customers said. Staff can use the switch too. */
const KitchenCard = () => {
    const [profile, setProfile] = useState<RestaurantProfile | null>(null);
    const [reviews, setReviews] = useState<RestaurantReviews | null>(null);
    const [switching, setSwitching] = useState(false);

    useEffect(() => {
        platform.profile().then(setProfile).catch(() => undefined);
        platform.restaurantReviews().then(setReviews).catch(() => undefined);
    }, []);

    const toggle = async () => {
        if (!profile) return;
        setSwitching(true);
        try {
            const updated = await platform.updateProfile({ accepting_orders: !profile.accepting_orders });
            setProfile(updated);
            toast.success(updated.accepting_orders ? 'Kitchen open: customers can order' : 'Kitchen closed: new orders are paused');
        } catch {
            toast.error('Could not change the kitchen status');
        } finally {
            setSwitching(false);
        }
    };

    return (
        <div className="p-6 bg-gray-900/40 border border-gray-800 rounded-3xl space-y-5">
            <div className="space-y-3">
                <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest">Kitchen</h4>
                {profile ? (
                    <>
                        <p className={profile.is_open ? "text-green-500 font-bold" : "text-red-400 font-bold"}>
                            {profile.is_open
                                ? 'Open: customers can order'
                                : profile.accepting_orders && profile.opens_at
                                    ? `Closed until ${formatClock(profile.opens_at)} (opening hours)`
                                    : 'Closed: new orders are paused'}
                        </p>
                        <button
                            onClick={toggle}
                            disabled={switching}
                            className={profile.accepting_orders
                                ? "w-full py-3 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-2xl text-sm disabled:opacity-60"
                                : "w-full py-3 bg-green-500 hover:bg-green-600 text-black font-bold rounded-2xl text-sm disabled:opacity-60"}
                        >
                            {switching ? 'Saving...' : profile.accepting_orders ? 'Close the kitchen for now' : 'Open the kitchen'}
                        </button>
                    </>
                ) : <p className="text-sm text-gray-500">Loading...</p>}
            </div>

            <div className="space-y-3 border-t border-gray-800 pt-5">
                <div className="flex items-center justify-between">
                    <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest">Reviews</h4>
                    {reviews && <RatingBadge rating={reviews.rating} count={reviews.review_count} />}
                </div>
                {reviews && reviews.reviews.length === 0 && <p className="text-sm text-gray-500">No reviews yet. Customers can rate an order once it is delivered.</p>}
                <ul className="space-y-3">
                    {reviews?.reviews.slice(0, 5).map(review => (
                        <li key={review.id} className="space-y-1">
                            <div className="flex items-center justify-between">
                                <Stars value={review.rating} size={14} />
                                <span className="text-[11px] text-gray-500">{review.customer_name} · {timeAgo(review.created_at)}</span>
                            </div>
                            {review.comment && <p className="text-sm text-gray-300">{review.comment}</p>}
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
};
