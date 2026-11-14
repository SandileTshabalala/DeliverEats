import { useEffect, useMemo, useState } from 'react';
import ThemeToggle from '../components/ThemeToggle';
import { Link } from 'react-router-dom';
import {
    ArrowRight, Banknote, Bike, ChevronDown, Clock, FileText, MapPin, Menu as MenuIcon, Navigation,
    Smartphone, Star, Store, Utensils, Wallet, X,
} from 'lucide-react';
import { clsx } from 'clsx';
import images from '../constant/images';
import { APP_NAME, TAGLINE } from '../config/brand';
import Logo from '../components/Logo';
import { sells, useCategories } from '../components/CategoryRail';
import { fallbackImage } from '../services/categories';
import { assetUrl } from '../services/platform';
import { usePublicStats } from '../hooks/usePublicStats';
import { useSite } from '../services/site';
import { restaurantService, type Restaurant } from '../services/restaurant';
import RestaurantCard from '../components/RestaurantCard';

const SECTIONS = [
    { id: 'how-it-works', label: 'How it works' },
    { id: 'food', label: 'Food' },
    { id: 'restaurants', label: 'For restaurants' },
    { id: 'drivers', label: 'Drivers' },
    { id: 'faq', label: 'FAQ' },
];

// Food tiles come from Admin > Categories: the ones restaurants sell, in the admin's order.
const MAX_FOOD_TILES = 9;

const FAQ = [
    {
        q: 'How do I pay?',
        a: 'Each restaurant chooses what it accepts: cash on delivery, its card machine at your door, or paying online in the app (card or instant EFT). You see the options at checkout.',
    },
    {
        q: 'Where do you deliver?',
        a: 'Each restaurant sets how far it delivers and its own delivery fee. Add your address and the app shows you who delivers to you and what delivery costs before you pay.',
    },
    {
        q: 'Can I see where my order is?',
        a: 'Yes. You see every step, from the kitchen accepting your order to the driver picking it up, and you can follow the driver on a map while it is on the way.',
    },
    {
        q: 'How does a restaurant join, and what does it cost?',
        a: 'Restaurants pay a small monthly plan instead of a commission on every order, and keep all of their order money. Contact us below to get your restaurant listed.',
    },
];

/** Scroll to a section, leaving room for the fixed header. */
const goTo = (id: string) => {
    const target = document.getElementById(id);
    if (!target) return;
    window.scrollTo({ top: target.getBoundingClientRect().top + window.scrollY - 80, behavior: 'smooth' });
};

const SectionLink = ({ id, children, className, onNavigate }: { id: string; children: React.ReactNode; className?: string; onNavigate?: () => void }) => (
    <a
        href={`#${id}`}
        className={className}
        onClick={event => {
            event.preventDefault();
            onNavigate?.();
            goTo(id);
            window.history.replaceState(null, '', `#${id}`);
        }}
    >
        {children}
    </a>
);

const Step = ({ icon: Icon, title, text }: { icon: typeof Store; title: string; text: string }) => (
    <div className="p-6 bg-gray-900 border border-gray-800 rounded-3xl space-y-3">
        <span className="w-12 h-12 rounded-2xl bg-brand-500/10 text-brand-500 flex items-center justify-center"><Icon size={22} /></span>
        <h3 className="text-lg font-bold text-white">{title}</h3>
        <p className="text-gray-400 leading-relaxed">{text}</p>
    </div>
);

const Landing = () => {
    const publicStats = usePublicStats();
    const site = useSite();
    const [menuOpen, setMenuOpen] = useState(false);
    const [restaurants, setRestaurants] = useState<Restaurant[]>([]);

    useEffect(() => {
        restaurantService.listRestaurants().then(list => setRestaurants(list.filter(r => r.is_active))).catch(() => undefined);
    }, []);

    // Categories some restaurant sells. Before any restaurant has picked one,
    // show the platform's categories that have a picture so the section is not empty.
    const categories = useCategories();
    const food = useMemo(() => {
        const withPicture = categories
            .map(c => ({ name: c.name, image: c.image_url ? assetUrl(c.image_url) : fallbackImage(c.name) }));
        const sold = withPicture.filter(c => restaurants.some(r => sells(r, c.name)));
        if (sold.length) return sold.slice(0, MAX_FOOD_TILES);
        // nobody has picked categories yet: show each stock photo only once
        const seen = new Set<string>();
        return withPicture.filter(c => c.image && !seen.has(c.image) && seen.add(c.image)).slice(0, MAX_FOOD_TILES);
    }, [categories, restaurants]);

    // Arriving at /#faq from another page: scroll there once the page has rendered
    useEffect(() => {
        const id = window.location.hash.slice(1);
        if (id) setTimeout(() => goTo(id), 100);
    }, []);

    const contact = site?.support_email
        ? { href: `mailto:${site.support_email}?subject=${encodeURIComponent(`List my restaurant on ${APP_NAME}`)}`, label: `Email ${site.support_email}` }
        : site?.support_phone
            ? { href: `tel:${site.support_phone.replace(/[^\d+]/g, '')}`, label: `Call ${site.support_phone}` }
            : null;

    return (
        <div className="min-h-screen bg-gray-950 text-white font-sans overflow-x-hidden">
            {/* Navigation */}
            <nav className="fixed top-0 left-0 right-0 z-50 bg-gray-950/80 backdrop-blur-xl border-b border-white/5">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 h-20 flex justify-between items-center">
                    <Link to="/" className="flex items-center space-x-3" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
                        <Logo className="h-11" />
                    </Link>

                    <div className="hidden lg:flex items-center space-x-8">
                        {SECTIONS.map(section => (
                            <SectionLink key={section.id} id={section.id} className="text-sm font-bold text-gray-400 hover:text-white transition-colors">
                                {section.label}
                            </SectionLink>
                        ))}
                    </div>

                    <div className="flex items-center gap-2 sm:gap-3">
                        <ThemeToggle />
                        <Link to="/login" className="hidden sm:inline text-sm font-bold text-white hover:text-brand-400 transition-colors px-2">Sign in</Link>
                        <Link to="/register" className="px-5 py-2.5 bg-brand-600 hover:bg-brand-500 text-white text-sm font-bold rounded-xl transition-colors">
                            Order now
                        </Link>
                        <button
                            className="lg:hidden p-2 text-gray-300 hover:text-white"
                            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
                            aria-expanded={menuOpen}
                            onClick={() => setMenuOpen(!menuOpen)}
                        >
                            {menuOpen ? <X size={24} /> : <MenuIcon size={24} />}
                        </button>
                    </div>
                </div>
                {menuOpen && (
                    <div className="lg:hidden border-t border-white/5 bg-gray-950 px-4 py-4 space-y-1">
                        {SECTIONS.map(section => (
                            <SectionLink key={section.id} id={section.id} onNavigate={() => setMenuOpen(false)}
                                className="block px-3 py-3 rounded-xl text-base font-bold text-gray-300 hover:bg-gray-900 hover:text-white">
                                {section.label}
                            </SectionLink>
                        ))}
                        <Link to="/login" className="block px-3 py-3 rounded-xl text-base font-bold text-gray-300 hover:bg-gray-900 hover:text-white">Sign in</Link>
                    </div>
                )}
            </nav>

            {/* Hero */}
            <header className="keep-dark relative min-h-[92vh] flex items-center overflow-hidden pt-20">
                <img src={images.heroGrill} alt="" className="absolute inset-0 w-full h-full object-cover" />
                <div className="absolute inset-0 bg-gradient-to-r from-gray-950 via-gray-950/85 to-gray-950/30" />
                <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 w-full">
                    <div className="max-w-2xl space-y-8">
                        <span className="inline-flex items-center space-x-2 px-4 py-1.5 bg-white/10 border border-white/10 rounded-full text-sm font-bold">
                            <MapPin size={14} className="text-brand-400" /><span>{TAGLINE}</span>
                        </span>
                        <h1 className="text-5xl sm:text-6xl md:text-7xl font-black tracking-tight leading-[0.95]">
                            Your favourite local food, <span className="text-brand-500">delivered to your door.</span>
                        </h1>
                        <p className="text-lg md:text-xl text-gray-300 leading-relaxed">
                            Order from the shisanyamas, kota spots and kitchens in your area. Pay cash, card or online, and follow your
                            delivery all the way to your door.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4">
                            <Link to="/register" className="inline-flex items-center justify-center space-x-2 px-8 py-4 bg-brand-600 hover:bg-brand-500 text-white font-bold rounded-2xl transition-colors">
                                <span>Start ordering</span><ArrowRight size={18} />
                            </Link>
                            <SectionLink id="restaurants" className="inline-flex items-center justify-center px-8 py-4 bg-white/10 hover:bg-white/15 border border-white/15 text-white font-bold rounded-2xl transition-colors">
                                List your restaurant
                            </SectionLink>
                        </div>
                        {publicStats && publicStats.restaurants > 0 && (
                            <p className="text-sm font-bold text-gray-300">
                                {publicStats.restaurants} local {publicStats.restaurants === 1 ? 'kitchen' : 'kitchens'} taking orders
                                {publicStats.orders_delivered > 0 && ` · ${publicStats.orders_delivered} orders delivered`}
                            </p>
                        )}
                    </div>
                </div>
                <SectionLink id="how-it-works" className="absolute bottom-8 left-1/2 -translate-x-1/2 p-2 rounded-full border border-white/15 text-gray-400 hover:text-white">
                    <span className="sr-only">How it works</span><ChevronDown size={22} />
                </SectionLink>
            </header>

            {/* How it works */}
            <section id="how-it-works" className="py-24 px-4 sm:px-6">
                <div className="max-w-7xl mx-auto space-y-12">
                    <div className="max-w-2xl space-y-3">
                        <p className="text-sm font-black text-brand-500 uppercase tracking-widest">How it works</p>
                        <h2 className="text-4xl md:text-5xl font-black tracking-tight">Hungry to fed in three steps</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <Step icon={Store} title="1. Pick a kitchen" text="See which local restaurants are open and deliver to you, with their menus, prices and delivery fee up front." />
                        <Step icon={Wallet} title="2. Order and pay your way" text="Cash on delivery, the restaurant's card machine at your door, or pay online in the app. You choose at checkout." />
                        <Step icon={Navigation} title="3. Follow it to your door" text="Get a message when the kitchen accepts and when your food leaves, and follow your driver on the map." />
                    </div>
                </div>
            </section>

            {/* Food */}
            <section id="food" className="py-24 px-4 sm:px-6 bg-gray-900/40 border-y border-white/5">
                <div className="max-w-7xl mx-auto space-y-12">
                    <div className="max-w-2xl space-y-3">
                        <p className="text-sm font-black text-brand-500 uppercase tracking-widest">Food</p>
                        <h2 className="text-4xl md:text-5xl font-black tracking-tight">Something for every craving</h2>
                        <p className="text-gray-400 text-lg">From the braai stand on the corner to the kitchen down the road.</p>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 md:gap-6">
                        {food.length === 0 && [1, 2, 3, 4, 5, 6].map(i => <div key={i} className="aspect-[4/3] rounded-3xl bg-gray-900 animate-pulse" />)}
                        {food.map(food => (
                            <Link key={food.name} to="/register" className="keep-dark group relative aspect-[4/3] rounded-3xl overflow-hidden border border-white/5 bg-gradient-to-br from-gray-800 to-gray-900">
                                {food.image
                                    ? <img src={food.image} alt="" loading="lazy" className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                                    : <Utensils className="absolute right-5 top-5 w-10 h-10 text-gray-600" />}
                                <span className="absolute inset-0 bg-gradient-to-t from-gray-950/90 via-gray-950/20 to-transparent" />
                                <span className="absolute left-4 bottom-4 text-lg md:text-xl font-black">{food.name}</span>
                            </Link>
                        ))}
                    </div>

                    {restaurants.length > 0 && (
                        <div className="space-y-6 pt-6">
                            <h3 className="text-2xl font-black">Taking orders on {APP_NAME}</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {restaurants.slice(0, 6).map(restaurant => <RestaurantCard key={restaurant.id} restaurant={restaurant} />)}
                            </div>
                        </div>
                    )}
                </div>
            </section>

            {/* For restaurants */}
            <section id="restaurants" className="py-24 px-4 sm:px-6">
                <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
                    <div className="space-y-8">
                        <div className="space-y-3">
                            <p className="text-sm font-black text-brand-500 uppercase tracking-widest">For restaurants</p>
                            <h2 className="text-4xl md:text-5xl font-black tracking-tight">Keep all your order money</h2>
                            <p className="text-gray-400 text-lg leading-relaxed">
                                No commission on your orders. You pay one small monthly plan and every rand your customers spend goes to you.
                            </p>
                        </div>
                        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                            {[
                                { icon: Banknote, title: 'Paid straight to you', text: 'Cash, your own card machine, or your own online payment account.' },
                                { icon: Bike, title: 'Your own drivers', text: 'Add your drivers in the app. Orders go to them only.' },
                                { icon: Clock, title: 'Your hours, your fees', text: 'Open and close when you want, and set your own delivery fee.' },
                                { icon: FileText, title: 'Reports and invoices', text: 'Download your sales and print invoices whenever you need them.' },
                            ].map(point => (
                                <li key={point.title} className="flex items-start space-x-3">
                                    <point.icon size={22} className="text-brand-500 mt-0.5 flex-shrink-0" />
                                    <div>
                                        <p className="font-bold text-white">{point.title}</p>
                                        <p className="text-sm text-gray-400">{point.text}</p>
                                    </div>
                                </li>
                            ))}
                        </ul>
                        <div className="flex flex-col sm:flex-row gap-4">
                            {contact ? (
                                <a href={contact.href} className="inline-flex items-center justify-center space-x-2 px-8 py-4 bg-brand-600 hover:bg-brand-500 text-white font-bold rounded-2xl transition-colors">
                                    <span>Get listed: {contact.label}</span><ArrowRight size={18} />
                                </a>
                            ) : (
                                <p className="text-gray-400">To list your restaurant, contact the {APP_NAME} team.</p>
                            )}
                            <Link to="/login" className="inline-flex items-center justify-center px-8 py-4 bg-gray-900 border border-gray-800 hover:border-gray-700 text-white font-bold rounded-2xl">
                                Restaurant sign in
                            </Link>
                        </div>
                    </div>
                    <div className="relative rounded-[40px] overflow-hidden border border-white/10 aspect-[4/5] lg:aspect-auto lg:h-[560px]">
                        <img src={images.ribsAndChips} alt="" loading="lazy" className="w-full h-full object-cover" />
                    </div>
                </div>
            </section>

            {/* Drivers */}
            <section id="drivers" className="py-24 px-4 sm:px-6 bg-gray-900/40 border-y border-white/5">
                <div className="max-w-5xl mx-auto text-center space-y-8">
                    <div className="space-y-3">
                        <p className="text-sm font-black text-brand-500 uppercase tracking-widest">Drivers</p>
                        <h2 className="text-4xl md:text-5xl font-black tracking-tight">Deliver for a kitchen near you</h2>
                        <p className="text-gray-400 text-lg max-w-2xl mx-auto">
                            Drivers work for a restaurant on {APP_NAME}. Ask the restaurant you deliver for to add you, then sign in to get your jobs.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
                        <Step icon={Smartphone} title="Jobs on your phone" text="Go online and new deliveries come to you, with an SMS for each one." />
                        <Step icon={Navigation} title="Directions included" text="Open the customer's address in your maps app and call them with one tap." />
                        <Step icon={Banknote} title="Know what to collect" text="Every job tells you whether to collect cash, use the card machine, or nothing because it is paid." />
                    </div>
                    <Link to="/login" className="inline-flex items-center space-x-2 px-8 py-4 bg-white text-black hover:bg-brand-500 hover:text-white font-bold rounded-2xl transition-colors">
                        <span>Driver sign in</span><ArrowRight size={18} />
                    </Link>
                </div>
            </section>

            {/* FAQ */}
            <section id="faq" className="py-24 px-4 sm:px-6">
                <div className="max-w-3xl mx-auto space-y-10">
                    <div className="space-y-3 text-center">
                        <p className="text-sm font-black text-brand-500 uppercase tracking-widest">FAQ</p>
                        <h2 className="text-4xl md:text-5xl font-black tracking-tight">Questions people ask</h2>
                    </div>
                    <div className="space-y-3">
                        {FAQ.map(item => (
                            <details key={item.q} className="group p-6 bg-gray-900 border border-gray-800 rounded-2xl open:border-brand-500/40">
                                <summary className="flex items-center justify-between cursor-pointer list-none font-bold text-lg">
                                    <span>{item.q}</span>
                                    <ChevronDown size={20} className="text-gray-500 group-open:rotate-180 transition-transform flex-shrink-0 ml-4" />
                                </summary>
                                <p className="mt-4 text-gray-400 leading-relaxed">{item.a}</p>
                            </details>
                        ))}
                    </div>
                </div>
            </section>

            {/* Final call to action */}
            <section className="px-4 sm:px-6 pb-24">
                <div className="keep-dark max-w-7xl mx-auto rounded-[40px] bg-brand-600 p-10 md:p-16 flex flex-col md:flex-row md:items-center justify-between gap-8">
                    <div className="space-y-3">
                        <h2 className="text-3xl md:text-5xl font-black tracking-tight">Hungry? Your kasi is open.</h2>
                        <p className="text-brand-100 text-lg">Create a free account and order in minutes.</p>
                    </div>
                    <div className="flex flex-col sm:flex-row gap-4">
                        <Link to="/register" className="inline-flex items-center justify-center px-8 py-4 bg-gray-950 text-white font-bold rounded-2xl hover:bg-gray-900">
                            Create account
                        </Link>
                        <Link to="/login" className="inline-flex items-center justify-center px-8 py-4 bg-brand-700 hover:bg-brand-800 text-white font-bold rounded-2xl">
                            Sign in
                        </Link>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-16 px-4 sm:px-6 border-t border-white/5">
                <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-10">
                    <div className="md:col-span-2 space-y-4">
                        <div className="flex items-center space-x-3">
                            <Logo className="h-12" />
                        </div>
                        <p className="max-w-sm text-gray-500 leading-relaxed">
                            Food from the restaurants in your community, delivered by their own drivers. Every order supports a local business.
                        </p>
                        <p className="flex items-center space-x-1 text-sm text-gray-600">
                            <Star size={14} className="text-brand-500" /><span>Rate your orders to help your favourite spots stand out.</span>
                        </p>
                    </div>
                    <div className="space-y-4">
                        <h3 className="text-sm font-black uppercase tracking-widest text-white">{APP_NAME}</h3>
                        <ul className="space-y-3 text-sm text-gray-400">
                            {SECTIONS.map(section => (
                                <li key={section.id}><SectionLink id={section.id} className="hover:text-white">{section.label}</SectionLink></li>
                            ))}
                            <li><Link to="/privacy" className="hover:text-white">Privacy Policy</Link></li>
                            <li><Link to="/terms" className="hover:text-white">Terms of Use</Link></li>
                        </ul>
                    </div>
                    <div className="space-y-4">
                        <h3 className="text-sm font-black uppercase tracking-widest text-white">Contact</h3>
                        <ul className="space-y-3 text-sm text-gray-400">
                            {site?.support_email && <li><a href={`mailto:${site.support_email}`} className="hover:text-white">{site.support_email}</a></li>}
                            {site?.support_phone && <li><a href={`tel:${site.support_phone.replace(/[^\d+]/g, '')}`} className="hover:text-white">{site.support_phone}</a></li>}
                            {site?.business_address && <li>{site.business_address}</li>}
                            {site && !site.support_email && !site.support_phone && !site.business_address && <li>Contact details coming soon</li>}
                        </ul>
                    </div>
                </div>
                <div className={clsx("max-w-7xl mx-auto mt-12 pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between gap-4 text-sm text-gray-600")}>
                    <p>&copy; {new Date().getFullYear()} {site?.business_name || APP_NAME}. All rights reserved.</p>
                    <p>Food photos: Unsplash. Map data © OpenStreetMap contributors.</p>
                </div>
            </footer>
        </div>
    );
};

export default Landing;
