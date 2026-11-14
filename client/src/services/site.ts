import { useEffect, useState } from 'react';
import api from './api';

export interface SiteInfo {
    app_name: string;
    business_name: string | null;
    business_address: string | null;
    support_email: string | null;
    support_phone: string | null;
    categories: string[];
}

let cached: Promise<SiteInfo | null> | null = null;

/** Who runs the platform and the list of restaurant categories. Fetched once per visit. */
export const loadSite = (): Promise<SiteInfo | null> => {
    if (!cached) {
        cached = api.get('/site').then(res => res.data as SiteInfo).catch(() => {
            cached = null; // try again next time
            return null;
        });
    }
    return cached;
};

export const useSite = () => {
    const [site, setSite] = useState<SiteInfo | null>(null);
    useEffect(() => {
        let active = true;
        loadSite().then(result => { if (active) setSite(result); });
        return () => { active = false; };
    }, []);
    return site;
};

export interface InboxItem {
    id: string;
    title: string;
    message: string;
    link: string | null;
    created_at: string;
}

export const inbox = {
    get: async (): Promise<{ unread: number; items: InboxItem[] }> => (await api.get('/notifications')).data,
    markRead: async () => (await api.post('/notifications/read')).data,
};

/** "5 min ago", "yesterday", "3 Nov" */
export const timeAgo = (iso: string) => {
    const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
    if (seconds < 172800) return 'yesterday';
    return new Date(iso).toLocaleDateString('en-ZA', { day: 'numeric', month: 'short' });
};
