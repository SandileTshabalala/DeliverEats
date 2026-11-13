import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
    Utensils,
    ChevronLeft,
    Star,
    Clock,
    MapPin,
    Plus,
    Minus,
    ShoppingBag,
    Image as ImageIcon,
    Flame
} from 'lucide-react';
import { restaurantService, type MenuItem, type Restaurant } from '../../services/restaurant';
import { useCart } from '../../context/CartContext';
import { toast } from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';

const Menu = () => {
    const { restaurantId } = useParams<{ restaurantId: string }>();
    const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
    const [items, setItems] = useState<MenuItem[]>([]);
    const [loading, setLoading] = useState(true);
    const { items: cartItems, addToCart, updateQuantity, totalItems } = useCart();

    useEffect(() => {
        if (restaurantId) {
            fetchData();
        }
    }, [restaurantId]);

    const fetchData = async () => {
        if (!restaurantId) return;
        try {
            setLoading(true);
            const [restaurantData, menuData] = await Promise.all([
                restaurantService.getRestaurant(restaurantId),
                restaurantService.getMenu(restaurantId),
            ]);
            if (restaurantData) setRestaurant(restaurantData);
            setItems(menuData ?? []);
        } catch (error) {
            toast.error('Failed to load menu');
        } finally {
            setLoading(false);
        }
    };

    const getItemQuantity = (itemId: string) => {
        return cartItems.find(i => i.id === itemId)?.quantity || 0;
    };

    return (
        <div className="space-y-12 animate-in fade-in duration-500">
            {/* Header / Back Navigation */}
            <div className="flex items-center justify-between">
                <Link
                    to="/customer"
                    className="flex items-center space-x-2 text-gray-400 hover:text-white transition-colors group"
                >
                    <div className="p-2 bg-gray-900 rounded-xl group-hover:bg-gray-800 transition-colors">
                        <ChevronLeft size={20} />
                    </div>
                    <span className="font-bold uppercase tracking-widest text-xs">Back to Restaurants</span>
                </Link>
            </div>

            {/* Restaurant Hero Info */}
            <section className="bg-gray-900 rounded-[40px] p-8 md:p-12 relative overflow-hidden border border-gray-800">
                <div className="absolute top-0 right-0 p-12 opacity-10 pointer-events-none">
                    <Utensils size={180} className="text-brand-500" />
                </div>

                <div className="relative z-10 space-y-6 max-w-3xl">
                    <div className="flex items-center space-x-3">
                        <span className="px-3 py-1 bg-green-500/10 text-green-500 text-[10px] font-black uppercase tracking-widest rounded-full border border-green-500/20">Open Now</span>
                        <div className="flex items-center space-x-1 px-3 py-1 bg-brand-600 rounded-full text-[10px] font-black uppercase tracking-widest text-white">
                            <Star size={10} className="fill-current" />
                            <span>4.8 Rating</span>
                        </div>
                    </div>

                    <div className="flex flex-col md:flex-row md:items-center gap-6">
                        {restaurant?.logo_img_url && (
                            <div className="w-24 h-24 rounded-3xl overflow-hidden border-2 border-brand-500/20 flex-shrink-0 bg-gray-950">
                                <img src={restaurant.logo_img_url} alt={restaurant.name} className="w-full h-full object-cover" />
                            </div>
                        )}
                        <h1 className="text-4xl md:text-6xl font-black tracking-tighter uppercase italic text-white">
                            {restaurant?.name || 'Loading...'}
                        </h1>
                    </div>
                    <p className="text-gray-400 text-lg font-medium leading-relaxed">
                        {restaurant?.description || "Experience the finest traditional flavors prepared with passion and served with a side of Matafini's heart."}
                    </p>

                    <div className="flex flex-wrap items-center gap-6 pt-4 text-gray-400">
                        <div className="flex items-center space-x-2">
                            <MapPin size={18} className="text-brand-500" />
                            <span className="text-sm font-bold uppercase tracking-wider">{restaurant?.address}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                            <Clock size={18} className="text-brand-500" />
                            <span className="text-sm font-bold uppercase tracking-wider">25-35 MIN DELIVERY</span>
                        </div>
                    </div>
                </div>
            </section>

            {/* Menu Items Grid */}
            <section className="space-y-8 pb-20">
                <div className="flex items-center space-x-4">
                    <div className="w-1.5 h-8 bg-brand-600 rounded-full"></div>
                    <h2 className="text-3xl font-black uppercase tracking-tighter italic">Recommended Dishes</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {loading ? (
                        [1, 2, 3, 4, 5, 6].map(i => (
                            <div key={i} className="h-64 bg-gray-900 rounded-[32px] animate-pulse"></div>
                        ))
                    ) : items.length === 0 ? (
                        <div className="col-span-full py-20 text-center bg-gray-900/40 rounded-[32px] border border-gray-800 border-dashed">
                            <Flame className="mx-auto text-gray-700 mb-4" size={48} />
                            <p className="text-gray-500 font-black uppercase">The grill is quiet... No items found.</p>
                        </div>
                    ) : (
                        items.map((item) => (
                            <div
                                key={item.id}
                                className={clsx(
                                    "group bg-gray-900 rounded-[32px] overflow-hidden border transition-all duration-300 flex flex-col h-full",
                                    item.is_available ? "border-gray-800 hover:border-brand-500/50" : "opacity-60 border-red-500/10 grayscale-[0.5]"
                                )}
                            >
                                <div className="h-44 bg-gray-800 relative overflow-hidden">
                                    {item.image_url ? (
                                        <img
                                            src={item.image_url}
                                            alt={item.name}
                                            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                                        />
                                    ) : (
                                        <div className="absolute inset-0 flex items-center justify-center text-gray-700 bg-gray-900">
                                            <ImageIcon size={48} />
                                        </div>
                                    )}
                                    <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-transparent to-transparent opacity-60"></div>

                                    {!item.is_available && (
                                        <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px] flex items-center justify-center z-20">
                                            <span className="px-4 py-2 bg-red-500 text-white font-black uppercase tracking-widest text-xs rounded-full shadow-2xl">Sold Out</span>
                                        </div>
                                    )}
                                </div>

                                <div className="p-6 flex flex-col flex-1 space-y-4">
                                    <div className="flex-1 space-y-2">
                                        <div className="flex justify-between items-start">
                                            <h3 className="text-xl font-black tracking-tight group-hover:text-brand-500 transition-colors uppercase italic leading-tight">
                                                {item.name}
                                            </h3>
                                            <p className="text-lg font-black text-white whitespace-nowrap ml-2">R {item.price}</p>
                                        </div>
                                        <p className="text-gray-500 text-sm font-medium line-clamp-2 leading-relaxed h-10">
                                            {item.description || "Freshly prepared with our secret blend of spices and charcoal grilled to perfection."}
                                        </p>
                                    </div>

                                    <div className="pt-4 border-t border-gray-800">
                                        <AnimatePresence mode="wait">
                                            {getItemQuantity(item.id) > 0 ? (
                                                <motion.div
                                                    initial={{ opacity: 0, scale: 0.9 }}
                                                    animate={{ opacity: 1, scale: 1 }}
                                                    exit={{ opacity: 0, scale: 0.9 }}
                                                    className="flex items-center justify-between bg-brand-600 rounded-2xl p-1"
                                                >
                                                    <button
                                                        onClick={() => updateQuantity(item.id, -1)}
                                                        className="p-3 hover:bg-white/10 rounded-xl transition-colors"
                                                    >
                                                        <Minus size={18} />
                                                    </button>
                                                    <span className="font-black text-lg">{getItemQuantity(item.id)}</span>
                                                    <button
                                                        onClick={() => updateQuantity(item.id, 1)}
                                                        className="p-3 hover:bg-white/10 rounded-xl transition-colors"
                                                    >
                                                        <Plus size={18} />
                                                    </button>
                                                </motion.div>
                                            ) : (
                                                <button
                                                    disabled={!item.is_available}
                                                    onClick={() => addToCart({ ...item, restaurant_id: restaurantId })}
                                                    className="w-full flex items-center justify-between space-x-3 py-3 rounded-2xl bg-gray-950 border border-gray-800 text-gray-300 font-black uppercase tracking-widest text-xs hover:bg-brand-600 hover:text-white hover:border-brand-600 transition-all active:scale-95 disabled:opacity-0 disabled:pointer-events-none"
                                                >
                                                    <Plus size={16} />
                                                    <span>Add to Cart</span>
                                                </button>
                                            )}
                                        </AnimatePresence>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </section>

            {/* Cart Floating Button */}
            <AnimatePresence>
                {totalItems > 0 && (
                    <motion.div
                        initial={{ y: 100, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        exit={{ y: 100, opacity: 0 }}
                        className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 w-full max-w-sm px-6"
                    >
                        <Link
                            to="/customer/cart"
                            className="w-full bg-brand-600 hover:bg-brand-500 text-white flex items-center justify-between p-5 rounded-[28px] shadow-2xl shadow-brand-600/30 active:scale-[0.98] transition-all group"
                        >
                            <div className="flex items-center space-x-4">
                                <div className="bg-white/20 p-2 rounded-xl group-hover:rotate-12 transition-transform">
                                    <ShoppingBag size={24} />
                                </div>
                                <div className="text-left">
                                    <p className="text-xs font-black uppercase tracking-widest opacity-70">View Cart</p>
                                    <p className="font-black uppercase tracking-tighter">{totalItems} Items Selected</p>
                                </div>
                            </div>
                            <ChevronLeft className="rotate-180" size={24} />
                        </Link>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default Menu;
