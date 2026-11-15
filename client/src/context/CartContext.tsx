import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import type { MenuItem } from '../services/restaurant';
import { lineKey, pickedOptions, unitPrice, type PickedOption } from '../utils/menu';

/**
 * One line of the cart: a dish and the choices picked for it. `price` is the
 * price of one INCLUDING the extras; `key` tells "Kota, hot" from "Kota, mild".
 */
export interface CartItem extends MenuItem {
    quantity: number;
    key: string;
    /** ids of the choices picked (sent to the server, which prices them) */
    choice_ids?: string[];
    /** the same picks, readable, for the cart screen */
    picked?: PickedOption[];
}

interface CartContextType {
    items: CartItem[];
    /** The one restaurant this cart belongs to (an order goes to a single kitchen). */
    restaurantId: string | null;
    /** add `quantity` of a dish with the given choices (ids) */
    addToCart: (item: MenuItem, choiceIds?: string[], quantity?: number) => void;
    /** by line key (a dish without choices: its id) */
    removeFromCart: (key: string) => void;
    updateQuantity: (key: string, delta: number) => void;
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
            // carts saved before choices existed have no line key
            return Array.isArray(parsed) ? parsed.map((line: CartItem) => ({ ...line, key: line.key ?? line.id })) : [];
        } catch (e) {
            console.error("Failed to load cart", e);
            return [];
        }
    });

    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    }, [items]);

    const addToCart = useCallback((item: MenuItem, choiceIds: string[] = [], quantity = 1) => {
        const line: CartItem = {
            ...item,
            key: lineKey(item.id, choiceIds),
            choice_ids: choiceIds,
            picked: pickedOptions(item.options, choiceIds),
            price: unitPrice(item.price, item.options, choiceIds),
            quantity: Math.min(50, Math.max(1, quantity)),
        };
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
            setItems([line]);
            return;
        }

        setItems(prev => {
            if (prev.some(i => i.key === line.key)) {
                return prev.map(i => i.key === line.key ? { ...i, quantity: Math.min(50, i.quantity + line.quantity) } : i);
            }
            return [...prev, line];
        });
    }, [items]);

    const removeFromCart = useCallback((key: string) => {
        setItems(prev => prev.filter(i => i.key !== key));
    }, []);

    const updateQuantity = useCallback((key: string, delta: number) => {
        setItems(prev =>
            prev.map(i => {
                if (i.key === key) {
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
