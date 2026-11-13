import { useState, useEffect } from 'react';
import { assetUrl } from '../../services/platform';
import {
    Search,
    MapPin,
    Clock,
    Star,
    ChevronLeft,
    Utensils,
    Flame,
    Zap,
    Heart,
    Filter
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { restaurantService, type Restaurant } from '../../services/restaurant';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';

const categories = [
    { name: 'All', icon: Utensils },
    { name: 'Chicken Dust', icon: Flame },
    { name: 'Traditional', icon: Zap },
    { name: 'Fast Food', icon: Clock },
    { name: 'Healthy', icon: Heart },
];

const Restaurants = () => {
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
            setRestaurants(data.filter(r => r.is_active));
        } catch (error) {
            toast.error('Failed to load restaurants');
        } finally {
            setLoading(false);
        }
    };

    const filteredRestaurants = restaurants.filter(r =>
    (r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (r.description && r.description.toLowerCase().includes(searchQuery.toLowerCase())))
        // Category filtering would go here if backend supported it, for now just name search
    );

    return (
        <div className="space-y-12 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="space-y-1">
                    <Link
                        to="/customer"
                        className="flex items-center space-x-2 text-gray-500 hover:text-white transition-colors group mb-4"
                    >
                        <ChevronLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                        <span className="text-[10px] font-black uppercase tracking-widest">Back to Home</span>
                    </Link>
                    <h1 className="text-4xl font-black uppercase tracking-tighter italic">Explore Matafini</h1>
                    <p className="text-gray-500 font-medium">Find the best local flavors and charcoal grills.</p>
                </div>

                <div className="flex items-center space-x-4">
                    <div className="relative group flex-1 md:w-80">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-brand-500 transition-colors" size={18} />
                        <input
                            type="text"
                            placeholder="Search restaurants..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full bg-gray-900 border border-gray-800 rounded-2xl py-3.5 pl-12 pr-6 text-white outline-none focus:ring-1 focus:ring-brand-500 transition-all text-sm font-medium"
                        />
                    </div>
                    <button className="p-3.5 bg-gray-900 border border-gray-800 rounded-2xl text-gray-400 hover:text-white transition-all">
                        <Filter size={20} />
                    </button>
                </div>
            </div>

            {/* Categories */}
            <div className="flex items-center space-x-2 overflow-x-auto pb-4 no-scrollbar">
                {categories.map((cat) => (
                    <button
                        key={cat.name}
                        onClick={() => setActiveCategory(cat.name)}
                        className={clsx(
                            "flex items-center space-x-2 px-6 py-3.5 rounded-2xl text-xs font-black uppercase tracking-widest transition-all whitespace-nowrap",
                            activeCategory === cat.name
                                ? "bg-white text-black shadow-xl"
                                : "bg-gray-900 border border-gray-800 text-gray-400 hover:text-white"
                        )}
                    >
                        <cat.icon size={14} />
                        <span>{cat.name}</span>
                    </button>
                ))}
            </div>

            {/* Results Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 pb-20">
                {loading ? (
                    [1, 2, 3, 4, 5, 6].map(i => (
                        <div key={i} className="h-80 bg-gray-900 rounded-[40px] animate-pulse"></div>
                    ))
                ) : filteredRestaurants.length === 0 ? (
                    <div className="col-span-full py-32 text-center bg-gray-900/40 rounded-[40px] border border-gray-800 border-dashed">
                        <Utensils className="mx-auto text-gray-700 mb-4" size={48} />
                        <p className="text-gray-500 font-black uppercase tracking-widest">No restaurants found matching your search</p>
                    </div>
                ) : (
                    filteredRestaurants.map((res) => (
                        <Link
                            to={`/customer/menu/${res.id}`}
                            key={res.id}
                            className="group relative bg-gray-900 rounded-[40px] overflow-hidden border border-gray-800 hover:border-brand-500/50 transition-all flex flex-col"
                        >
                            <div className="h-52 bg-gray-800 relative overflow-hidden flex items-center justify-center">
                                {res.logo_img_url ? (
                                    <img
                                        src={assetUrl(res.logo_img_url)}
                                        alt={res.name}
                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                    />
                                ) : (
                                    <Utensils className="w-16 h-16 text-gray-700 group-hover:scale-110 transition-transform duration-500" />
                                )}
                                <div className="absolute inset-0 bg-brand-500/10 group-hover:bg-brand-500/0 transition-colors"></div>
                                <div className="absolute top-6 left-6 z-20">
                                    <div className="flex items-center space-x-1 px-4 py-2 bg-gray-950/80 backdrop-blur-md rounded-full border border-white/10 shadow-xl">
                                        <Star className="text-brand-500 fill-current" size={14} />
                                        <span className="text-xs font-black text-white">4.8</span>
                                    </div>
                                </div>
                            </div>
                            <div className="p-8 space-y-4 flex-1">
                                <div className="space-y-2">
                                    <h3 className="text-2xl font-black tracking-tight group-hover:text-brand-500 transition-colors uppercase italic">{res.name}</h3>
                                    <p className="text-gray-500 text-sm font-medium line-clamp-2 leading-relaxed">
                                        {res.description || "Authentic Matafini flavors prepared daily with fresh ingredients and traditional spices."}
                                    </p>
                                </div>
                                <div className="flex items-center justify-between pt-6 border-t border-gray-800">
                                    <div className="flex items-center space-x-4">
                                        <div className="flex items-center space-x-2 text-gray-500">
                                            <Clock size={16} className="text-brand-500" />
                                            <span className="text-xs font-bold uppercase tracking-wider">25-35 MIN</span>
                                        </div>
                                        <div className="flex items-center space-x-2 text-gray-500">
                                            <MapPin size={16} className="text-brand-500" />
                                            <span className="text-xs font-bold uppercase tracking-wider">{res.address.split(',')[0]}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </Link>
                    ))
                )}
            </div>
        </div>
    );
};

export default Restaurants;
