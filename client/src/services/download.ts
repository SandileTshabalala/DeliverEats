import { toast } from 'react-hot-toast';
import api from './api';

/** File name the server chose (Content-Disposition), or a fallback. */
const fileNameFrom = (header: string | undefined, fallback: string) => {
    const match = /filename="?([^";]+)"?/i.exec(header ?? '');
    return match ? match[1] : fallback;
};

/**
 * Download a report or invoice. It goes through the API client (not a plain
 * link) because downloads need the signed-in user's token.
 */
export const downloadFile = async (path: string, params: Record<string, string> = {}, fallbackName = 'download') => {
    try {
        const response = await api.get(path, { params, responseType: 'blob' });
        const url = URL.createObjectURL(response.data as Blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = fileNameFrom(response.headers['content-disposition'], fallbackName);
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 10_000);
        return true;
    } catch (error: any) {
        // the error body is a Blob too: read the server's message out of it
        let message = 'The download failed. Please try again.';
        const data = error?.response?.data;
        if (data instanceof Blob) {
            try {
                const detail = JSON.parse(await data.text()).detail;
                if (typeof detail === 'string') message = detail;
            } catch {
                // not JSON: keep the general message
            }
        }
        toast.error(message);
        return false;
    }
};

const iso = (value: Date) => {
    const local = new Date(value.getTime() - value.getTimezoneOffset() * 60_000);
    return local.toISOString().slice(0, 10);
};

export interface Period {
    from: string;
    to: string;
}

/** Quick choices for report periods. */
export const PERIODS: { label: string; make: () => Period }[] = [
    {
        label: 'This month', make: () => {
            const now = new Date();
            return { from: iso(new Date(now.getFullYear(), now.getMonth(), 1)), to: iso(now) };
        },
    },
    {
        label: 'Last month', make: () => {
            const now = new Date();
            return { from: iso(new Date(now.getFullYear(), now.getMonth() - 1, 1)), to: iso(new Date(now.getFullYear(), now.getMonth(), 0)) };
        },
    },
    {
        label: 'Last 7 days', make: () => {
            const now = new Date();
            return { from: iso(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6)), to: iso(now) };
        },
    },
    {
        label: 'This year', make: () => {
            const now = new Date();
            return { from: iso(new Date(now.getFullYear(), 0, 1)), to: iso(now) };
        },
    },
];
