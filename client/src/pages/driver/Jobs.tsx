import { useState, useEffect } from 'react';
import OrderDetailsModal from '../../components/OrderDetailsModal';
import type { OrderDetails } from '../../components/OrderDetailsModal';
import { orderRef, fullName, phoneHref } from '../../services/orders';
import { formatRand } from '../../context/CartContext';
import {
    Truck,
    Search,
    MapPin,
    Calendar,
    ChevronRight,
    CheckCircle2,
} from 'lucide-react';
import { driverService } from '../../services/drivers';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

import { orderStatus, when } from '../../utils/orderDisplay';
const Jobs = () => {
    const [jobs, setJobs] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [viewing, setViewing] = useState<OrderDetails | null>(null);
    const [filter, setFilter] = useState<'all' | 'completed' | 'cancelled'>('all');

    useEffect(() => {
        fetchJobs();
    }, []);

    const fetchJobs = async () => {
        try {
            setLoading(true);
            const data = await driverService.getHistory(); // Use history to see all past jobs
            setJobs(data);
        } catch (error) {
            toast.error('Failed to fetch delivery history');
        } finally {
            setLoading(false);
        }
    };

    const filteredJobs = jobs.filter(job => {
        const matchesSearch = job.id.toLowerCase().includes(search.toLowerCase()) ||
            (job.restaurant_name && job.restaurant_name.toLowerCase().includes(search.toLowerCase()));
        const matchesFilter = filter === 'all' || job.status === filter;
        return matchesSearch && matchesFilter;
    });

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Delivery History</h1>
                    <p className="text-gray-400 mt-1">Review your completed and pending deliveries.</p>
                </div>
                <button
                    onClick={fetchJobs}
                    className="flex items-center space-x-2 px-4 py-2.5 bg-gray-900 border border-gray-800 text-gray-300 hover:text-white rounded-xl transition-all"
                >
                    <Truck size={18} />
                    <span>Refresh List</span>
                </button>
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1 relative group">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-brand-500 transition-colors" size={20} />
                    <input
                        type="text"
                        placeholder="Search by order ID or restaurant..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full bg-gray-900/50 border border-gray-800 rounded-xl pl-10 pr-4 py-2.5 focus:ring-1 focus:ring-brand-500 focus:border-brand-500 outline-none transition-all placeholder-gray-600"
                    />
                </div>
                <div className="flex bg-gray-900/50 border border-gray-800 rounded-xl p-1">
                    {(['all', 'completed', 'cancelled'] as const).map((f) => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={clsx(
                                "px-4 py-1.5 rounded-lg text-sm font-bold transition-all uppercase tracking-wider",
                                filter === f ? "bg-brand-500 text-black shadow-lg" : "text-gray-500 hover:text-gray-300"
                            )}
                        >
                            {f}
                        </button>
                    ))}
                </div>
            </div>

            {/* Jobs List */}
            <div className="space-y-4">
                {loading ? (
                    [1, 2, 3].map(i => (
                        <div key={i} className="h-24 bg-gray-900/40 border border-gray-800 rounded-3xl animate-pulse"></div>
                    ))
                ) : filteredJobs.length === 0 ? (
                    <div className="p-12 text-center bg-gray-900/40 border border-gray-800 rounded-3xl border-dashed">
                        <p className="text-gray-500 font-medium">No deliveries found matching your search.</p>
                    </div>
                ) : (
                    <div className="grid gap-4">
                        <AnimatePresence mode="popLayout">
                            {filteredJobs.map((job) => (
                                <motion.div
                                    layout
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.95 }}
                                    key={job.id}
                                    className="p-5 bg-gray-900/40 hover:bg-gray-800/40 border border-gray-800 rounded-3xl transition-all group flex flex-col md:flex-row md:items-center justify-between gap-4"
                                >
                                    <div className="flex items-center space-x-4">
                                        <div className={clsx(
                                            "w-12 h-12 rounded-2xl flex items-center justify-center font-bold",
                                            job.status === 'delivered' ? "bg-green-500/10 text-green-500" : "bg-gray-800 text-gray-400"
                                        )}>
                                            {job.status === 'delivered' ? <CheckCircle2 size={24} /> : <Truck size={24} />}
                                        </div>
                                        <div>
                                            <div className="flex items-center space-x-2">
                                                <p className="font-bold text-white">{job.restaurant_name || 'Restaurant'}</p>
                                                <span className="text-xs text-gray-600 font-mono">{orderRef(job.id)}</span>
                                            </div>
                                            <div className="flex flex-wrap items-center gap-y-1 gap-x-4 mt-1">
                                                <div className="flex items-center text-xs text-gray-500 space-x-1">
                                                    <MapPin size={12} className="text-brand-500/50" />
                                                    <span>{job.delivery_address || 'No delivery address on this order'}</span>
                                                </div>
                                                {job.customer && (
                                                    <div className="flex items-center text-xs text-gray-500 space-x-2">
                                                        <span>{fullName(job.customer) || 'Customer'}</span>
                                                        {job.customer.contact_number && (
                                                            <a href={phoneHref(job.customer.contact_number)} className="text-brand-500 font-bold hover:text-brand-400">
                                                                Call {job.customer.contact_number}
                                                            </a>
                                                        )}
                                                    </div>
                                                )}
                                                <div className="flex items-center text-xs text-gray-500 space-x-1">
                                                    <Calendar size={12} className="text-brand-500/50" />
                                                    <span>{when(job.created_at)}</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between md:justify-end gap-4">
                                        <div className="text-right hidden sm:block">
                                            <p className="text-lg font-bold text-white">{formatRand(job.total || 0)}</p>
                                            <p className="text-[10px] text-gray-500 uppercase font-bold tracking-widest">{orderStatus(job.status).label}</p>
                                        </div>
                                        <button aria-label={`View order ${orderRef(job.id)}`} onClick={() => setViewing(job)} className="p-2 text-gray-500 group-hover:text-brand-500 bg-gray-800/50 rounded-xl transition-colors">
                                            <ChevronRight size={24} />
                                        </button>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                )}
            </div>
            <OrderDetailsModal order={viewing} onClose={() => setViewing(null)} />
        </div>
    );
};

export default Jobs;
