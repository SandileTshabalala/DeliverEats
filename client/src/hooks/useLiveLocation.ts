import { useEffect, useRef, useState } from 'react';
import { socketBaseUrl } from './useOrderWebSocket';

export interface DriverPosition {
    lat: number;
    lng: number;
    /** when the phone took the reading (ms since 1970) */
    ts: number;
}

// Send at most this often: enough to follow a bike, light on data and battery
const SEND_EVERY_MS = 10_000;

export type SharingState = 'off' | 'starting' | 'sharing' | 'denied' | 'unsupported';

/**
 * Driver side: while `enabled`, read the phone's GPS and stream it to the
 * server. The server saves it (so the nearest driver gets new jobs) and relays
 * it to the customer whose order this driver is carrying.
 *
 * Browsers only allow location on HTTPS (or localhost).
 */
export const useShareDriverLocation = (driverId: string | undefined, enabled: boolean): SharingState => {
    const [state, setState] = useState<SharingState>('starting');
    const supported = typeof navigator !== 'undefined' && 'geolocation' in navigator;
    const active = enabled && !!driverId;

    useEffect(() => {
        if (!active || !supported) return;

        let socket: WebSocket | null = null;
        let stopped = false;
        let retry: ReturnType<typeof setTimeout> | undefined;
        let lastSent = 0;
        let latest: DriverPosition | null = null;

        const send = () => {
            if (latest && socket?.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify(latest));
                lastSent = Date.now();
            }
        };

        const connect = () => {
            const token = sessionStorage.getItem('access_token');
            if (stopped || !token) return;
            socket = new WebSocket(`${socketBaseUrl()}/ws/orders/driver/${driverId}?token=${encodeURIComponent(token)}`);
            socket.onopen = send;
            socket.onclose = () => {
                if (!stopped) retry = setTimeout(connect, 5000);
            };
        };

        connect();
        const watch = navigator.geolocation.watchPosition(
            position => {
                latest = { lat: position.coords.latitude, lng: position.coords.longitude, ts: position.timestamp };
                setState('sharing');
                if (Date.now() - lastSent >= SEND_EVERY_MS) send();
            },
            error => setState(error.code === error.PERMISSION_DENIED ? 'denied' : 'starting'),
            { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 },
        );
        // keep sending the last fix while standing still (the phone may not report a change)
        const heartbeat = setInterval(send, SEND_EVERY_MS * 3);

        return () => {
            stopped = true;
            navigator.geolocation.clearWatch(watch);
            clearInterval(heartbeat);
            if (retry) clearTimeout(retry);
            socket?.close();
            setState('starting'); // the next time sharing starts, it begins by looking for a fix
        };
    }, [driverId, active, supported]);

    if (!active) return 'off';
    if (!supported) return 'unsupported';
    return state;
};

/**
 * Customer side: the live position of the driver carrying `orderId`, or null
 * until the first reading arrives. `available` turns false when the server says
 * there is nothing to track (no driver yet, or the order is finished).
 */
export const useFollowDriver = (orderId: string, enabled: boolean) => {
    const [position, setPosition] = useState<DriverPosition | null>(null);
    const [available, setAvailable] = useState(true);
    const stoppedRef = useRef(false);

    useEffect(() => {
        if (!enabled) return;
        stoppedRef.current = false;
        let socket: WebSocket | null = null;
        let retry: ReturnType<typeof setTimeout> | undefined;

        const connect = () => {
            const token = sessionStorage.getItem('access_token');
            if (stoppedRef.current || !token) return;
            socket = new WebSocket(`${socketBaseUrl()}/ws/orders/order/${orderId}?token=${encodeURIComponent(token)}`);
            socket.onmessage = event => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'tracking_unavailable') {
                        setAvailable(false);
                        stoppedRef.current = true;
                        return;
                    }
                    if (typeof data.lat === 'number' && typeof data.lng === 'number') {
                        setAvailable(true);
                        setPosition({ lat: data.lat, lng: data.lng, ts: Number(data.ts) || Date.now() });
                    }
                } catch {
                    // ignore anything that is not a position
                }
            };
            socket.onclose = () => {
                if (!stoppedRef.current) retry = setTimeout(connect, 5000);
            };
        };

        connect();
        return () => {
            stoppedRef.current = true;
            if (retry) clearTimeout(retry);
            socket?.close();
        };
    }, [orderId, enabled]);

    return { position, available };
};

export const distanceKm = (a: { lat: number; lng: number }, b: { lat: number; lng: number }) => {
    const radians = (degrees: number) => (degrees * Math.PI) / 180;
    const dLat = radians(b.lat - a.lat);
    const dLng = radians(b.lng - a.lng);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(radians(a.lat)) * Math.cos(radians(b.lat)) * Math.sin(dLng / 2) ** 2;
    return 2 * 6371 * Math.asin(Math.sqrt(h));
};
