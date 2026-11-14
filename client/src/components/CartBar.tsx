import { Link, useLocation } from 'react-router-dom';
import { ShoppingBag } from 'lucide-react';
import { formatRand, useCart } from '../context/CartContext';

/** Floating "View cart" bar while browsing, like the big food apps. */
const CartBar = () => {
    const { items, totalItems, totalPrice } = useCart();
    const { pathname } = useLocation();
    if (totalItems === 0 || pathname.startsWith('/customer/cart')) return null;
    const from = items[0]?.restaurant_name;

    return (
        <div className="fixed bottom-4 inset-x-0 z-40 px-4 pointer-events-none">
            <Link
                to="/customer/cart"
                className="pointer-events-auto mx-auto max-w-lg flex items-center justify-between gap-4 px-5 py-4 bg-brand-600 hover:bg-brand-500 text-white rounded-2xl shadow-2xl shadow-brand-900/40 transition-colors"
            >
                <span className="flex items-center gap-3 min-w-0">
                    <span className="relative flex-shrink-0">
                        <ShoppingBag size={22} />
                        <span className="absolute -top-2 -right-2 min-w-[18px] h-[18px] px-1 bg-gray-950 text-brand-500 text-[10px] font-black rounded-full flex items-center justify-center">
                            {totalItems}
                        </span>
                    </span>
                    <span className="min-w-0">
                        <span className="block font-black">View cart</span>
                        {from && <span className="block text-xs text-white/80 truncate">from {from}</span>}
                    </span>
                </span>
                <span className="font-black whitespace-nowrap">{formatRand(totalPrice)}</span>
            </Link>
        </div>
    );
};

export default CartBar;
