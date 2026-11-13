import api from "./api";

export interface OrderItem {
    menu_item_id: string;
    quantity: number;
    price: number;
}

export interface Order {
    id: string;
    customer_id: string;
    restaurant_id: string;
    driver_id: string | null;
    status: string;
    total: number;
    created_at: string;
    items: any[];
    total_amount?: number;
    restaurant_name?: string;
    delivery_address?: string | null;
    payment_status?: string;
    payment_method?: string | null;
    customer?: OrderPerson;
    driver?: (OrderPerson & { vehicle_type?: string; vehicle_number?: string | null }) | null;
}

export interface OrderPerson {
    id: string;
    name?: string | null;
    sur_name?: string | null;
    contact_number?: string | null;
}

/**
 * The order number people read out: the same 8 characters on every screen and
 * in every SMS, so a customer, the kitchen and the driver can match an order.
 */
export const orderRef = (id?: string | null) => (id ? `#${id.slice(0, 8).toUpperCase()}` : '#');

export const fullName = (person?: OrderPerson | null) =>
    person ? [person.name, person.sur_name].filter(Boolean).join(' ') : '';

/** tel: link target, keeping only what a dialler understands */
export const phoneHref = (number?: string | null) => `tel:${(number ?? '').replace(/[^\d+]/g, '')}`;

export const orderService = {
    createOrder: async (data: { restaurant_id: string; address_id?: string; items: { menu_item_id: string; quantity: number }[] }): Promise<Order> => {
        const res = await api.post("/orders/", data);
        return res.data;
    },

    acceptOrder: async (orderId: string): Promise<Order> => {
        const res = await api.post(`/orders/${orderId}/accept`);
        return res.data;
    },

    updateStatus: async (orderId: string, status: string): Promise<{ order_id: string; status: string }> => {
        const res = await api.post(`/orders/${orderId}/status`, null, {
            params: { status }
        });
        return res.data;
    },

    getRestaurantOrders: async (): Promise<Order[]> => {
        const res = await api.get("/restaurant/orders");
        return res.data;
    },

    getMyOrders: async (): Promise<Order[]> => {
        const res = await api.get("/orders/my");
        return res.data;
    }
};
