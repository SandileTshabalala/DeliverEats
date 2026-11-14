import { Link } from 'react-router-dom';
import { Bike, Clock, MapPin, Utensils } from 'lucide-react';
import { clsx } from 'clsx';
import { assetUrl } from '../services/platform';
import type { Restaurant } from '../services/restaurant';
import { RatingBadge } from './Stars';
import { formatClock } from '../utils/clock';

/** "R15 delivery", "From R15 delivery" (charged per km), "Free delivery", or "... · free over R150". */
export const deliveryNote = (restaurant: Restaurant) => {
    if (restaurant.delivery_fee_from == null) return null;
    const fee = Number(restaurant.delivery_fee_from);
    const over = restaurant.free_delivery_over ? Number(restaurant.free_delivery_over) : null;
    if (fee === 0 && !restaurant.delivery_per_km) return 'Free delivery';
    const base = `${restaurant.delivery_per_km ? 'From ' : ''}R${fee % 1 ? fee.toFixed(2) : fee} delivery`;
    return over ? `${base} · free over R${over % 1 ? over.toFixed(2) : over}` : base;
};

/** When a closed restaurant opens again, if it has hours. */
export const openingNote = (restaurant: Restaurant) => {
    if (restaurant.is_open) return restaurant.closes_at ? `Open until ${formatClock(restaurant.closes_at)}` : 'Open now';
    if (restaurant.accepting_orders === false) return 'Closed for now';
    return restaurant.opens_at ? `Closed · opens ${formatClock(restaurant.opens_at)}` : 'Closed';
};

const RestaurantCard = ({ restaurant }: { restaurant: Restaurant }) => {
    const open = restaurant.is_open !== false;
    return (
        <Link
            to={`/customer/menu/${restaurant.id}`}
            className={clsx(
                "group relative bg-gray-900 rounded-[32px] overflow-hidden border border-gray-800 hover:border-brand-500/50 transition-all flex flex-col",
                !open && "opacity-70"
            )}
        >
            <div className="h-48 bg-gray-800 relative overflow-hidden flex items-center justify-center">
                {restaurant.logo_img_url ? (
                    <img
                        src={assetUrl(restaurant.logo_img_url)}
                        alt=""
                        loading="lazy"
                        className={clsx("w-full h-full object-cover group-hover:scale-105 transition-transform duration-500", !open && "grayscale")}
                    />
                ) : (
                    <Utensils className="w-14 h-14 text-gray-700" />
                )}
                <div className="absolute top-4 left-4 flex items-center gap-2">
                    <span className="px-3 py-1.5 bg-gray-950/85 backdrop-blur-md rounded-full border border-white/10">
                        <RatingBadge rating={restaurant.rating} count={restaurant.review_count} />
                    </span>
                    {restaurant.category && (
                        <span className="px-3 py-1.5 bg-gray-950/85 backdrop-blur-md rounded-full border border-white/10 text-[11px] font-bold text-gray-200">
                            {restaurant.category}
                        </span>
                    )}
                </div>
            </div>
            <div className="p-6 space-y-3 flex-1 flex flex-col">
                <div className="space-y-1 flex-1">
                    <h3 className="text-xl font-black tracking-tight group-hover:text-brand-500 transition-colors">{restaurant.name}</h3>
                    {restaurant.description && <p className="text-gray-500 text-sm line-clamp-2">{restaurant.description}</p>}
                </div>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-3 border-t border-gray-800 text-xs font-bold">
                    <span className={clsx("flex items-center space-x-1.5", open ? "text-green-500" : "text-red-400")}>
                        <Clock size={14} />
                        <span>{openingNote(restaurant)}</span>
                    </span>
                    {deliveryNote(restaurant) && (
                        <span className="flex items-center space-x-1.5 text-gray-400">
                            <Bike size={14} className="text-brand-500" />
                            <span>{deliveryNote(restaurant)}</span>
                        </span>
                    )}
                    <span className="flex items-center space-x-1.5 text-gray-500 min-w-0">
                        <MapPin size={14} className="text-brand-500 flex-shrink-0" />
                        <span className="truncate">{restaurant.address.split(',')[0]}</span>
                    </span>
                </div>
            </div>
        </Link>
    );
};

export default RestaurantCard;
