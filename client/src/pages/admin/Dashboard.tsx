import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Store, Users, ShoppingBag, Wallet, ArrowRight } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { formatRand } from '../../context/CartContext';
import { errorMessage, STATUS_LABEL, STATUS_STYLE } from '../../services/billing';
import type { SubscriptionStatus } from '../../services/billing';
import { platform } from '../../services/platform';
import type { AdminStats } from '../../services/platform';

const card = "bg-gray-900 border border-gray-800 rounded-2xl p-6";

const STATUS_ORDER: SubscriptionStatus[] = ['active', 'trialing', 'past_due', 'expired', 'suspended', 'cancelled', 'none'];

const Dashboard = () => {
    const [stats, setStats] = useState<AdminStats | null>(null);
    const [failed, setFailed] = useState(false);

    useEffect(() => {
        platform.adminStats()
            .then(setStats)
            .catch(error => {
                setFailed(true);
                toast.error(errorMessage(error, 'Could not load the dashboard'));
            });
    }, []);

    if (failed) return <div className="p-8 text-gray-500">The dashboard could not be loaded. Refresh to try again.</div>;
    if (!stats) return <div className="p-8 text-gray-500">Loading dashboard...</div>;

    const tiles = [
        { label: 'Subscription income this month', value: formatRand(stats.subscription_income.this_month), hint: `${formatRand(stats.subscription_income.monthly_recurring)} a month from active plans`, icon: Wallet },
        { label: 'Restaurants open', value: `${stats.restaurants.live} of ${stats.restaurants.total}`, hint: 'Visible to customers right now', icon: Store },
        { label: 'Orders today', value: String(stats.orders.today), hint: `${stats.orders.this_month} this month, ${stats.orders.all_time} in total`, icon: ShoppingBag },
        { label: 'Customers', value: String(stats.customers), hint: `${stats.drivers} drivers across all restaurants`, icon: Users },
    ];

    const days = stats.orders.last_7_days;
    const busiest = Math.max(1, ...days.map(day => day.orders));
    const weekTotal = days.reduce((sum, day) => sum + day.orders, 0);
    const weekday = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-ZA', { weekday: 'short' });

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">Overview</h1>
                <p className="text-gray-400 mt-1">How the platform is doing. Order money belongs to the restaurants; your income is subscriptions.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
                {tiles.map(tile => (
                    <div key={tile.label} className={card}>
                        <div className="flex items-center justify-between">
                            <p className="text-sm font-medium text-gray-500">{tile.label}</p>
                            <tile.icon size={20} className="text-brand-500" />
                        </div>
                        <p className="text-3xl font-bold text-white mt-3">{tile.value}</p>
                        <p className="text-xs text-gray-500 mt-2">{tile.hint}</p>
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Orders per day: one bar per day, value on top, no decoration */}
                <section className={clsx(card, "lg:col-span-2")} aria-label="Orders in the last 7 days">
                    <div className="flex items-baseline justify-between mb-6">
                        <h2 className="text-lg font-bold text-white">Orders, last 7 days</h2>
                        <p className="text-sm text-gray-500">{weekTotal} in total</p>
                    </div>
                    {weekTotal === 0 ? (
                        <p className="text-gray-500 text-sm py-12 text-center">No orders in the last 7 days.</p>
                    ) : (
                        <div className="h-56 flex items-end gap-3">
                            {days.map(day => (
                                <div key={day.date} className="flex-1 h-full flex flex-col items-center justify-end gap-2" title={`${day.date}: ${day.orders} orders`}>
                                    <span className="text-xs font-bold text-gray-300">{day.orders}</span>
                                    <div
                                        className="w-full bg-brand-500 rounded-t-md min-h-[2px]"
                                        style={{ height: `${(day.orders / busiest) * 80}%` }}
                                    />
                                    <span className="text-[11px] font-bold text-gray-500">{weekday(day.date)}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </section>

                <section className={card}>
                    <h2 className="text-lg font-bold text-white mb-4">Subscriptions</h2>
                    <ul className="space-y-3">
                        {STATUS_ORDER.filter(status => (stats.subscriptions[status] ?? 0) > 0).map(status => (
                            <li key={status} className="flex items-center justify-between">
                                <span className={clsx("px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border", STATUS_STYLE[status])}>
                                    {STATUS_LABEL[status]}
                                </span>
                                <span className="text-white font-bold">{stats.subscriptions[status]}</span>
                            </li>
                        ))}
                        {stats.restaurants.total === 0 && <li className="text-sm text-gray-500">No restaurants yet.</li>}
                    </ul>
                    {!stats.subscriptions_enforced && (
                        <p className="text-xs text-yellow-500 mt-4">Subscriptions are not enforced yet: unpaid restaurants stay open.</p>
                    )}
                    <Link to="/admin/billing" className="mt-5 inline-flex items-center space-x-2 text-sm font-bold text-brand-500 hover:text-brand-400">
                        <span>Manage subscriptions</span><ArrowRight size={16} />
                    </Link>
                </section>
            </div>
        </div>
    );
};

export default Dashboard;
