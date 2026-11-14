import { createContext, useCallback, useContext, useEffect, useState } from 'react';

export type ThemeChoice = 'light' | 'dark' | 'system';
type Resolved = 'light' | 'dark';

const STORAGE_KEY = 'theme';

const systemTheme = (): Resolved =>
    window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';

const readChoice = (): ThemeChoice => {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved === 'light' || saved === 'dark' || saved === 'system') return saved;
    } catch {
        // private browsing / blocked storage: fall back to the system setting
    }
    return 'system';
};

const apply = (resolved: Resolved) => {
    document.documentElement.dataset.theme = resolved;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', resolved === 'light' ? '#ffffff' : '#110f0d');
};

interface ThemeContextValue {
    choice: ThemeChoice;
    resolved: Resolved;
    setChoice: (choice: ThemeChoice) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
    const [choice, setChoiceState] = useState<ThemeChoice>(readChoice);
    const [system, setSystem] = useState<Resolved>(systemTheme);
    const resolved: Resolved = choice === 'system' ? system : choice;

    // follow the phone / computer setting while "system" is chosen
    useEffect(() => {
        const query = window.matchMedia?.('(prefers-color-scheme: light)');
        if (!query) return;
        const update = () => setSystem(query.matches ? 'light' : 'dark');
        query.addEventListener('change', update);
        return () => query.removeEventListener('change', update);
    }, []);

    useEffect(() => apply(resolved), [resolved]);

    const setChoice = useCallback((next: ThemeChoice) => {
        setChoiceState(next);
        try {
            localStorage.setItem(STORAGE_KEY, next);
        } catch {
            // not saved, but still applied for this visit
        }
    }, []);

    return <ThemeContext.Provider value={{ choice, resolved, setChoice }}>{children}</ThemeContext.Provider>;
};

export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (!context) throw new Error('useTheme must be used inside ThemeProvider');
    return context;
};
