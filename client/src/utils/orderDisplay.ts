/**
 * How orders are shown everywhere (restaurant, driver, customer, admin), so
 * the same order reads the same on every screen.
 */

/**
 * The server stores times in UTC and sends them WITHOUT a timezone
 * ("2026-11-14T13:16:25"). Read as-is, the browser takes that as local time
 * and every time shows 2 hours early in South Africa. Times that already carry
 * a zone ("...Z", "+00:00") and plain dates ("2026-11-14") are left alone.
 */
export const serverDate = (iso: string | null | undefined): Date => {
    if (!iso) return new Date(NaN);
    const hasZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(iso);
    return new Date(iso.includes('T') && !hasZone ? `${iso}Z` : iso);
};

const timeOf = (date: Date) => date.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' });

/** "Today, 14:05" / "Yesterday, 09:30" / "12 Nov, 18:20" */
export const when = (iso: string | null | undefined): string => {
    const date = serverDate(iso);
    if (Number.isNaN(date.getTime())) return '';
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    if (date.toDateString() === today.toDateString()) return `Today, ${timeOf(date)}`;
    if (date.toDateString() === yesterday.toDateString()) return `Yesterday, ${timeOf(date)}`;
    const sameYear = date.getFullYear() === today.getFullYear();
    return `${date.toLocaleDateString('en-ZA', { day: 'numeric', month: 'short', ...(sameYear ? {} : { year: 'numeric' }) })}, ${timeOf(date)}`;
};

export const ORDER_STATUS: Record<string, { label: string; style: string }> = {
    pending: { label: 'New', style: 'bg-brand-500/10 text-brand-500 border-brand-500/20' },
    accepted: { label: 'Accepted', style: 'bg-blue-500/10 text-blue-500 border-blue-500/20' },
    preparing: { label: 'Preparing', style: 'bg-blue-500/10 text-blue-500 border-blue-500/20' },
    waiting_for_driver: { label: 'Waiting for driver', style: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/25' },
    ready: { label: 'Ready', style: 'bg-green-500/10 text-green-600 border-green-500/25' },
    picked_up: { label: 'On the way', style: 'bg-green-500/10 text-green-600 border-green-500/25' },
    delivered: { label: 'Delivered', style: 'bg-gray-800 text-gray-400 border-gray-700' },
    cancelled: { label: 'Cancelled', style: 'bg-red-500/10 text-red-500 border-red-500/20' },
};

export const orderStatus = (status: string) =>
    ORDER_STATUS[status] ?? { label: status.replace(/_/g, ' '), style: 'bg-gray-800 text-gray-400 border-gray-700' };

/** "1 item" / "3 items" */
export const itemCount = (n: number | null | undefined) => `${n ?? 0} ${(n ?? 0) === 1 ? 'item' : 'items'}`;
