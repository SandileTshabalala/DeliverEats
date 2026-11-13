import { useEffect, useState } from 'react';
import { platform } from '../services/platform';
import type { PublicStats } from '../services/platform';

/** Real platform counters for the public pages. null until loaded (or if unavailable). */
export const usePublicStats = () => {
    const [stats, setStats] = useState<PublicStats | null>(null);
    useEffect(() => {
        let active = true;
        platform.publicStats().then(result => { if (active) setStats(result); });
        return () => { active = false; };
    }, []);
    return stats;
};
