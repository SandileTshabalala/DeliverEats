import { useEffect, useState } from 'react';
import { Check, Monitor, Moon, Sun } from 'lucide-react';
import { clsx } from 'clsx';
import { useTheme } from '../context/ThemeContext';
import type { ThemeChoice } from '../context/ThemeContext';

const OPTIONS: { value: ThemeChoice; label: string; icon: typeof Sun }[] = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'system', label: 'Same as device', icon: Monitor },
];

/** Header button: pick light, dark, or follow the device. */
const ThemeToggle = () => {
    const { choice, resolved, setChoice } = useTheme();
    const [open, setOpen] = useState(false);

    useEffect(() => {
        if (!open) return;
        const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [open]);

    const Icon = resolved === 'light' ? Sun : Moon;
    return (
        <div className="relative">
            <button
                onClick={() => setOpen(!open)}
                aria-label="Light or dark mode"
                aria-expanded={open}
                className="p-2.5 text-gray-400 hover:text-white hover:bg-gray-900 rounded-xl transition-colors"
            >
                <Icon size={20} />
            </button>
            {open && (
                <>
                    <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
                    <div role="menu" className="absolute right-0 mt-2 w-52 bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl z-50 p-1.5">
                        {OPTIONS.map(option => (
                            <button
                                key={option.value}
                                role="menuitemradio"
                                aria-checked={choice === option.value}
                                onClick={() => { setChoice(option.value); setOpen(false); }}
                                className={clsx(
                                    "w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-bold transition-colors",
                                    choice === option.value ? "bg-gray-800 text-white" : "text-gray-400 hover:bg-gray-800 hover:text-white"
                                )}
                            >
                                <span className="flex items-center space-x-3"><option.icon size={16} /><span>{option.label}</span></span>
                                {choice === option.value && <Check size={16} className="text-brand-500" />}
                            </button>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
};

export default ThemeToggle;
