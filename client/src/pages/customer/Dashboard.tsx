import { useState, useEffect } from 'react';
import {
    Search,
    MapPin,
    Clock,
    Star,
    ArrowRight,
    Utensils,
    Flame,
    Zap,
    Heart
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { restaurantService, type Restaurant } from '../../services/restaurant';
import { toast } from 'react-hot-toast';
import { motion } from 'framer-motion';
import { clsx } from 'clsx';

const categories = [
    { name: 'All', icon: Utensils },
    { name: 'Chicken Dust', icon: Flame },
    { name: 'Traditional', icon: Zap },
    { name: 'Fast Food', icon: Clock },
    { name: 'Healthy', icon: Heart },
];

const Dashboard = () => {
    const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [activeCategory, setActiveCategory] = useState('All');

    useEffect(() => {
        fetchRestaurants();
    }, []);

    const fetchRestaurants = async () => {
        try {
            setLoading(true);
            const data = await restaurantService.listRestaurants();
            // Filter to only show active restaurants
            setRestaurants(data.filter(r => r.is_active));
        } catch (error) {
            toast.error('Failed to load restaurants');
        } finally {
            setLoading(false);
        }
    };

    const filteredRestaurants = restaurants.filter(r =>
        r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (r.description && r.description.toLowerCase().includes(searchQuery.toLowerCase()))
    );

    return (
        <div className="space-y-12 animate-in fade-in duration-700">
            {/* Hero Section */}
            <section className="relative h-[450px] rounded-[40px] overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-r from-gray-950 via-gray-950/60 to-transparent z-10"></div>
                <div className="absolute inset-0 bg-blue-600/10 pointer-events-none"></div>

                {/* Visual placeholder for food image */}
                <div className="absolute inset-0 bg-gray-900 flex items-center justify-center">
                    <Flame className="w-64 h-64 text-gray-800 animate-pulse" />
                </div>

                <div className="relative z-20 h-full flex flex-col justify-center px-12 md:px-20 space-y-6 max-w-2xl">
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="inline-flex items-center space-x-2 px-3 py-1 bg-blue-600 rounded-full"
                    >
                        <Zap size={14} className="text-white fill-current" />
                        <span className="text-[10px] font-black uppercase tracking-widest text-white">Most Wanted in Matafini</span>
                    </motion.div>

                    <motion.h1
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        className="text-5xl md:text-7xl font-black tracking-tight leading-none uppercase italic"
                    >
                        Chicken Dust <br />
                        <span className="text-blue-500">Mastered.</span>
                    </motion.h1>

                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.2 }}
                        className="text-gray-400 text-lg font-medium leading-relaxed"
                    >
                        Order from the best local vendors and experience the true taste of traditional charcoal grilled chicken.
                    </motion.p>

                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.3 }}
                        className="flex items-center space-x-4 pt-4"
                    >
                        <div className="flex -space-x-3">
                            {[1, 2, 3, 4].map(i => (
                                <div key={i} className="w-10 h-10 rounded-full border-2 border-gray-950 bg-gray-800"></div>
                            ))}
                        </div>
                        <p className="text-sm font-bold text-gray-400">
                            <span className="text-white">2.4k+</span> reviews this month
                        </p>
                    </motion.div>
                </div>
            </section>

            {/* Search and Filters */}
            <section className="space-y-8">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div className="relative group flex-1 max-w-md">
                        <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-blue-500 transition-colors" size={20} />
                        <input
                            type="text"
                            placeholder="What are you craving?"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full bg-gray-900/50 border border-gray-800 rounded-2xl py-4 pl-14 pr-6 text-white outline-none focus:ring-1 focus:ring-blue-500 transition-all font-medium"
                        />
                    </div>

                    <div className="flex items-center space-x-2 overflow-x-auto pb-2 no-scrollbar">
                        {categories.map((cat) => (
                            <button
                                key={cat.name}
                                onClick={() => setActiveCategory(cat.name)}
                                className={clsx(
                                    "flex items-center space-x-2 px-5 py-3 rounded-2xl text-xs font-black uppercase tracking-widest transition-all whitespace-nowrap",
                                    activeCategory === cat.name
                                        ? "bg-white text-black shadow-xl"
                                        : "bg-gray-900 border border-gray-800 text-gray-500 hover:text-white"
                                )}
                            >
                                <cat.icon size={14} />
                                <span>{cat.name}</span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Popular Restaurants */}
                <div className="space-y-6">
                    <div className="flex items-center justify-between">
                        <h2 className="text-2xl font-black uppercase tracking-tighter italic">Popular Near You</h2>
                        <Link to="/customer/restaurants" className="flex items-center space-x-2 text-blue-500 font-bold hover:space-x-3 transition-all">
                            <span>See all</span>
                            <ArrowRight size={18} />
                        </Link>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {loading ? (
                            [1, 2, 3].map(i => (
                                <div key={i} className="h-80 bg-gray-900 rounded-[32px] animate-pulse"></div>
                            ))
                        ) : filteredRestaurants.length === 0 ? (
                            <div className="col-span-full py-20 text-center bg-gray-900/40 rounded-[32px] border border-gray-800 border-dashed">
                                <Search className="mx-auto text-gray-700 mb-4" size={48} />
                                <p className="text-gray-500 font-black uppercase">No restaurants found</p>
                            </div>
                        ) : (
                            filteredRestaurants.map((res) => (
                                <Link
                                    to={`/customer/menu/${res.id}`}
                                    key={res.id}
                                    className="group relative bg-gray-900 rounded-[32px] overflow-hidden border border-gray-800 hover:border-blue-500/50 transition-all"
                                >
                                    <div className="h-48 bg-gray-800 relative overflow-hidden flex items-center justify-center">
                                        {res.logo_img_url ? (
                                            <img
                                                src={res.logo_img_url}
                                                alt={res.name}
                                                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                            />
                                        ) : (
                                            <Utensils className="w-12 h-12 text-gray-700 group-hover:scale-110 transition-transform duration-500" />
                                        )}
                                        <div className="absolute inset-0 bg-blue-500/10 group-hover:bg-blue-500/0 transition-colors"></div>
                                        <div className="absolute top-4 left-4 z-20">
                                            <div className="flex items-center space-x-1 px-3 py-1.5 bg-gray-950/80 backdrop-blur-md rounded-full border border-white/10 shadow-lg">
                                                <Star className="text-blue-500 fill-current" size={12} />
                                                <span className="text-[10px] font-black text-white">4.8</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="p-8 space-y-4">
                                        <div className="space-y-1">
                                            <h3 className="text-2xl font-black tracking-tight group-hover:text-blue-500 transition-colors uppercase italic">{res.name}</h3>
                                            <p className="text-gray-500 text-sm font-medium line-clamp-1">{res.address}</p>
                                        </div>
                                        <div className="flex items-center justify-between pt-4 border-t border-gray-800">
                                            <div className="flex items-center space-x-4">
                                                <div className="flex items-center space-x-2 text-gray-500">
                                                    <Clock size={14} className="text-blue-500" />
                                                    <span className="text-xs font-bold uppercase tracking-wider">25 min</span>
                                                </div>
                                                <div className="flex items-center space-x-2 text-gray-500">
                                                    <MapPin size={14} className="text-blue-500" />
                                                    <span className="text-xs font-bold uppercase tracking-wider">1.2 km</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </Link>
                            ))
                        )}
                    </div>
                </div>
            </section>
        </div>
    );
};

export default Dashboard;
