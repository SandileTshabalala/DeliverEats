import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Compass } from 'lucide-react';
import Logo from '../components/Logo';
import ThemeToggle from '../components/ThemeToggle';

/**
 * Shown for an address that does not exist. `home` is where "Go home" leads:
 * the landing page for visitors, or the dashboard of the area the user was in.
 * Inside an app area (embedded) it sits in that area's layout, so the menu stays.
 */
const NotFound = ({ home = '/', embedded = false }: { home?: string; embedded?: boolean }) => {
    const navigate = useNavigate();
    const { pathname } = useLocation();

    const body = (
        <div className="w-full max-w-md text-center space-y-7 animate-in fade-in zoom-in-95 duration-500">
            <div className="relative mx-auto w-28 h-28">
                <div className="absolute inset-0 bg-brand-500 rounded-full blur-[60px] opacity-20" />
                <div className="relative w-28 h-28 rounded-[32px] bg-gray-900 border border-gray-800 flex items-center justify-center">
                    <Compass size={48} className="text-brand-500" />
                </div>
            </div>
            <div className="space-y-2">
                <p className="text-sm font-black text-brand-500 uppercase tracking-widest">404</p>
                <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white">This page is off the menu</h1>
                <p className="text-gray-400 font-medium">
                    We couldn't find <span className="font-mono text-gray-300 break-all">{pathname}</span>. The link may be old or mistyped.
                </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Link to={home} className="px-6 py-3.5 rounded-2xl bg-brand-600 hover:bg-brand-700 text-white font-bold shadow-lg shadow-brand-600/25">
                    Go home
                </Link>
                <button onClick={() => navigate(-1)} className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl bg-gray-900 border border-gray-800 hover:border-gray-700 text-white font-bold">
                    <ArrowLeft size={18} /> Go back
                </button>
            </div>
        </div>
    );

    if (embedded) return <div className="min-h-[70vh] flex items-center justify-center px-4 py-10">{body}</div>;
    return (
        <div className="relative min-h-screen bg-gray-950 flex flex-col">
            <header className="flex items-center justify-between px-6 py-5">
                <Link to="/"><Logo className="h-10" /></Link>
                <ThemeToggle />
            </header>
            <main className="flex-1 flex items-center justify-center px-4 pb-20">{body}</main>
        </div>
    );
};

export default NotFound;
