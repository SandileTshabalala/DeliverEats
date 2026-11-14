import api from "./api";

import { serverDate } from '../utils/orderDisplay';
export interface Plan {
    id: string;
    name: string;
    description: string | null;
    price: string;
    interval_months: 1 | 3 | 6 | 12;
    trial_days: number;
    max_orders_per_month: number | null;
    is_active: boolean;
    sort_order: number;
}

export type PlanInput = Omit<Plan, 'id'>;

export type SubscriptionStatus = 'none' | 'trialing' | 'active' | 'past_due' | 'expired' | 'suspended' | 'cancelled';

export interface Subscription {
    restaurant_id: string;
    restaurant_name: string;
    status: SubscriptionStatus;
    is_live: boolean;
    enforced: boolean;
    grace_days: number;
    plan: Plan | null;
    current_period_end: string | null;
    auto_renews: boolean;
    /** a PayFast debit order is running: another checkout would charge twice */
    recurring_active?: boolean;
    orders_this_month: number;
    orders_limit: number | null;
    limit_reached: boolean;
    note: string | null;
}

export interface BillingOverview {
    subscription: Subscription;
    plans: Plan[];
    online_payment_available: boolean;
}

export interface SubscriptionPayment {
    id: string;
    amount: string;
    status: string;
    method: string;
    reference: string | null;
    invoice_number?: number | null;
    created_at: string;
}

export interface PaymentSettings {
    accepts_cash: boolean;
    accepts_card_machine: boolean;
    payfast_enabled: boolean;
    payfast_merchant_id: string | null;
    payfast_merchant_key: string | null;
    payfast_passphrase: string | null;
    payfast_sandbox: boolean;
    ozow_enabled: boolean;
    ozow_site_code: string | null;
    ozow_client_id: string | null;
    ozow_client_secret: string | null;
    ozow_sandbox: boolean;
    peach_enabled: boolean;
    peach_entity_id: string | null;
    peach_secret_token: string | null;
    peach_sandbox: boolean;
}

export interface DeliverySettings {
    base_fee: string;
    per_km_fee: string;
    free_delivery_over: string | null;
    max_distance_km: number | null;
    latitude: number | null;
    longitude: number | null;
}

export interface OrderQuote {
    subtotal: string;
    delivery_fee: string;
    total: string;
    distance_km: number | null;
    free_delivery: boolean;
    free_delivery_over: string | null;
}

export interface TeamMember {
    id: string;
    email: string;
    name: string;
    sur_name: string;
    contact_number: string;
    is_active: boolean;
    is_owner: boolean;
}

export interface TeamDriver extends TeamMember {
    vehicle_type: string;
    vehicle_number: string | null;
    is_available: boolean;
}

export interface NewTeamMember {
    email: string;
    password: string;
    name: string;
    sur_name: string;
    contact_number: string;
    vehicle_type?: string;
    vehicle_number?: string;
}

export const STATUS_LABEL: Record<SubscriptionStatus, string> = {
    none: 'No plan',
    trialing: 'Free trial',
    active: 'Active',
    past_due: 'Payment overdue',
    expired: 'Expired',
    suspended: 'Suspended',
    cancelled: 'Cancelled',
};

export const STATUS_STYLE: Record<SubscriptionStatus, string> = {
    none: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
    trialing: 'bg-brand-500/10 text-brand-400 border-brand-500/20',
    active: 'bg-green-500/10 text-green-500 border-green-500/20',
    past_due: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    expired: 'bg-red-500/10 text-red-500 border-red-500/20',
    suspended: 'bg-red-500/10 text-red-500 border-red-500/20',
    cancelled: 'bg-gray-500/10 text-gray-400 border-gray-500/20',
};

export const intervalLabel = (months: number) =>
    months === 1 ? 'month' : months === 12 ? 'year' : `${months} months`;

export const formatDate = (iso: string | null) =>
    iso ? serverDate(iso).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', year: 'numeric' }) : '-';

/** Readable message from an API error. */
export const errorMessage = (error: any, fallback: string) => {
    const detail = error?.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return `${detail[0].loc?.slice(-1)[0] ?? 'Field'}: ${detail[0].msg}`;
    return fallback;
};

// ---- platform owner
export const adminBilling = {
    plans: async (): Promise<Plan[]> => (await api.get("/admin/billing/plans")).data,
    createPlan: async (data: PlanInput): Promise<Plan> => (await api.post("/admin/billing/plans", data)).data,
    updatePlan: async (id: string, data: Partial<PlanInput>): Promise<Plan> => (await api.patch(`/admin/billing/plans/${id}`, data)).data,
    deletePlan: async (id: string): Promise<{ message: string }> => (await api.delete(`/admin/billing/plans/${id}`)).data,
    subscriptions: async (): Promise<Subscription[]> => (await api.get("/admin/billing/subscriptions")).data,
    setSubscription: async (restaurantId: string, data: { plan_id?: string; status?: string; current_period_end?: string; note?: string; stop_recurring?: boolean }): Promise<Subscription> =>
        (await api.put(`/admin/billing/restaurants/${restaurantId}/subscription`, data)).data,
    recordPayment: async (restaurantId: string, data: { plan_id: string; amount?: string; note?: string }): Promise<Subscription> =>
        (await api.post(`/admin/billing/restaurants/${restaurantId}/payments`, data)).data,
};

// ---- a restaurant managing itself (the server scopes everything to the signed-in restaurant)
export const manage = {
    billing: async (): Promise<BillingOverview> => (await api.get("/manage/billing")).data,
    subscribe: async (planId: string): Promise<{ action: 'trial_started' | 'activated' | 'checkout'; checkout_url: string | null; checkout_fields: Record<string, string> | null }> =>
        (await api.post("/manage/billing/subscribe", { plan_id: planId })).data,
    billingHistory: async (): Promise<SubscriptionPayment[]> => (await api.get("/manage/billing/payments")).data,
    paymentSettings: async (): Promise<PaymentSettings> => (await api.get("/manage/payment-settings")).data,
    savePaymentSettings: async (data: Partial<PaymentSettings>): Promise<PaymentSettings> => (await api.put("/manage/payment-settings", data)).data,
    deliverySettings: async (): Promise<DeliverySettings> => (await api.get("/manage/delivery-settings")).data,
    saveDeliverySettings: async (data: Record<string, string | number | null>): Promise<DeliverySettings> => (await api.put("/manage/delivery-settings", data)).data,
    drivers: async (): Promise<TeamDriver[]> => (await api.get("/manage/drivers")).data,
    addDriver: async (data: NewTeamMember): Promise<TeamDriver> => (await api.post("/manage/drivers", data)).data,
    removeDriver: async (id: string) => (await api.delete(`/manage/drivers/${id}`)).data,
    staff: async (): Promise<TeamMember[]> => (await api.get("/manage/staff")).data,
    addStaff: async (data: NewTeamMember): Promise<TeamMember> => (await api.post("/manage/staff", data)).data,
    removeStaff: async (id: string) => (await api.delete(`/manage/staff/${id}`)).data,
};
