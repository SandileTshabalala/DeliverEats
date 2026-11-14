import api from './api';
import images from '../constant/images';

export interface Category {
    id: string;
    name: string;
    image_url: string | null;
}

export interface AdminCategory extends Category {
    is_active: boolean;
    sort_order: number;
    restaurant_count: number;
}

const upload = (image: Blob) => {
    const form = new FormData();
    form.append('file', image, 'category');
    return form;
};

export const categories = {
    list: async (): Promise<Category[]> => (await api.get('/categories')).data,

    // platform owner
    all: async (): Promise<AdminCategory[]> => (await api.get('/admin/categories')).data,
    create: async (name: string): Promise<AdminCategory> => (await api.post('/admin/categories', { name })).data,
    update: async (id: string, data: { name?: string; is_active?: boolean }): Promise<AdminCategory> =>
        (await api.patch(`/admin/categories/${id}`, data)).data,
    reorder: async (ids: string[]): Promise<AdminCategory[]> => (await api.put('/admin/categories/order', { ids })).data,
    uploadImage: async (id: string, image: Blob): Promise<AdminCategory> =>
        (await api.post(`/admin/categories/${id}/image`, upload(image), { headers: { 'Content-Type': undefined } })).data,
    removeImage: async (id: string): Promise<AdminCategory> => (await api.delete(`/admin/categories/${id}/image`)).data,
    remove: async (id: string) => api.delete(`/admin/categories/${id}`),
};

/**
 * Stock photo shown until the platform owner uploads a picture for the category.
 * Matched on words in the name, so renamed categories still get a sensible one.
 */
export const fallbackImage = (name: string): string | null => {
    const n = name.toLowerCase();
    if (/shisa|braai|grill|meat/.test(n)) return images.shisanyama;
    if (/chicken|wings/.test(n)) return images.chicken;
    if (/burger|fast food|kota|bunny|chips/.test(n)) return images.burgers;
    if (/pizza/.test(n)) return images.pizza;
    if (/rib/.test(n)) return images.ribsAndChips;
    if (/tradition|african|kasi|home|plate|meal/.test(n)) return images.plates;
    return null;
};
