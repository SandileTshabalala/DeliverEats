import { useEffect, useRef, useCallback } from 'react';

interface WebSocketMessage {
    type: 'new_order' | 'order_updated';
    order_id: string;
    status?: string;
    restaurant_id?: string;
    driver_id?: string;
}

export const useOrderWebSocket = (onMessage: (message: WebSocketMessage) => void) => {
    const ws = useRef<WebSocket | null>(null);
    const reconnectTimeout = useRef<any>(null);

    const connect = useCallback(() => {
        try {
            // Get token from sessionStorage
            const token = sessionStorage.getItem('access_token');
            if (!token) {
                console.log('No access token found, skipping WebSocket connection');
                return;
            }

            // Connect to WebSocket endpoint with token as query param
            const wsUrl = `ws://localhost:8000/api/v1/ws/orders/updates?token=${token}`;
            ws.current = new WebSocket(wsUrl);

            ws.current.onopen = () => {
                console.log('WebSocket connected');
            };

            ws.current.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    onMessage(message);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            ws.current.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            ws.current.onclose = () => {
                console.log('WebSocket disconnected, reconnecting in 3s...');
                // Attempt to reconnect after 3 seconds
                reconnectTimeout.current = setTimeout(() => {
                    connect();
                }, 3000);
            };
        } catch (error) {
            console.error('Failed to connect to WebSocket:', error);
        }
    }, [onMessage]);

    useEffect(() => {
        connect();

        return () => {
            if (reconnectTimeout.current) {
                clearTimeout(reconnectTimeout.current);
            }
            if (ws.current) {
                ws.current.close();
            }
        };
    }, [connect]);

    return ws;
};
