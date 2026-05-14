import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import type { MenuItem } from '../services/restaurant';

interface CartItem extends MenuItem {
    quantity: number;
}

interface CartContextType {
    items: CartItem[];
    addToCart: (item: MenuItem) => void;
    removeFromCart: (itemId: string) => void;
    updateQuantity: (itemId: string, delta: number) => void;
    clearCart: () => void;
    totalPrice: number;
    totalItems: number;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export const CartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [items, setItems] = useState<CartItem[]>(() => {
        try {
            const savedCart = localStorage.getItem('lvovo_cart');
            return savedCart ? JSON.parse(savedCart) : [];
        } catch (e) {
            console.error("Failed to load cart", e);
            return [];
        }
    });

    useEffect(() => {
        localStorage.setItem('lvovo_cart', JSON.stringify(items));
    }, [items]);

    const addToCart = useCallback((item: MenuItem) => {
        setItems(prev => {
            const existing = prev.find(i => i.id === item.id);
            if (existing) {
                return prev.map(i => i.id === item.id ? { ...i, quantity: i.quantity + 1 } : i);
            }
            return [...prev, { ...item, quantity: 1 }];
        });
    }, []);

    const removeFromCart = useCallback((itemId: string) => {
        setItems(prev => prev.filter(i => i.id !== itemId));
    }, []);

    const updateQuantity = useCallback((itemId: string, delta: number) => {
        setItems(prev =>
            prev.map(i => {
                if (i.id === itemId) {
                    const newQty = Math.max(0, i.quantity + delta);
                    return { ...i, quantity: newQty };
                }
                return i;
            }).filter(i => i.quantity > 0)
        );
    }, []);

    const clearCart = useCallback(() => setItems([]), []);

    const totalPrice = items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);

    const value = useMemo(() => ({
        items,
        addToCart,
        removeFromCart,
        updateQuantity,
        clearCart,
        totalPrice,
        totalItems,
    }), [items, addToCart, removeFromCart, updateQuantity, clearCart, totalPrice, totalItems]);

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
