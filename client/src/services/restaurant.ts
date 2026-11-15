import api from "./api";
import type { OptionGroup } from "../utils/menu";

export interface Restaurant {
    id: string;
    name: string;
    description: string | null;
    address: string;
    is_active: boolean;
    logo_img_url: string | null;
    category?: string | null;
    /** every food type it sells, main one first */
    categories?: string[];
    /** open right now: the owner's switch is on and we are inside the opening hours */
    is_open?: boolean;
    accepting_orders?: boolean;
    opens_at?: string | null;
    closes_at?: string | null;
    rating?: number | null;
    review_count?: number;
    delivery_fee_from?: string | null;
    delivery_per_km?: boolean;
    free_delivery_over?: string | null;
    /** order of the menu sections, as the restaurant arranged them */
    menu_sections?: string[] | null;
}

export interface MenuItem {
    id: string;
    name: string;
    description: string | null;
    price: number;
    is_available: boolean;
    image_url?: string;
    restaurant_id?: string;
    /** kept on cart items so the cart bar can say where the order is from */
    restaurant_name?: string;
    /** "Mains", "Drinks"... (empty = the first, unnamed section) */
    section?: string | null;
    /** choices the customer makes: spice level, extras... */
    options?: OptionGroup[];
}

export const restaurantService = {
    listRestaurants: async (): Promise<Restaurant[]> => {
        const res = await api.get("/restaurant/");
        return res.data;
    },

    getRestaurant: async (restaurantId: string): Promise<Restaurant | null> => {
        try {
            const res = await api.get(`/restaurant/${restaurantId}`);
            return res.data;
        } catch {
            return null;
        }
    },

    /** The restaurant that belongs to the signed-in restaurant admin. */
    getMyRestaurant: async (): Promise<Restaurant> => {
        const res = await api.get("/restaurant/mine");
        return res.data;
    },

    /** Owner view of the menu: includes items that are switched off. */
    getManageMenu: async (restaurantId: string): Promise<MenuItem[]> => {
        const res = await api.get(`/menus/restaurant/${restaurantId}/manage`);
        return res.data;
    },

    getMenu: async (restaurantId: string): Promise<MenuItem[]> => {
        const res = await api.get(`/menus/restaurant/${restaurantId}`);
        return res.data;
    },

    createMenuItem: async (restaurantId: string, data: any): Promise<MenuItem> => {
        const res = await api.post(`/menus/restaurant/${restaurantId}/items`, data);
        return res.data;
    },

    updateMenuItem: async (itemId: string, data: any): Promise<MenuItem> => {
        const res = await api.patch(`/menus/${itemId}`, data);
        return res.data;
    },

    /** Upload a photo for a menu item (resize it first with resizeImage). */
    uploadItemImage: async (itemId: string, image: Blob): Promise<MenuItem> => {
        const form = new FormData();
        form.append('file', image, 'photo');
        const res = await api.post(`/menus/${itemId}/image`, form, { headers: { 'Content-Type': undefined } });
        return res.data;
    },

    deleteMenuItem: async (itemId: string): Promise<void> => {
        await api.delete(`/menus/${itemId}`);
    }
};
