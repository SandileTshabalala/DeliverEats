import { useEffect, useRef } from 'react';

export interface OrderSocketMessage {
    type: 'new_order' | 'order_updated' | 'auth_success' | 'auth_error';
    order_id?: string;
    status?: string;
    restaurant_id?: string;
    driver_id?: string;
    payment_status?: string;
}

/** ws(s)://host/api/v1 derived from the same VITE_API_URL the REST client uses. */
const socketBaseUrl = (): string => {
    const apiUrl: string = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    const absolute = new URL(apiUrl, window.location.origin);
    absolute.protocol = absolute.protocol === 'https:' ? 'wss:' : 'ws:';
    return absolute.toString().replace(/\/$/, '');
};

/**
 * Live order events for the signed-in user.
 *
 * The socket is opened once per mounted component. The latest `onMessage` is
 * kept in a ref, so passing a new inline function on every render does NOT
 * tear the connection down and reopen it (the previous version did, and also
 * reconnected after being closed on purpose, leaking sockets).
 */
export const useOrderWebSocket = (onMessage: (message: OrderSocketMessage) => void) => {
    const handler = useRef(onMessage);
    useEffect(() => {
        handler.current = onMessage;
    });

    useEffect(() => {
        let socket: WebSocket | null = null;
        let retryTimer: ReturnType<typeof setTimeout> | undefined;
        let stopped = false;
        let attempt = 0;

        const connect = () => {
            if (stopped) return;
            const token = sessionStorage.getItem('access_token');
            if (!token) return;

            socket = new WebSocket(`${socketBaseUrl()}/ws/orders/updates?token=${encodeURIComponent(token)}`);

            socket.onopen = () => {
                attempt = 0;
            };

            socket.onmessage = (event) => {
                try {
                    const message: OrderSocketMessage = JSON.parse(event.data);
                    if (message.type === 'auth_error') {
                        // Token expired: the next REST call refreshes it, then we retry
                        return;
                    }
                    handler.current(message);
                } catch {
                    // ignore anything that is not JSON
                }
            };

            socket.onclose = () => {
                if (stopped) return;
                // Back off: 2s, 4s, 8s ... capped at 30s
                attempt += 1;
                retryTimer = setTimeout(connect, Math.min(30000, 1000 * 2 ** attempt));
            };
        };

        connect();

        return () => {
            stopped = true;
            if (retryTimer) clearTimeout(retryTimer);
            socket?.close();
        };
    }, []);
};
