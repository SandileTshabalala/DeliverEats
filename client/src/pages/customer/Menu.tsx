import { useEffect, useState } from 'react';
import { formatClock } from '../../utils/clock';
import { Link, useParams } from 'react-router-dom';
import { Bike, ChevronLeft, Clock, Image as ImageIcon, MapPin, Minus, Plus, Search, Utensils, X } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { RatingBadge } from '../../components/Stars';
import { deliveryNote, openingNote } from '../../components/RestaurantCard';
import { formatRand, useCart } from '../../context/CartContext';
import { assetUrl } from '../../services/platform';
import { restaurantService, type MenuItem, type Restaurant } from '../../services/restaurant';

/** Item details with quantity, opened by tapping a dish. */
const ItemSheet = ({ item, open, onClose, onAdd }: {
    item: MenuItem; open: boolean; onClose: () => void; onAdd: (quantity: number) => void;
}) => {
    const [quantity, setQuantity] = useState(1);
    useEffect(() => {
        const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [onClose]);

    return (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-end sm:items-center justify-center sm:p-4" onClick={onClose}>
            <div
                role="dialog"
                aria-modal="true"
                aria-label={item.name}
                onClick={event => event.stopPropagation()}
                className="bg-gray-900 border border-gray-800 rounded-t-3xl sm:rounded-3xl w-full max-w-lg max-h-[92vh] overflow-y-auto"
            >
                <div className="relative">
                    {item.image_url ? (
                        <img src={assetUrl(item.image_url)} alt="" className="w-full aspect-[16/10] object-cover sm:rounded-t-3xl rounded-t-3xl" />
                    ) : (
                        <div className="w-full h-20" />
                    )}
                    <button onClick={onClose} aria-label="Close" className="absolute top-3 right-3 p-2 bg-gray-950/90 text-white rounded-full">
                        <X size={18} />
                    </button>
                </div>
                <div className="p-6 space-y-4">
                    <div>
                        <h2 className="text-2xl font-black">{item.name}</h2>
                        <p className="text-lg font-bold text-brand-500 mt-1">{formatRand(item.price)}</p>
                    </div>
                    {item.description && <p className="text-gray-400 leading-relaxed">{item.description}</p>}
                    {open ? (
                        <div className="flex items-center gap-3 pt-2">
                            <div className="flex items-center bg-gray-950 border border-gray-800 rounded-2xl">
                                <button aria-label="One less" onClick={() => setQuantity(q => Math.max(1, q - 1))} className="p-3.5 text-gray-300 hover:text-white"><Minus size={18} /></button>
                                <span className="w-8 text-center font-black text-lg" aria-live="polite">{quantity}</span>
                                <button aria-label="One more" onClick={() => setQuantity(q => Math.min(50, q + 1))} className="p-3.5 text-gray-300 hover:text-white"><Plus size={18} /></button>
                            </div>
                            <button
                                onClick={() => onAdd(quantity)}
                                className="flex-1 py-4 bg-brand-600 hover:bg-brand-500 text-white font-black rounded-2xl"
                            >
                                Add {quantity} · {formatRand(Number(item.price) * quantity)}
                            </button>
                        </div>
                    ) : (
                        <p className="text-sm font-bold text-red-400">{item.is_available ? 'The restaurant is closed right now.' : 'Sold out for now.'}</p>
                    )}
                </div>
            </div>
        </div>
    );
};

const Menu = () => {
    const { restaurantId } = useParams<{ restaurantId: string }>();
    const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
    const [items, setItems] = useState<MenuItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [viewing, setViewing] = useState<MenuItem | null>(null);
    const { items: cartItems, addToCart, updateQuantity } = useCart();

    useEffect(() => {
        if (!restaurantId) return;
        Promise.all([restaurantService.getRestaurant(restaurantId), restaurantService.getMenu(restaurantId)])
            .then(([restaurantData, menu]) => {
                setRestaurant(restaurantData);
                setItems(menu ?? []);
            })
            .catch(() => toast.error('Could not load the menu'))
            .finally(() => setLoading(false));
    }, [restaurantId]);

    // Unknown (still loading) counts as open so the page does not flash "closed"
    const isOpen = restaurant?.is_open !== false;
    const quantityOf = (id: string) => cartItems.find(i => i.id === id)?.quantity ?? 0;
    const orderable = (item: MenuItem) => item.is_available && isOpen;

    const add = (item: MenuItem, quantity = 1) => {
        if (!orderable(item)) return;
        addToCart({ ...item, restaurant_id: restaurantId, restaurant_name: restaurant?.name });
        if (quantity > 1) updateQuantity(item.id, quantity - 1);
    };

    const query = search.trim().toLowerCase();
    const shown = items.filter(item => !query || item.name.toLowerCase().includes(query) || (item.description ?? '').toLowerCase().includes(query));
    const banner = restaurant?.logo_img_url || items.find(item => item.image_url)?.image_url;

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <Link to="/customer" className="inline-flex items-center space-x-2 text-sm font-bold text-gray-400 hover:text-white">
                <ChevronLeft size={18} /><span>All restaurants</span>
            </Link>

            {/* Banner and details */}
            <section className="space-y-5">
                <div className="keep-dark relative h-40 md:h-56 rounded-3xl overflow-hidden bg-gray-900 border border-gray-800">
                    {banner ? (
                        <img src={assetUrl(banner)} alt="" className={clsx("w-full h-full object-cover", !isOpen && "grayscale")} />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center"><Utensils size={56} className="text-gray-700" /></div>
                    )}
                    {!isOpen && restaurant && (
                        <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                            <span className="px-4 py-2 bg-gray-950/90 rounded-full font-bold text-white">{openingNote(restaurant)}</span>
                        </div>
                    )}
                </div>
                <div className="space-y-2">
                    <h1 className="text-3xl md:text-4xl font-black tracking-tight">{restaurant?.name ?? (loading ? 'Loading...' : 'Restaurant')}</h1>
                    {restaurant && (
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm font-bold text-gray-400">
                            <RatingBadge rating={restaurant.rating} count={restaurant.review_count} />
                            {(restaurant.categories?.length ? restaurant.categories : restaurant.category ? [restaurant.category] : []).length > 0 && <span>{(restaurant.categories?.length ? restaurant.categories : [restaurant.category]).join(' · ')}</span>}
                            <span className={clsx("flex items-center gap-1.5", isOpen ? "text-green-500" : "text-red-400")}>
                                <Clock size={14} />{openingNote(restaurant)}
                            </span>
                            {deliveryNote(restaurant) && <span className="flex items-center gap-1.5"><Bike size={14} className="text-brand-500" />{deliveryNote(restaurant)}</span>}
                            <span className="flex items-center gap-1.5"><MapPin size={14} className="text-brand-500" />{restaurant.address}</span>
                        </div>
                    )}
                    {restaurant?.description && <p className="text-gray-400 max-w-3xl">{restaurant.description}</p>}
                </div>
                {restaurant && !isOpen && (
                    <p role="status" className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 font-bold text-sm">
                        {restaurant.name} is closed right now{restaurant.accepting_orders !== false && restaurant.opens_at ? ` and opens at ${formatClock(restaurant.opens_at)}` : ''}.
                        You can look at the menu, but orders are paused.
                    </p>
                )}
            </section>

            {/* Menu */}
            <section className="space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <h2 className="text-2xl font-black">Menu</h2>
                    {items.length > 6 && (
                        <div className="relative sm:w-72">
                            <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500" />
                            <input
                                type="search"
                                aria-label="Search this menu"
                                placeholder="Search the menu"
                                value={search}
                                onChange={event => setSearch(event.target.value)}
                                className="w-full bg-gray-900 border border-gray-800 rounded-xl py-2.5 pl-10 pr-3 text-white placeholder-gray-500 outline-none focus:ring-2 focus:ring-brand-500"
                            />
                        </div>
                    )}
                </div>

                {loading ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {[1, 2, 3, 4].map(i => <div key={i} className="h-36 bg-gray-900 rounded-2xl animate-pulse" />)}
                    </div>
                ) : shown.length === 0 ? (
                    <div className="py-16 text-center bg-gray-900/40 rounded-3xl border border-gray-800 border-dashed">
                        <p className="text-gray-400 font-bold">{items.length === 0 ? 'This restaurant has not added its menu yet.' : 'No dishes match your search.'}</p>
                    </div>
                ) : (
                    <ul className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {shown.map(item => {
                            const inCart = quantityOf(item.id);
                            return (
                                <li key={item.id}>
                                    <div
                                        className={clsx(
                                            "group flex gap-4 p-4 h-full bg-gray-900 border rounded-2xl transition-colors",
                                            item.is_available ? "border-gray-800 hover:border-gray-700" : "border-gray-800 opacity-60"
                                        )}
                                    >
                                        <button onClick={() => setViewing(item)} className="flex-1 min-w-0 text-left space-y-1.5">
                                            <p className="font-bold text-white text-lg leading-snug">{item.name}</p>
                                            <p className="font-bold text-gray-300">{formatRand(item.price)}</p>
                                            {item.description && <p className="text-sm text-gray-500 line-clamp-2">{item.description}</p>}
                                            {!item.is_available && <p className="text-xs font-black uppercase tracking-widest text-red-400">Sold out</p>}
                                        </button>
                                        <div className="relative flex-shrink-0">
                                            <button onClick={() => setViewing(item)} aria-label={`About ${item.name}`} className="block w-28 h-28 rounded-xl overflow-hidden bg-gray-800">
                                                {item.image_url
                                                    ? <img src={assetUrl(item.image_url)} alt="" loading="lazy" className="w-full h-full object-cover" />
                                                    : <span className="w-full h-full flex items-center justify-center text-gray-700"><ImageIcon size={28} /></span>}
                                            </button>
                                            {orderable(item) && (
                                                inCart > 0 ? (
                                                    <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 flex items-center bg-gray-950 border border-gray-800 rounded-full shadow-lg">
                                                        <button aria-label={`One less ${item.name}`} onClick={() => updateQuantity(item.id, -1)} className="p-2 text-gray-300 hover:text-white"><Minus size={14} /></button>
                                                        <span className="w-6 text-center text-sm font-black">{inCart}</span>
                                                        <button aria-label={`One more ${item.name}`} onClick={() => updateQuantity(item.id, 1)} className="p-2 text-gray-300 hover:text-white"><Plus size={14} /></button>
                                                    </div>
                                                ) : (
                                                    <button
                                                        aria-label={`Add ${item.name}`}
                                                        onClick={() => { add(item); toast.success(`${item.name} added`, { duration: 1500 }); }}
                                                        className="absolute -bottom-2 -right-2 w-10 h-10 bg-brand-600 hover:bg-brand-500 text-white rounded-full shadow-lg flex items-center justify-center"
                                                    >
                                                        <Plus size={20} />
                                                    </button>
                                                )
                                            )}
                                        </div>
                                    </div>
                                </li>
                            );
                        })}
                    </ul>
                )}
            </section>

            {viewing && (
                <ItemSheet
                    item={viewing}
                    open={orderable(viewing)}
                    onClose={() => setViewing(null)}
                    onAdd={quantity => {
                        add(viewing, quantity);
                        toast.success(`${quantity} × ${viewing.name} added`, { duration: 1500 });
                        setViewing(null);
                    }}
                />
            )}
        </div>
    );
};

export default Menu;
