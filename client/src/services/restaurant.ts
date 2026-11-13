import api from "./api";

export interface Restaurant {
    id: string;
    name: string;
    description: string | null;
    address: string;
    is_active: boolean;
    logo_img_url: string | null;
}

export interface MenuItem {
    id: string;
    name: string;
    description: string | null;
    price: number;
    is_available: boolean;
    image_url?: string;
    restaurant_id?: string;
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

    deleteMenuItem: async (itemId: string): Promise<void> => {
        await api.delete(`/menus/${itemId}`);
    }
};
