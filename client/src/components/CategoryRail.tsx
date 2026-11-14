import { useEffect, useMemo, useState } from 'react';
import { LayoutGrid, Utensils } from 'lucide-react';
import { clsx } from 'clsx';
import { assetUrl } from '../services/platform';
import { categories as categoryService, fallbackImage, type Category } from '../services/categories';
import type { Restaurant } from '../services/restaurant';

/** Restaurants that sell `category` (any of their categories, not only the main one). */
export const sells = (restaurant: Restaurant, category: string) =>
    (restaurant.categories?.length ? restaurant.categories : [restaurant.category]).includes(category);

/** The platform's categories, in the owner's order (fetched once per visit). */
let cached: Promise<Category[]> | null = null;
export const useCategories = () => {
    const [list, setList] = useState<Category[]>([]);
    useEffect(() => {
        let active = true;
        if (!cached) cached = categoryService.list().catch(() => { cached = null; return []; });
        cached.then(result => { if (active) setList(result); });
        return () => { active = false; };
    }, []);
    return list;
};

const Tile = ({ name, image, active, onClick }: { name: string; image: string | null | undefined; active: boolean; onClick: () => void }) => (
    <button
        onClick={onClick}
        aria-pressed={active}
        className="group flex flex-col items-center gap-2 w-[84px] flex-shrink-0 focus:outline-none"
    >
        <span className={clsx(
            "relative w-[72px] h-[72px] rounded-full overflow-hidden flex items-center justify-center bg-gray-900 border-2 transition-all",
            active ? "border-brand-500 ring-4 ring-brand-500/20" : "border-gray-800 group-hover:border-gray-600"
        )}>
            {image === undefined ? (
                <LayoutGrid size={26} className={active ? "text-brand-500" : "text-gray-400"} />
            ) : image ? (
                <img src={image} alt="" loading="lazy" className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" />
            ) : (
                <Utensils size={24} className="text-gray-500" />
            )}
        </span>
        {/* the label sits on the page background, never on the photo, so it reads in both themes */}
        <span className={clsx("text-xs font-bold text-center leading-tight line-clamp-2", active ? "text-brand-500" : "text-gray-300")}>
            {name}
        </span>
    </button>
);

/**
 * Round picture tiles for browsing by food type, like the food apps. Only
 * categories that some restaurant here actually sells are shown.
 */
const CategoryRail = ({ restaurants, active, onChange }: { restaurants: Restaurant[]; active: string; onChange: (name: string) => void }) => {
    const all = useCategories();
    const shown = useMemo(() => all.filter(c => restaurants.some(r => sells(r, c.name))), [all, restaurants]);
    if (shown.length === 0) return null;
    return (
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1 no-scrollbar" role="group" aria-label="Browse by food type">
            <Tile name="All" image={undefined} active={active === 'All'} onClick={() => onChange('All')} />
            {shown.map(category => (
                <Tile
                    key={category.id}
                    name={category.name}
                    image={category.image_url ? assetUrl(category.image_url) : fallbackImage(category.name)}
                    active={active === category.name}
                    onClick={() => onChange(active === category.name ? 'All' : category.name)}
                />
            ))}
        </div>
    );
};

export default CategoryRail;
