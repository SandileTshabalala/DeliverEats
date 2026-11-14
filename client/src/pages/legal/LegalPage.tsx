import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useSite } from '../../services/site';
import type { SiteInfo } from '../../services/site';

export const LAST_UPDATED = '14 November 2026';

/** "Deliver Eats (Pty) Ltd" when set, otherwise the app name. */
export const operatorName = (site: SiteInfo | null) => site?.business_name || site?.app_name || 'the platform operator';

export const ContactDetails = ({ site }: { site: SiteInfo | null }) => {
    const lines = [
        site?.business_name,
        site?.business_address,
        site?.support_email && <a key="email" href={`mailto:${site.support_email}`} className="text-brand-500 hover:text-brand-400">{site.support_email}</a>,
        site?.support_phone && <a key="phone" href={`tel:${site.support_phone.replace(/[^\d+]/g, '')}`} className="text-brand-500 hover:text-brand-400">{site.support_phone}</a>,
    ].filter(Boolean);
    if (lines.length === 0) {
        // Shown until BUSINESS_NAME / SUPPORT_EMAIL / SUPPORT_PHONE are set on the server
        return <p>Our contact details have not been published yet.</p>;
    }
    return <address className="not-italic space-y-1">{lines.map((line, i) => <p key={i}>{line}</p>)}</address>;
};

export const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <section className="space-y-3">
        <h2 className="text-xl font-bold text-white">{title}</h2>
        <div className="space-y-3 text-gray-300 leading-relaxed">{children}</div>
    </section>
);

const LegalPage = ({ title, children }: { title: string; children: (site: SiteInfo | null) => React.ReactNode }) => {
    const site = useSite();
    return (
        <div className="min-h-screen bg-gray-950 text-gray-100">
            <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12 space-y-10">
                <Link to="/" className="inline-flex items-center space-x-2 text-sm font-bold text-gray-400 hover:text-white">
                    <ArrowLeft size={16} /><span>Back to {site?.app_name ?? 'home'}</span>
                </Link>
                <header className="space-y-2">
                    <h1 className="text-4xl font-black text-white tracking-tight">{title}</h1>
                    <p className="text-sm text-gray-500">Last updated {LAST_UPDATED}</p>
                </header>
                {children(site)}
                <footer className="pt-8 border-t border-gray-800 flex flex-wrap gap-6 text-sm">
                    <Link to="/privacy" className="text-gray-400 hover:text-white">Privacy Policy</Link>
                    <Link to="/terms" className="text-gray-400 hover:text-white">Terms of Use</Link>
                </footer>
            </div>
        </div>
    );
};

export default LegalPage;
