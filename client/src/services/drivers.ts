import api from "./api";

export interface DriverProfile {
    id: string;
    vehicle_type: string;
    vehicle_number: string | null;
    is_available: boolean;
}

export const driverService = {
    getProfile: async (): Promise<DriverProfile> => {
        const res = await api.get("/drivers/profile");
        return res.data;
    },

    updateProfile: async (data: { vehicle_type: string; vehicle_number?: string }): Promise<DriverProfile> => {
        const res = await api.post("/drivers/profile", data);
        return res.data;
    },

    toggleAvailability: async (available: boolean): Promise<{ is_available: boolean }> => {
        const res = await api.post(`/drivers/availability?available=${available}`);
        return res.data;
    },

    getJobs: async (): Promise<any[]> => {
        const res = await api.get("/orders/driver/jobs");
        return res.data;
    },

    updateOrderStatus: async (orderId: string, status: string): Promise<any> => {
        const res = await api.post(`/drivers/orders/${orderId}/status`, null, {
            params: { status }
        });
        return res.data;
    },

    getStats: async (): Promise<any> => {
        const res = await api.get("/drivers/stats");
        return res.data;
    },

    getHistory: async (): Promise<any[]> => {
        const res = await api.get("/orders/driver/history");
        return res.data;
    }
};
