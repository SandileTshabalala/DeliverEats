import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import type { MenuItem } from '../services/restaurant';

interface CartItem extends MenuItem {
    quantity: number;
}

interface CartContextType {
    items: CartItem[];
    /** The one restaurant this cart belongs to (an order goes to a single kitchen). */
    restaurantId: string | null;
    addToCart: (item: MenuItem) => void;
    removeFromCart: (itemId: string) => void;
    updateQuantity: (itemId: string, delta: number) => void;
    clearCart: () => void;
    totalPrice: number;
    totalItems: number;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

const STORAGE_KEY = 'lvovo_cart';

/** Money maths in cents so 3 x R19.99 is R59.97 and not R59.970000000000006. */
const toCents = (price: number | string) => Math.round(Number(price) * 100);

export const formatRand = (amount: number | string) =>
    `R ${Number(amount).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const CartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [items, setItems] = useState<CartItem[]>(() => {
        try {
            const savedCart = localStorage.getItem(STORAGE_KEY);
            const parsed = savedCart ? JSON.parse(savedCart) : [];
            return Array.isArray(parsed) ? parsed : [];
        } catch (e) {
            console.error("Failed to load cart", e);
            return [];
        }
    });

    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    }, [items]);

    const addToCart = useCallback((item: MenuItem) => {
        // One order = one restaurant. Adding from a different restaurant starts
        // a new cart instead of silently mixing two kitchens (the order used to
        // be sent to whichever restaurant the first item came from).
        const currentRestaurant = items[0]?.restaurant_id;
        const switching = items.length > 0
            && !!item.restaurant_id
            && !!currentRestaurant
            && currentRestaurant !== item.restaurant_id;

        if (switching) {
            toast('Your cart was from another restaurant, so we started a new one.', { icon: '🛒' });
            setItems([{ ...item, quantity: 1 }]);
            return;
        }

        setItems(prev => {
            if (prev.some(i => i.id === item.id)) {
                return prev.map(i => i.id === item.id ? { ...i, quantity: i.quantity + 1 } : i);
            }
            return [...prev, { ...item, quantity: 1 }];
        });
    }, [items]);

    const removeFromCart = useCallback((itemId: string) => {
        setItems(prev => prev.filter(i => i.id !== itemId));
    }, []);

    const updateQuantity = useCallback((itemId: string, delta: number) => {
        setItems(prev =>
            prev.map(i => {
                if (i.id === itemId) {
                    const newQty = Math.min(50, Math.max(0, i.quantity + delta));
                    return { ...i, quantity: newQty };
                }
                return i;
            }).filter(i => i.quantity > 0)
        );
    }, []);

    const clearCart = useCallback(() => setItems([]), []);

    const totalPrice = items.reduce((sum, item) => sum + toCents(item.price) * item.quantity, 0) / 100;
    const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);
    const restaurantId = items[0]?.restaurant_id ?? null;

    const value = useMemo(() => ({
        items,
        restaurantId,
        addToCart,
        removeFromCart,
        updateQuantity,
        clearCart,
        totalPrice,
        totalItems,
    }), [items, restaurantId, addToCart, removeFromCart, updateQuantity, clearCart, totalPrice, totalItems]);

    return (
        <CartContext.Provider value={value}>
            {children}
        </CartContext.Provider>
    );
};

export const useCart = () => {
    const context = useContext(CartContext);
    if (context === undefined) {
        throw new Error('useCart must be used within a CartProvider');
    }
    return context;
};
