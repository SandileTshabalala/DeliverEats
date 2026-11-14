import { useCallback, useEffect, useState } from 'react';
import api from '../services/api';

export interface SavedAddress {
    id: string;
    formatted_address: string;
    suburb: string | null;
    city: string | null;
    is_default: boolean;
}

const KEY = 'delivery_address_id';
const EVENT = 'delivery-address-changed';

/** The address the customer picked in "Deliver to" (kept on this device). */
export const getChosenAddressId = (): string | null => {
    try {
        return localStorage.getItem(KEY);
    } catch {
        return null;
    }
};

export const chooseAddress = (id: string) => {
    try {
        localStorage.setItem(KEY, id);
    } catch {
        // not remembered, but still used for this visit
    }
    window.dispatchEvent(new CustomEvent(EVENT, { detail: id }));
};

/** Short label for an address: the suburb, or the first part of the street address. */
export const addressLabel = (address?: SavedAddress | null) =>
    address ? (address.suburb || address.formatted_address.split(',')[0]) : '';

/**
 * The customer's saved addresses and which one deliveries go to. Falls back to
 * the default address, then the first one.
 */
export const useDeliveryAddress = () => {
    const [addresses, setAddresses] = useState<SavedAddress[]>([]);
    const [chosenId, setChosenId] = useState<string | null>(getChosenAddressId);
    const [loading, setLoading] = useState(true);

    const reload = useCallback(async () => {
        try {
            const response = await api.get('/users/me');
            setAddresses(response.data.addresses ?? []);
        } catch {
            setAddresses([]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        let active = true;
        api.get('/users/me')
            .then(response => { if (active) setAddresses(response.data.addresses ?? []); })
            .catch(() => undefined)
            .finally(() => { if (active) setLoading(false); });
        const onChange = (event: Event) => setChosenId((event as CustomEvent<string>).detail);
        window.addEventListener(EVENT, onChange);
        return () => {
            active = false;
            window.removeEventListener(EVENT, onChange);
        };
    }, []);

    const chosen = addresses.find(a => a.id === chosenId)
        ?? addresses.find(a => a.is_default)
        ?? addresses[0]
        ?? null;

    return { addresses, chosen, choose: chooseAddress, loading, reload };
};
