/**
 * Opening hours are stored as "HH:MM" (24-hour, local time). People read them
 * as "10:00 PM", so every screen shows them through this.
 */
export const formatClock = (value: string | null | undefined): string => {
    const match = /^(\d{1,2}):(\d{2})$/.exec(value ?? '');
    if (!match) return value ?? '';
    const hours = Number(match[1]);
    const suffix = hours < 12 ? 'AM' : 'PM';
    const twelve = hours % 12 === 0 ? 12 : hours % 12;
    return `${twelve}:${match[2]} ${suffix}`;
};

/** Every half hour of the day, for the opening-hours dropdowns. */
export const HALF_HOURS: { value: string; label: string }[] = Array.from({ length: 48 }, (_, i) => {
    const value = `${String(Math.floor(i / 2)).padStart(2, '0')}:${i % 2 ? '30' : '00'}`;
    return { value, label: formatClock(value) };
});
