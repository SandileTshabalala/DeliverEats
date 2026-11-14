import { clsx } from 'clsx';
import { APP_NAME } from '../config/brand';

/**
 * The Deliver Eats logo. "Deliver" is dark ink in the light theme and off-white
 * in the dark theme; CSS in index.css shows the right one for the current theme.
 *
 * tone="dark": always the white-text version, for logos sitting on photos.
 * mark: only the pin (for tight spaces); it reads on both themes.
 */
const Logo = ({ className = 'h-10', tone = 'auto', mark = false }: { className?: string; tone?: 'auto' | 'dark'; mark?: boolean }) => {
    if (mark) return <img src="/logo-mark.png" alt={APP_NAME} className={clsx('w-auto select-none', className)} draggable={false} />;
    if (tone === 'dark') return <img src="/logo-dark.webp" alt={APP_NAME} className={clsx('w-auto select-none', className)} draggable={false} />;
    return (
        <>
            <img src="/logo-light.webp" alt={APP_NAME} className={clsx('logo-for-light w-auto select-none', className)} draggable={false} />
            <img src="/logo-dark.webp" alt={APP_NAME} className={clsx('logo-for-dark w-auto select-none', className)} draggable={false} />
        </>
    );
};

export default Logo;
