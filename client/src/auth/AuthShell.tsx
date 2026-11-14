import { Link } from 'react-router-dom';
import { Bike, CheckCircle2, Store, Wallet } from 'lucide-react';
import Logo from '../components/Logo';
import ThemeToggle from '../components/ThemeToggle';
import { TAGLINE } from '../config/brand';
import images from '../constant/images';

const POINTS = [
    { icon: Store, text: 'Shisanyamas, kota spots and home kitchens near you' },
    { icon: Bike, text: 'Follow your driver live, all the way to your door' },
    { icon: Wallet, text: 'Pay cash, card or online, as the restaurant offers' },
];

/**
 * Sign-in style page: food photo with the logo on the left (large screens),
 * the form on the right. Used by sign in and the password reset pages.
 */
const AuthShell = ({ title, subtitle, children, footer }: {
    title: string; subtitle?: React.ReactNode; children: React.ReactNode; footer?: React.ReactNode;
}) => (
    <div className="relative min-h-screen bg-gray-950 flex">
        <div className="absolute top-4 right-4 z-20"><ThemeToggle /></div>

        <aside className="keep-dark hidden lg:flex lg:w-[46%] xl:w-1/2 relative overflow-hidden">
            <img src={images.heroGrill} alt="" className="absolute inset-0 w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/55 to-black/75" />
            <div className="relative z-10 flex flex-col justify-between p-12 xl:p-16 w-full">
                <Link to="/" className="self-start"><Logo tone="dark" className="h-16" /></Link>
                <div className="space-y-8 max-w-lg">
                    <h2 className="text-5xl font-black leading-[1.05] tracking-tight text-white">
                        Your kasi&apos;s best food,<br /><span className="text-brand-500">delivered.</span>
                    </h2>
                    <ul className="space-y-4">
                        {POINTS.map(({ icon: Icon, text }) => (
                            <li key={text} className="flex items-center gap-4 text-gray-100 font-medium">
                                <span className="w-10 h-10 rounded-xl bg-white/10 backdrop-blur-md border border-white/15 flex items-center justify-center flex-shrink-0">
                                    <Icon size={18} className="text-brand-400" />
                                </span>
                                {text}
                            </li>
                        ))}
                    </ul>
                    <p className="flex items-center gap-2 text-sm text-gray-300">
                        <CheckCircle2 size={16} className="text-brand-400" /> {TAGLINE}
                    </p>
                </div>
            </div>
        </aside>

        <main className="flex-1 flex items-center justify-center px-6 py-16 sm:px-10 relative overflow-hidden">
            <div className="lg:hidden absolute -top-24 left-1/2 -translate-x-1/2 w-80 h-80 bg-brand-600 rounded-full blur-[110px] opacity-20 pointer-events-none" />
            <div className="relative w-full max-w-md animate-in fade-in slide-in-from-bottom-4 duration-500">
                <Link to="/" className="lg:hidden inline-block mb-10"><Logo className="h-12" /></Link>
                <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-white">{title}</h1>
                {subtitle && <p className="mt-2 text-gray-400 font-medium">{subtitle}</p>}
                <div className="mt-8">{children}</div>
                {footer && <div className="mt-8 text-center text-sm text-gray-400">{footer}</div>}
            </div>
        </main>
    </div>
);

export const authInput = "w-full bg-gray-900 border border-gray-800 rounded-2xl py-3.5 pl-12 pr-4 text-white placeholder-gray-500 outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all font-medium";
export const authLabel = "block text-sm font-bold text-gray-300 mb-2";
export const authButton = "w-full flex items-center justify-center gap-2 py-4 rounded-2xl bg-brand-600 hover:bg-brand-700 text-white font-bold text-base shadow-lg shadow-brand-600/25 transition-all active:scale-[0.99] disabled:opacity-70 disabled:cursor-not-allowed";

export default AuthShell;
