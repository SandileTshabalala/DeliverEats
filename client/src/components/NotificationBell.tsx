import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { clsx } from 'clsx';
import { inbox, timeAgo } from '../services/site';
import type { InboxItem } from '../services/site';

const REFRESH_MS = 45_000;

/**
 * The bell in the header: the same messages people get by SMS / email
 * (new order, driver assigned, on the way, plan reminders ...), kept in the app.
 */
const NotificationBell = () => {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const [unread, setUnread] = useState(0);
    const [items, setItems] = useState<InboxItem[]>([]);
    const [loaded, setLoaded] = useState(false);
    const panel = useRef<HTMLDivElement>(null);

    const refresh = useCallback(async () => {
        try {
            const data = await inbox.get();
            setUnread(data.unread);
            setItems(data.items);
        } catch {
            // the bell is a convenience: never show an error for it
        } finally {
            setLoaded(true);
        }
    }, []);

    useEffect(() => {
        let active = true;
        const load = () => {
            inbox.get()
                .then(data => {
                    if (!active) return;
                    setUnread(data.unread);
                    setItems(data.items);
                })
                .catch(() => undefined)
                .finally(() => { if (active) setLoaded(true); });
        };
        load();
        const timer = setInterval(() => {
            if (document.visibilityState === 'visible') load();
        }, REFRESH_MS);
        window.addEventListener('focus', load);
        return () => {
            active = false;
            clearInterval(timer);
            window.removeEventListener('focus', load);
        };
    }, []);

    useEffect(() => {
        if (!open) return;
        const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [open]);

    const toggle = async () => {
        const opening = !open;
        setOpen(opening);
        if (opening) {
            await refresh();
            if (unread > 0) {
                setUnread(0);
                inbox.markRead().catch(() => undefined);
            }
        }
    };

    const follow = (item: InboxItem) => {
        setOpen(false);
        if (item.link) navigate(item.link);
    };

    return (
        <div className="relative" ref={panel}>
            <button
                onClick={toggle}
                aria-label={unread > 0 ? `Notifications, ${unread} unread` : 'Notifications'}
                aria-expanded={open}
                className="relative p-2.5 text-gray-400 hover:text-white hover:bg-gray-900 rounded-xl transition-colors"
            >
                <Bell size={20} />
                {unread > 0 && (
                    <span className="absolute top-1 right-1 min-w-[18px] h-[18px] px-1 bg-brand-600 text-white text-[10px] font-black rounded-full flex items-center justify-center border-2 border-gray-950">
                        {unread > 9 ? '9+' : unread}
                    </span>
                )}
            </button>

            {open && (
                <>
                    <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
                    <div className="absolute right-0 mt-2 w-[min(22rem,calc(100vw-2rem))] bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl z-50 overflow-hidden">
                        <div className="px-4 py-3 border-b border-gray-800">
                            <p className="text-sm font-bold text-white">Notifications</p>
                        </div>
                        <div className="max-h-96 overflow-y-auto">
                            {!loaded ? (
                                <p className="px-4 py-8 text-sm text-gray-500 text-center">Loading...</p>
                            ) : items.length === 0 ? (
                                <p className="px-4 py-8 text-sm text-gray-500 text-center">Nothing yet. Order updates will show up here.</p>
                            ) : (
                                <ul className="divide-y divide-gray-800">
                                    {items.map((item, index) => (
                                        <li key={item.id}>
                                            <button
                                                onClick={() => follow(item)}
                                                className={clsx(
                                                    "w-full text-left px-4 py-3 hover:bg-gray-800/60 transition-colors",
                                                    !item.link && "cursor-default"
                                                )}
                                            >
                                                <div className="flex items-start justify-between gap-3">
                                                    <p className={clsx("text-sm font-bold", index < unread ? "text-white" : "text-gray-300")}>{item.title}</p>
                                                    <span className="text-[11px] text-gray-500 whitespace-nowrap">{timeAgo(item.created_at)}</span>
                                                </div>
                                                <p className="text-sm text-gray-400 mt-0.5 whitespace-pre-line line-clamp-3">{item.message}</p>
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default NotificationBell;
