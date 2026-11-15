import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface Point { lat: number; lng: number }

const pin = (html: string, label: string) => L.divIcon({
    className: '',               // no Leaflet default white box
    html: `<div role="img" aria-label="${label}">${html}</div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
});

// Plain inline SVG so nothing is fetched (Leaflet's default marker images break in bundled apps)
const DRIVER = pin(
    `<div style="width:36px;height:36px;border-radius:9999px;background:#ea580c;border:3px solid #fff;box-shadow:0 2px 10px rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="5.5" cy="17.5" r="3.5"/><circle cx="18.5" cy="17.5" r="3.5"/><path d="M15 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2zm-3 11.5V14l-3-3 4-3 2 3h2"/></svg>
    </div>`,
    'Your driver',
);
const HOME = pin(
    `<div style="width:36px;height:36px;border-radius:9999px;background:#111827;border:3px solid #fff;box-shadow:0 2px 10px rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/></svg>
    </div>`,
    'Delivery address',
);

/**
 * Small live map: the driver (moves as new positions arrive) and where the
 * order is going. Map pictures come from OpenStreetMap.
 */
const DriverMap = ({ driver, destination, className = '' }: { driver: Point; destination?: Point | null; className?: string }) => {
    const box = useRef<HTMLDivElement>(null);
    const map = useRef<L.Map | null>(null);
    const driverMarker = useRef<L.Marker | null>(null);
    const userMoved = useRef(false);

    // create the map once
    useEffect(() => {
        if (!box.current || map.current) return;
        const created = L.map(box.current, { zoomControl: true, attributionControl: true, scrollWheelZoom: false })
            .setView([driver.lat, driver.lng], 15);
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>',
        }).addTo(created);
        driverMarker.current = L.marker([driver.lat, driver.lng], { icon: DRIVER, zIndexOffset: 1000, keyboard: false }).addTo(created);
        if (destination) L.marker([destination.lat, destination.lng], { icon: HOME, keyboard: false }).addTo(created);
        // once the customer pans or zooms, stop re-framing the map under their finger
        created.on('dragstart zoomstart', (event: L.LeafletEvent) => {
            if ((event as L.LeafletEvent & { originalEvent?: Event }).originalEvent) userMoved.current = true;
        });
        map.current = created;
        return () => {
            created.remove();
            map.current = null;
            driverMarker.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // follow the driver
    useEffect(() => {
        const current = map.current;
        if (!current || !driverMarker.current) return;
        driverMarker.current.setLatLng([driver.lat, driver.lng]);
        if (userMoved.current) return;
        if (destination) {
            current.fitBounds(L.latLngBounds([[driver.lat, driver.lng], [destination.lat, destination.lng]]), { padding: [48, 48], maxZoom: 16 });
        } else {
            current.panTo([driver.lat, driver.lng]);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [driver.lat, driver.lng, destination?.lat, destination?.lng]);

    return <div ref={box} className={`relative z-0 rounded-2xl overflow-hidden border border-gray-800 ${className}`} />;
};

export default DriverMap;
