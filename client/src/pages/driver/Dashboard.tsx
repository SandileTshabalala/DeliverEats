import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useShareDriverLocation } from '../../hooks/useLiveLocation';
import OrderDetailsModal from '../../components/OrderDetailsModal';
import type { OrderDetails } from '../../components/OrderDetailsModal';
import { orderRef, fullName, phoneHref } from '../../services/orders';
import {
    Truck,
    CheckCircle2,
    Clock,
    Power,
    MapPin,
    Navigation,
    TrendingUp
} from 'lucide-react';
import { driverService } from '../../services/drivers';
import type { DriverProfile } from '../../services/drivers';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';

const DriverDashboard = () => {
    const [profile, setProfile] = useState<DriverProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [jobs, setJobs] = useState<any[]>([]);
    const [isToggling, setIsToggling] = useState(false);

    const [statsData, setStatsData] = useState<any>(null);
    const [viewing, setViewing] = useState<OrderDetails | null>(null);
    // Share GPS while online or on a delivery: nearest-driver matching and the customer's tracking use it
    const sharing = useShareDriverLocation(profile?.id, !!profile && (profile.is_available || jobs.length > 0));

    useEffect(() => {
        fetchInitialData();
    }, []);

    const fetchInitialData = async () => {
        try {
            setLoading(true);
            const [profileData, jobsData, sData] = await Promise.all([
                driverService.getProfile(),
                driverService.getJobs(),
                driverService.getStats()
            ]);
            setProfile(profileData);
            setJobs(jobsData);
            setStatsData(sData);
        } catch (error) {
            toast.error('Failed to load dashboard data');
        } finally {
            setLoading(false);
        }
    };

    const handleToggleAvailability = async () => {
        if (!profile) return;
        try {
            setIsToggling(true);
            const result = await driverService.toggleAvailability(!profile.is_available);
            setProfile({ ...profile, is_available: result.is_available });
            if (result.is_available) {
                toast.success('You are online');
                // going online can hand you an order that was waiting for a driver
                setJobs(await driverService.getJobs());
            } else {
                toast.success(jobs.length > 0 ? 'You are offline. Finish this delivery; you will get no new jobs.' : 'You are offline');
            }
        } catch (error: any) {
            const detail = error.response?.data?.detail;
            toast.error(typeof detail === 'string' ? detail : 'Could not change your status. Check your connection and try again.');
        } finally {
            setIsToggling(false);
        }
    };

    const handleUpdateStatus = async (orderId: string, status: string) => {
        try {
            console.log(`Sending status update for ${orderId} to ${status}`);
            toast.loading(status === 'picked_up' ? 'Picking up order...' : 'Completing delivery...');
            await driverService.updateOrderStatus(orderId, status);
            toast.dismiss();
            toast.success(status === 'picked_up' ? 'Picked up. Drive safely.' : 'Delivered. Well done.');
            setViewing(null);
            fetchInitialData(); // Refresh list
        } catch (error: any) {
            console.error('Update status error:', error);
            toast.dismiss();
            const msg = error.response?.data?.detail || "Failed to update order";
            toast.error(msg);
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
        { label: 'Today\'s Deliveries', value: statsData?.today_deliveries || 0, icon: Truck, color: 'text-brand-500', bg: 'bg-brand-500/10' },
        { label: 'Completed', value: statsData?.completed_deliveries || 0, icon: CheckCircle2, color: 'text-green-500', bg: 'bg-green-500/10' },
        { label: 'Earnings', value: `R ${statsData?.total_earnings?.toFixed(2) || '0.00'}`, icon: TrendingUp, color: 'text-brand-500', bg: 'bg-brand-500/10' },
        { label: 'Deliveries completed', value: `${statsData?.reliability_score || 0}%`, icon: Clock, color: 'text-purple-500', bg: 'bg-purple-500/10' },
    ];

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Online/Offline Status Card */}
            <div className={clsx(
                "p-6 rounded-3xl border transition-all duration-300 shadow-2xl overflow-hidden relative",
                profile?.is_available
                    ? "bg-green-500/10 border-green-500/20"
                    : "bg-gray-900/50 border-gray-800"
            )}>
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
                    <div className="flex items-center space-x-6">
                        <div className={clsx(
                            "w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-500",
                            profile?.is_available ? "bg-green-500 text-white shadow-lg shadow-green-500/20" : "bg-gray-800 text-gray-400"
                        )}>
                            <Power size={32} />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-white">
                                {profile?.is_available ? 'You are Online' : 'You are Offline'}
                            </h2>
                            <p className="text-gray-400">
                                {jobs.length > 0
                                    ? (profile?.is_available
                                        ? 'On a delivery. You get the next job when this one is done.'
                                        : 'On a delivery. No new jobs after this one.')
                                    : (profile?.is_available
                                        ? 'Waiting for the next delivery'
                                        : 'Go online to start receiving jobs')}
                            </p>
                            {sharing !== 'off' && (
                                <p className={sharing === 'sharing' ? "text-xs text-green-500 mt-1" : "text-xs text-yellow-500 mt-1"}>
                                    {sharing === 'sharing' && 'Sharing your location with your customer while you work'}
                                    {sharing === 'starting' && 'Finding your location...'}
                                    {sharing === 'denied' && 'Location is blocked. Allow it in your browser so customers can follow their delivery.'}
                                    {sharing === 'unsupported' && 'This device cannot share its location.'}
                                </p>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={handleToggleAvailability}
                        disabled={isToggling}
                        className={clsx(
                            "px-8 py-4 rounded-2xl font-bold transition-all flex items-center justify-center space-x-3 min-w-[180px]",
                            profile?.is_available
                                ? "bg-gray-800 hover:bg-gray-700 text-white"
                                : "bg-brand-500 hover:bg-brand-600 text-black shadow-xl shadow-brand-500/20"
                        )}
                    >
                        {isToggling ? (
                            <div className="w-6 h-6 border-2 border-current border-t-transparent animate-spin rounded-full"></div>
                        ) : (
                            <>
                                <Power size={20} />
                                <span>{profile?.is_available ? 'Go Offline' : 'Go Online'}</span>
                            </>
                        )}
                    </button>
                </div>
                {/* Visual decoration */}
                {profile?.is_available && (
                    <div className="absolute top-0 right-0 -mr-8 -mt-8 w-32 h-32 bg-green-500/10 blur-3xl rounded-full animate-pulse"></div>
                )}
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {stats.map((stat, i) => (
                    <motion.div
                        key={stat.label}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="p-6 bg-gray-900/40 backdrop-blur-xl border border-gray-800 rounded-3xl hover:border-gray-700 transition-colors group"
                    >
                        <div className={clsx("w-12 h-12 rounded-2xl flex items-center justify-center mb-4 transition-transform group-hover:scale-110", stat.bg, stat.color)}>
                            <stat.icon size={24} />
                        </div>
                        <p className="text-xs font-bold text-gray-500 uppercase tracking-widest">{stat.label}</p>
                        <p className="text-2xl font-bold text-white mt-1">{stat.value}</p>
                    </motion.div>
                ))}
            </div>

            {/* Current/Active Jobs */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h3 className="text-xl font-bold text-white flex items-center space-x-2">
                        <Navigation size={20} className="text-brand-500" />
                        <span>Active Orders</span>
                    </h3>
                    <Link to="/driver/jobs" className="text-sm text-brand-500 hover:underline font-medium">View history</Link>
                </div>

                {jobs.length === 0 ? (
                    <div className="p-12 text-center bg-gray-900/40 backdrop-blur-xl border border-gray-800 border-dashed rounded-3xl">
                        <div className="w-16 h-16 bg-gray-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Truck size={32} className="text-gray-600" />
                        </div>
                        <p className="text-gray-400 font-medium tracking-tight">No deliveries right now.</p>
                        <p className="text-gray-600 text-sm mt-1">New jobs will appear here when you're online.</p>
                    </div>
                ) : (
                    <div className="grid gap-4">
                        {jobs.map((job) => (
                            <div key={job.id} className="p-6 bg-gray-900/40 border border-gray-800 rounded-3xl flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="flex items-center space-x-4">
                                    <div className="w-12 h-12 bg-brand-500/10 rounded-2xl flex items-center justify-center text-brand-500 font-bold">
                                        {orderRef(job.id).slice(0, 5)}
                                    </div>
                                    <div>
                                        <p className="font-bold text-white">{job.restaurant_name || 'Restaurant'} <span className="text-xs text-gray-600 font-mono">{orderRef(job.id)}</span></p>
                                        {job.customer && (
                                            <p className="text-xs text-gray-400 mt-1">
                                                {fullName(job.customer) || 'Customer'}
                                                {job.customer.contact_number && (
                                                    <a href={phoneHref(job.customer.contact_number)} className="ml-2 text-brand-500 font-bold hover:text-brand-400">
                                                        Call {job.customer.contact_number}
                                                    </a>
                                                )}
                                            </p>
                                        )}
                                        <div className="flex items-center text-xs text-gray-500 space-x-2 mt-1">
                                            <MapPin size={12} />
                                            <span>{job.delivery_address || 'No delivery address'}</span>
                                            <span>•</span>
                                            <span className="uppercase text-brand-500 font-bold">{job.status.replace('_', ' ')}</span>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-3">
                                    <button onClick={() => setViewing(job)} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-xl text-sm font-bold transition-all">Details</button>

                                    {['preparing', 'accepted', 'waiting_for_driver'].includes(job.status) && (
                                        <span className="px-3 py-2 text-xs font-bold text-gray-500">Kitchen is still preparing</span>
                                    )}

                                    {job.status === 'ready' && (
                                        <button
                                            onClick={() => handleUpdateStatus(job.id, 'picked_up')}
                                            className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-black rounded-xl text-sm font-bold transition-all shadow-lg shadow-brand-500/20"
                                        >
                                            Pick Up Order
                                        </button>
                                    )}

                                    {job.status === 'picked_up' && (
                                        <button
                                            onClick={() => handleUpdateStatus(job.id, 'delivered')}
                                            className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-xl text-sm font-bold transition-all shadow-lg shadow-green-500/20"
                                        >
                                            Complete Delivery
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            <OrderDetailsModal
                order={viewing}
                onClose={() => setViewing(null)}
                actions={viewing && (
                    <>
                        {viewing.status === 'ready' && (
                            <button onClick={() => handleUpdateStatus(viewing.id, 'picked_up')} className="flex-1 px-4 py-3 bg-brand-500 hover:bg-brand-600 text-black rounded-xl text-sm font-bold">
                                Pick Up Order
                            </button>
                        )}
                        {viewing.status === 'picked_up' && (
                            <button onClick={() => handleUpdateStatus(viewing.id, 'delivered')} className="flex-1 px-4 py-3 bg-green-500 hover:bg-green-600 text-white rounded-xl text-sm font-bold">
                                Complete Delivery
                            </button>
                        )}
                    </>
                )}
            />
        </div>
    );
};

export default DriverDashboard;
