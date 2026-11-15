import api from "./api";

/**
 * Uploaded images are stored as a path on the API server (e.g.
 * "/api/v1/uploads/logos/x.webp"). Turn that into a full address the browser
 * can load. Full URLs (older logos hosted elsewhere) are returned unchanged.
 */
export const assetUrl = (path: string | null | undefined): string | undefined => {
    if (!path) return undefined;
    if (!path.startsWith('/')) return path;
    const apiUrl: string = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    return new URL(apiUrl, window.location.origin).origin + path;
};

export interface AdminStats {
    restaurants: { total: number; live: number };
    customers: number;
    drivers: number;
    orders: { today: number; this_month: number; all_time: number; last_7_days: { date: string; orders: number }[] };
    subscription_income: { this_month: string; all_time: string; monthly_recurring: string };
    subscriptions: Record<string, number>;
    subscriptions_enforced: boolean;
}

export interface AdminRestaurant {
    id: string;
    name: string;
    address: string;
    description: string | null;
    logo_img_url: string | null;
    is_active: boolean;
    is_live: boolean;
    owner_name: string | null;
    owner_email: string | null;
    owner_phone: string | null;
    subscription_status: string;
    plan_name: string | null;
    paid_until: string | null;
    orders_this_month: number;
}

export interface SystemStatus {
    environment: string;
    app_name: string;
    frontend_url: string;
    public_api_url: string;
    sms: { configured: boolean; sandbox: boolean; sender_id: string | null };
    email: { configured: boolean; from: string | null };
    payfast: { configured: boolean; sandbox: boolean };
    subscriptions: { enforced: boolean; grace_days: number };
    default_delivery_fee: number;
    secrets_encryption_key_set: boolean;
    legal_contact_set: boolean;
}

export interface BusinessDetails {
    business_name: string | null;
    business_address: string | null;
    support_email: string | null;
    support_phone: string | null;
    vat_number: string | null;
}

export interface RestaurantProfile {
    id: string;
    name: string;
    address: string;
    description: string | null;
    logo_img_url: string | null;
    is_active: boolean;
    category: string | null;
    accepting_orders: boolean;
    opens_at: string | null;
    closes_at: string | null;
    is_open: boolean;
    /** chosen categories, main one first */
    category_ids: string[];
    category_options: { id: string; name: string; image_url: string | null }[];
    max_categories: number;
    vat_number: string | null;
    /** customers call this to change or cancel an order; null = the owner's number */
    phone: string | null;
    owner_phone: string | null;
    menu_sections: string[];
}

export interface RestaurantReviews {
    rating: number | null;
    review_count: number;
    reviews: { id: string; order_id: string; rating: number; comment: string | null; created_at: string; customer_name: string }[];
}

export interface RestaurantStats {
    orders_today: number;
    orders_this_month: number;
    sales_today: string | number;
    sales_this_month: string | number;
    open_orders: number;
    menu_items_available: number;
}

export interface PublicStats {
    restaurants: number;
    orders_delivered: number;
}

export const platform = {
    adminStats: async (): Promise<AdminStats> => (await api.get("/admin/stats")).data,
    restaurants: async (): Promise<AdminRestaurant[]> => (await api.get("/admin/restaurants")).data,
    updateRestaurant: async (id: string, data: Partial<Pick<AdminRestaurant, 'name' | 'address' | 'description' | 'is_active'>>): Promise<AdminRestaurant> =>
        (await api.patch(`/admin/restaurants/${id}`, data)).data,
    system: async (): Promise<SystemStatus> => (await api.get("/admin/system")).data,
    business: async (): Promise<BusinessDetails> => (await api.get("/admin/business")).data,
    saveBusiness: async (data: Record<keyof BusinessDetails, string>): Promise<BusinessDetails> => (await api.put("/admin/business", data)).data,
    sendTestMessage: async (): Promise<{ sms: boolean; email: boolean }> => (await api.post("/notifications/test")).data,
    changePassword: async (current_password: string, new_password: string) =>
        (await api.post("/auth/change-password", { current_password, new_password })).data,
    publicStats: async (): Promise<PublicStats | null> => {
        try {
            return (await api.get("/stats/public")).data;
        } catch {
            return null; // decoration only: never break a page over it
        }
    },

    // a restaurant's own profile
    profile: async (): Promise<RestaurantProfile> => (await api.get("/manage/restaurant")).data,
    /** order of the menu sections customers see */
    saveMenuSections: async (sections: string[]): Promise<string[]> =>
        (await api.put("/manage/menu-sections", { sections })).data.menu_sections,
    updateProfile: async (data: Partial<Pick<RestaurantProfile, 'name' | 'address' | 'description' | 'category_ids' | 'accepting_orders' | 'opens_at' | 'closes_at' | 'vat_number' | 'phone'>>): Promise<RestaurantProfile> =>
        (await api.patch("/manage/restaurant", data)).data,
    uploadLogo: async (image: Blob): Promise<RestaurantProfile> => {
        const form = new FormData();
        form.append('file', image, 'logo');
        // let the browser set the multipart boundary itself
        return (await api.post("/manage/restaurant/logo", form, { headers: { 'Content-Type': undefined } })).data;
    },
    removeLogo: async (): Promise<RestaurantProfile> => (await api.delete("/manage/restaurant/logo")).data,
    restaurantStats: async (): Promise<RestaurantStats> => (await api.get("/manage/stats")).data,
    restaurantReviews: async (): Promise<RestaurantReviews> => (await api.get("/manage/reviews")).data,
};

/**
 * Shrink a photo in the browser before uploading: a phone photo is several MB,
 * a logo needs to be about 30 KB. Saves the owner's data and keeps the app fast.
 */
export const resizeImage = (file: File, maxSize = 512): Promise<Blob> =>
    new Promise((resolve, reject) => {
        const url = URL.createObjectURL(file);
        const image = new Image();
        image.onload = () => {
            URL.revokeObjectURL(url);
            const scale = Math.min(1, maxSize / Math.max(image.width, image.height));
            const canvas = document.createElement('canvas');
            canvas.width = Math.max(1, Math.round(image.width * scale));
            canvas.height = Math.max(1, Math.round(image.height * scale));
            const context = canvas.getContext('2d');
            if (!context) {
                reject(new Error('Could not read the image'));
                return;
            }
            context.drawImage(image, 0, 0, canvas.width, canvas.height);
            // JPEG is understood everywhere; white behind transparent PNGs
            const flattened = document.createElement('canvas');
            flattened.width = canvas.width;
            flattened.height = canvas.height;
            const flat = flattened.getContext('2d')!;
            flat.fillStyle = '#ffffff';
            flat.fillRect(0, 0, flattened.width, flattened.height);
            flat.drawImage(canvas, 0, 0);
            flattened.toBlob(blob => (blob ? resolve(blob) : reject(new Error('Could not prepare the image'))), 'image/jpeg', 0.85);
        };
        image.onerror = () => {
            URL.revokeObjectURL(url);
            reject(new Error('That file is not an image we can read'));
        };
        image.src = url;
    });
