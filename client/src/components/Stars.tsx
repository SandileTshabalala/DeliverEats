import { useState } from 'react';
import { Star } from 'lucide-react';
import { clsx } from 'clsx';

/** Read-only rating, e.g. "4.5 (12)". Shows "New" when nobody has rated yet. */
export const RatingBadge = ({ rating, count, className }: { rating?: number | null; count?: number; className?: string }) => (
    <span className={clsx("inline-flex items-center space-x-1", className)}>
        <Star size={12} className={rating ? "text-brand-500 fill-current" : "text-gray-500"} />
        {rating ? (
            <>
                <span className="text-xs font-black text-white">{rating.toFixed(1)}</span>
                {count ? <span className="text-[11px] text-gray-400">({count})</span> : null}
            </>
        ) : (
            <span className="text-xs font-bold text-gray-300">New</span>
        )}
    </span>
);

/** Stars to show a given score, or to pick one when `onChange` is passed. */
export const Stars = ({ value, onChange, size = 24 }: { value: number; onChange?: (value: number) => void; size?: number }) => {
    const [hover, setHover] = useState(0);
    const shown = hover || value;
    const labels = ['Bad', 'Not great', 'OK', 'Good', 'Excellent'];

    if (!onChange) {
        return (
            <span className="inline-flex" aria-label={`${value} out of 5`}>
                {[1, 2, 3, 4, 5].map(n => (
                    <Star key={n} size={size} className={n <= value ? "text-brand-500 fill-current" : "text-gray-700"} />
                ))}
            </span>
        );
    }

    return (
        <span className="inline-flex" role="radiogroup" aria-label="Your rating" onMouseLeave={() => setHover(0)}>
            {[1, 2, 3, 4, 5].map(n => (
                <button
                    key={n}
                    type="button"
                    role="radio"
                    aria-checked={value === n}
                    aria-label={`${n} star${n > 1 ? 's' : ''}: ${labels[n - 1]}`}
                    onClick={() => onChange(n)}
                    onMouseEnter={() => setHover(n)}
                    className="p-1"
                >
                    <Star size={size} className={n <= shown ? "text-brand-500 fill-current" : "text-gray-600"} />
                </button>
            ))}
        </span>
    );
};
