import api from "./api";
import type { Role } from "../utils/roles";

export interface RefreshTokenAdmin {
    id: string;
    created_at: string;
    last_used_at: string | null;
    expires_at: string;
    user_agent: string | null;
    ip_address: string | null;
    is_revoked: boolean;
}

export interface AdminUser {
    id: string;
    email: string;
    name: string;
    sur_name: string;
    role: Role;
    is_active: boolean;
}

export interface PaymentProvider {
    id: string;
    provider_name: string;
    display_name: string;
    public_key: string | null;
    secret_key: string | null;
    enabled: boolean;
    is_active: boolean;
    config: Record<string, any> | null;
}

export interface AdminUserUpdate {
    email?: string;
    is_active?: boolean;
    role?: Role;
}

export interface DriverCreate extends Partial<AdminUser> {
    email: string;
    name: string;
    sur_name: string;
    contact_number: string;
    password: string;
    vehicle_type: string;
    vehicle_number?: string;
}

export interface RestaurantCreate {
    name: string;
    address: string;
    description?: string;
    admin_email: string;
    admin_password: string;
    admin_name: string;
    admin_sur_name: string;
    admin_contact_number: string;
}

export interface SuperAdminCreate {
    email: string;
    name: string;
    sur_name: string;
    contact_number: string;
    password: string;
    role: Role;
}

export const adminService = {
    getUsers: async (): Promise<AdminUser[]> => {
        const res = await api.get("/admin/users");
        return res.data;
    },

    getUserById: async (userId: string): Promise<AdminUser> => {
        const res = await api.get(`/admin/users/${userId}`);
        return res.data;
    },

    updateUser: async (userId: string, data: AdminUserUpdate): Promise<AdminUser> => {
        const res = await api.patch(`/admin/users/${userId}`, data);
        return res.data;
    },

    deactivateUser: async (userId: string): Promise<{ message: string }> => {
        const res = await api.delete(`/admin/users/${userId}`);
        return res.data;
    },

    getUserSessions: async (userId: string): Promise<RefreshTokenAdmin[]> => {
        const res = await api.get(`/admin/users/${userId}/sessions`);
        return res.data;
    },

    revokeSession: async (tokenId: string): Promise<{ message: string }> => {
        const res = await api.post(`/admin/sessions/${tokenId}/revoke`);
        return res.data;
    },

    forceLogoutUser: async (userId: string): Promise<{ message: string }> => {
        const res = await api.post(`/admin/users/${userId}/logout-all`);
        return res.data;
    },

    createDriver: async (data: DriverCreate): Promise<AdminUser> => {
        const res = await api.post("/admin/drivers", data);
        return res.data;
    },

    createRestaurant: async (data: RestaurantCreate): Promise<any> => {
        const res = await api.post("/admin/restaurants", data);
        return res.data;
    },

    createSuperAdmin: async (data: SuperAdminCreate): Promise<AdminUser> => {
        const res = await api.post("/admin/users", data);
        return res.data;
    },

    getPaymentProviders: async (): Promise<PaymentProvider[]> => {
        const res = await api.get("/admin/payments/providers");
        return res.data;
    },

    updatePaymentProvider: async (providerId: string, data: Partial<PaymentProvider>): Promise<PaymentProvider> => {
        const res = await api.patch(`/admin/payments/providers/${providerId}`, data);
        return res.data;
    },

    createPaymentProvider: async (data: Partial<PaymentProvider>): Promise<PaymentProvider> => {
        const res = await api.post("/admin/payments/providers", data);
        return res.data;
    },

    deletePaymentProvider: async (providerId: string): Promise<any> => {
        const res = await api.delete(`/admin/payments/providers/${providerId}`);
        return res.data;
    }
};
