import { useState, useEffect } from 'react';
import { assetUrl } from '../../services/platform';
import {
    UtensilsCrossed,
    Plus,
    Edit2,
    Trash2,
    Search,
    CheckCircle2,
    XCircle,
    Image as ImageIcon
} from 'lucide-react';
import { restaurantService } from '../../services/restaurant';
import type { MenuItem } from '../../services/restaurant';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import AddMenuItemModal from '../../components/restaurant/AddMenuItemModal';

const RestaurantMenus = () => {
    const { user } = useAuth();
    const [menus, setMenus] = useState<MenuItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const [editingItem, setEditingItem] = useState<MenuItem | null>(null);
    const [restaurantId, setRestaurantId] = useState<string | null>(null);

    useEffect(() => {
        if (user) {
            fetchMenus();
        }
    }, [user]);

    const fetchMenus = async () => {
        try {
            setLoading(true);
            // Ask the server which restaurant is ours. (This used to fall back to
            // the first restaurant in the public list, i.e. somebody else's menu.)
            const myRestaurant = await restaurantService.getMyRestaurant();
            setRestaurantId(myRestaurant.id);
            // The owner view includes sold-out items so they can be switched back on
            const data = await restaurantService.getManageMenu(myRestaurant.id);
            setMenus(data);
        } catch (error) {
            toast.error('Failed to fetch menu items');
        } finally {
            setLoading(false);
        }
    };

    const toggleAvailability = async (item: MenuItem) => {
        try {
            await restaurantService.updateMenuItem(item.id, { is_available: !item.is_available });
            toast.success(`${item.name} is now ${!item.is_available ? 'available' : 'unavailable'}`);
            fetchMenus();
        } catch (error) {
            toast.error('Failed to update item availability');
        }
    };

    const handleDelete = async (itemId: string) => {
        if (!window.confirm('Are you sure you want to delete this item?')) return;

        try {
            await restaurantService.deleteMenuItem(itemId);
            toast.success('Item deleted successfully');
            fetchMenus();
        } catch (error) {
            toast.error('Failed to delete item');
        }
    };

    const filteredMenus = menus.filter(m =>
        m.name.toLowerCase().includes(search.toLowerCase()) ||
        (m.description && m.description.toLowerCase().includes(search.toLowerCase()))
    );

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Menu Management</h1>
                    <p className="text-gray-400 mt-1">Add, edit or remove items from your digital menu.</p>
                </div>
                <button
                    onClick={() => {
                        setEditingItem(null);
                        setIsAddModalOpen(true);
                    }}
                    className="flex items-center space-x-2 px-6 py-3 bg-brand-600 hover:bg-brand-500 text-white font-bold rounded-2xl transition-all shadow-xl shadow-brand-600/20 active:scale-95"
                >
                    <Plus size={20} />
                    <span>Add New Item</span>
                </button>
            </div>

            {/* Controls */}
            <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1 relative group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-brand-500 transition-colors" size={20} />
                    <input
                        type="text"
                        placeholder="Search menu items..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full bg-gray-900/50 border border-gray-800 rounded-2xl pl-12 pr-4 py-3 focus:ring-1 focus:ring-brand-500 focus:border-brand-500 outline-none transition-all placeholder-gray-600"
                    />
                </div>
                <div className="flex bg-gray-900/50 border border-gray-800 rounded-2xl p-1.5 px-4 items-center space-x-2 text-sm font-bold text-gray-500 uppercase tracking-widest">
                    <UtensilsCrossed size={16} />
                    <span>{filteredMenus.length} Items</span>
                </div>
            </div>

            {/* Menu Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                <AnimatePresence mode="popLayout">
                    {loading ? (
                        [1, 2, 3].map(i => (
                            <div key={i} className="h-48 bg-gray-900/40 border border-gray-800 rounded-3xl animate-pulse" />
                        ))
                    ) : filteredMenus.length === 0 ? (
                        <div className="col-span-full p-20 text-center bg-gray-900/40 border border-gray-800 rounded-3xl border-dashed">
                            <UtensilsCrossed size={48} className="text-gray-700 mx-auto mb-4" />
                            <p className="text-gray-500 font-bold">Your menu is currently empty.</p>
                        </div>
                    ) : (
                        filteredMenus.map((item) => (
                            <motion.div
                                layout
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.9 }}
                                key={item.id}
                                className={clsx(
                                    "bg-gray-900/40 border rounded-3xl overflow-hidden group transition-all",
                                    item.is_available ? "border-gray-800" : "border-red-500/20 opacity-70 grayscale-[0.5]"
                                )}
                            >
                                <div className="h-40 bg-gray-800 relative overflow-hidden">
                                    {item.image_url ? (
                                        <img
                                            src={assetUrl(item.image_url)}
                                            alt={item.name}
                                            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                                        />
                                    ) : (
                                        <div className="absolute inset-0 flex items-center justify-center text-gray-700">
                                            <ImageIcon size={48} />
                                        </div>
                                    )}
                                    <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-transparent to-transparent opacity-60"></div>
                                    <div className="absolute top-4 left-4 z-20">
                                        <span className={clsx(
                                            "px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider shadow-lg",
                                            item.is_available ? "bg-green-500 text-black" : "bg-red-500 text-white"
                                        )}>
                                            {item.is_available ? 'Available' : 'Sold Out'}
                                        </span>
                                    </div>
                                </div>
                                <div className="p-6 relative">
                                    <div className="flex justify-between items-start gap-3 mb-2">
                                        <h3 className="font-bold text-lg text-white group-hover:text-brand-400 transition-colors uppercase tracking-tighter leading-tight">{item.name}</h3>
                                        <p className="font-black text-xl text-white whitespace-nowrap shrink-0">R {item.price}</p>
                                    </div>
                                    <p className="text-gray-500 text-xs line-clamp-2 leading-relaxed h-8 mb-6">{item.description || 'No description provided for this item.'}</p>
                                    <div className="flex items-center justify-between pt-4 border-t border-gray-800/50">
                                        <div className="flex items-center space-x-2">
                                            <button
                                                onClick={() => toggleAvailability(item)}
                                                className={clsx(
                                                    "p-2 rounded-xl transition-all",
                                                    item.is_available ? "bg-gray-800 text-gray-500 hover:text-red-400" : "bg-green-500/10 text-green-500 hover:bg-green-500/20"
                                                )}
                                                title={item.is_available ? 'Mark as Out of Stock' : 'Mark as Available'}
                                            >
                                                {item.is_available ? <XCircle size={18} /> : <CheckCircle2 size={18} />}
                                            </button>
                                            <button
                                                onClick={() => {
                                                    setEditingItem(item);
                                                    setIsAddModalOpen(true);
                                                }}
                                                className="p-2 bg-gray-800 text-gray-500 hover:text-white rounded-xl transition-all"
                                            >
                                                <Edit2 size={18} />
                                            </button>
                                        </div>
                                        <button
                                            onClick={() => handleDelete(item.id)}
                                            className="p-2 bg-gray-800 text-gray-500 hover:text-red-500 rounded-xl transition-all"
                                        >
                                            <Trash2 size={18} />
                                        </button>
                                    </div>
                                </div>
                            </motion.div>
                        ))
                    )}
                </AnimatePresence>
            </div>

            {restaurantId && (
                <AddMenuItemModal
                    isOpen={isAddModalOpen}
                    onClose={() => {
                        setIsAddModalOpen(false);
                        setEditingItem(null);
                    }}
                    onSuccess={fetchMenus}
                    restaurantId={restaurantId}
                    itemToEdit={editingItem}
                />
            )}
        </div>
    );
};

export default RestaurantMenus;
