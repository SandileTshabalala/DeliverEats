import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, Utensils, X } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import CategoryRail, { sells } from './CategoryRail';
import RestaurantCard from './RestaurantCard';
import { restaurantService, type Restaurant } from '../services/restaurant';

/**
 * Search, food-type tiles, "Open now" and the restaurant grid. Used on the
 * customer home and the Restaurants page. The chosen food type is kept in the
 * address (?category=Chicken) so it survives going back from a menu.
 */
const RestaurantBrowser = ({ title = 'All restaurants' }: { title?: string }) => {
    const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
    const [loading, setLoading] = useState(true);
    const [params, setParams] = useSearchParams();
    const [search, setSearch] = useState(params.get('q') ?? '');
    const category = params.get('category') || 'All';
    const openOnly = params.get('open') === '1';

    useEffect(() => {
        restaurantService.listRestaurants()
            .then(data => setRestaurants(data.filter(r => r.is_active)))
            .catch(() => toast.error('Could not load restaurants'))
            .finally(() => setLoading(false));
    }, []);

    const setParam = (key: string, value: string | null) => {
        const next = new URLSearchParams(params);
        if (value) next.set(key, value); else next.delete(key);
        setParams(next, { replace: true });
    };

    const query = search.trim().toLowerCase();
    const shown = restaurants.filter(r =>
        (category === 'All' || sells(r, category))
        && (!openOnly || r.is_open)
        && (!query || [r.name, r.description, r.address, ...(r.categories ?? [r.category])]
            .some(field => (field ?? '').toLowerCase().includes(query)))
    );
    const openCount = restaurants.filter(r => r.is_open).length;
    const filtering = query !== '' || category !== 'All' || openOnly;

    return (
        <div className="space-y-6">
            <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" size={20} />
                <input
                    type="search"
                    aria-label="Search restaurants and food"
                    placeholder="Search restaurants, food or your area"
                    value={search}
                    onChange={event => setSearch(event.target.value)}
                    className="w-full bg-gray-900 border border-gray-800 rounded-2xl py-4 pl-12 pr-12 text-white placeholder-gray-500 outline-none focus:ring-2 focus:ring-brand-500"
                />
                {search && (
                    <button onClick={() => setSearch('')} aria-label="Clear search" className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-gray-500 hover:text-white">
                        <X size={18} />
                    </button>
                )}
            </div>

            <CategoryRail restaurants={restaurants} active={category} onChange={name => setParam('category', name === 'All' ? null : name)} />

            <section className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <h2 className="text-xl font-black">
                        {filtering ? `${shown.length} ${shown.length === 1 ? 'restaurant' : 'restaurants'}${category !== 'All' ? ` · ${category}` : ''}` : title}
                    </h2>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => setParam('open', openOnly ? null : '1')}
                            aria-pressed={openOnly}
                            className={clsx(
                                "px-4 py-2 rounded-full text-sm font-bold whitespace-nowrap transition-colors",
                                openOnly ? "bg-green-500 text-white" : "bg-gray-900 border border-gray-800 text-gray-300 hover:text-white"
                            )}
                        >
                            Open now{openCount ? ` (${openCount})` : ''}
                        </button>
                        {filtering && (
                            <button onClick={() => { setSearch(''); setParams({}, { replace: true }); }} className="text-sm font-bold text-brand-500 hover:text-brand-400">
                                Clear
                            </button>
                        )}
                    </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                    {loading ? (
                        [1, 2, 3, 4, 5, 6].map(i => <div key={i} className="h-80 bg-gray-900 rounded-[32px] animate-pulse" />)
                    ) : shown.length === 0 ? (
                        <div className="col-span-full py-20 text-center bg-gray-900/40 rounded-[32px] border border-gray-800 border-dashed space-y-2">
                            <Utensils className="mx-auto text-gray-700" size={44} />
                            <p className="text-gray-400 font-bold">
                                {restaurants.length === 0 ? 'No restaurants are taking orders yet. Check back soon.' : 'Nothing matches. Try another search or food type.'}
                            </p>
                        </div>
                    ) : (
                        shown.map(restaurant => <RestaurantCard key={restaurant.id} restaurant={restaurant} />)
                    )}
                </div>
            </section>
        </div>
    );
};

export default RestaurantBrowser;
