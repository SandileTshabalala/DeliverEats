import { useCallback, useEffect, useRef, useState } from 'react';
import { formatClock, HALF_HOURS } from '../../utils/clock';
import { useSearchParams } from 'react-router-dom';
import { Banknote, CreditCard, Globe, Landmark, CheckCircle2, AlertTriangle, MapPin, Store, Upload } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { formatRand } from '../../context/CartContext';
import { redirectToHostedCheckout } from '../../services/paymentFactory';
import {
    errorMessage, formatDate, intervalLabel, manage, STATUS_LABEL, STATUS_STYLE,
} from '../../services/billing';
import type { BillingOverview, DeliverySettings, PaymentSettings, SubscriptionPayment } from '../../services/billing';
import { assetUrl, platform, resizeImage } from '../../services/platform';
import { AccountDetailsCard, PasswordCard } from '../../components/AccountSettings';
import type { RestaurantProfile } from '../../services/platform';

const input = "w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 focus:border-brand-500 outline-none";
const label = "block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5";
const card = "bg-gray-900 border border-gray-800 rounded-2xl p-6 md:p-8 space-y-6";

const Toggle = ({ checked, onChange, title, hint, icon }: { checked: boolean; onChange: (value: boolean) => void; title: string; hint: string; icon: React.ReactNode }) => (
    <label className={clsx("flex items-start space-x-4 p-4 rounded-xl border cursor-pointer transition-colors", checked ? "border-brand-500/50 bg-brand-500/5" : "border-gray-800 bg-gray-950")}>
        <input type="checkbox" checked={checked} onChange={event => onChange(event.target.checked)} className="mt-1 rounded bg-gray-950 border-gray-700 text-brand-600" />
        <span className={clsx("mt-0.5", checked ? "text-brand-500" : "text-gray-600")}>{icon}</span>
        <span>
            <span className="block font-bold text-white">{title}</span>
            <span className="block text-sm text-gray-500">{hint}</span>
        </span>
    </label>
);

const Settings = () => {
    const [billing, setBilling] = useState<BillingOverview | null>(null);
    const [history, setHistory] = useState<SubscriptionPayment[]>([]);
    const [payments, setPayments] = useState<PaymentSettings | null>(null);
    // Kept as text while editing so a field can be empty ("no limit")
    const [delivery, setDelivery] = useState({ base_fee: '0', per_km_fee: '0', free_delivery_over: '', max_distance_km: '', latitude: '', longitude: '' });
    const [savingDelivery, setSavingDelivery] = useState(false);
    const [profile, setProfile] = useState<RestaurantProfile | null>(null);
    const [savingProfile, setSavingProfile] = useState(false);
    const [uploadingLogo, setUploadingLogo] = useState(false);
    const logoInput = useRef<HTMLInputElement>(null);
    const [locating, setLocating] = useState(false);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [subscribing, setSubscribing] = useState<string | null>(null);

    const applyDelivery = (saved: DeliverySettings) => setDelivery({
        base_fee: String(Number(saved.base_fee)),
        per_km_fee: String(Number(saved.per_km_fee)),
        free_delivery_over: saved.free_delivery_over ? String(Number(saved.free_delivery_over)) : '',
        max_distance_km: saved.max_distance_km != null ? String(saved.max_distance_km) : '',
        latitude: saved.latitude != null ? String(saved.latitude) : '',
        longitude: saved.longitude != null ? String(saved.longitude) : '',
    });

    const load = useCallback(async () => {
        try {
            const [overview, paymentSettings, paymentHistory, deliverySettings, restaurantProfile] = await Promise.all([
                manage.billing(), manage.paymentSettings(), manage.billingHistory(), manage.deliverySettings(), platform.profile(),
            ]);
            setProfile(restaurantProfile);
            applyDelivery(deliverySettings);
            setBilling(overview);
            setPayments(paymentSettings);
            setHistory(paymentHistory);
        } catch (error) {
            toast.error(errorMessage(error, 'Could not load your settings'));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    // Back from paying the subscription on PayFast. The confirmation reaches the
    // server separately, so the status is re-checked a few times.
    const [searchParams, setSearchParams] = useSearchParams();
    const handledReturn = useRef(false);
    useEffect(() => {
        const result = searchParams.get('billing');
        if (!result || handledReturn.current) return;
        handledReturn.current = true;
        setSearchParams({}, { replace: true });
        if (result === 'cancelled') {
            toast.error('Payment was cancelled. Your plan has not changed.');
            return;
        }
        toast.success('Thank you! We are confirming your payment.', { duration: 6000 });
        const timers = [3000, 8000, 20000].map(ms => setTimeout(load, ms));
        return () => timers.forEach(clearTimeout);
    }, [searchParams, setSearchParams, load]);

    const savePayments = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!payments) return;
        setSaving(true);
        try {
            setPayments(await manage.savePaymentSettings(payments));
            toast.success('Payment methods saved');
        } catch (error) {
            toast.error(errorMessage(error, 'Could not save payment methods'));
        } finally {
            setSaving(false);
        }
    };

    const saveProfile = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!profile) return;
        setSavingProfile(true);
        try {
            setProfile(await platform.updateProfile({
                name: profile.name, address: profile.address, description: profile.description || null,
                category_ids: profile.category_ids,
                opens_at: profile.opens_at || null, closes_at: profile.closes_at || null,
                vat_number: profile.vat_number || null,
                phone: profile.phone || '',
            }));
            toast.success('Restaurant details saved');
        } catch (error) {
            toast.error(errorMessage(error, 'Could not save your details'));
        } finally {
            setSavingProfile(false);
        }
    };

    const chooseLogo = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        event.target.value = ''; // so choosing the same file again still triggers
        if (!file) return;
        setUploadingLogo(true);
        try {
            // shrink on the phone first: a few tens of KB instead of several MB
            setProfile(await platform.uploadLogo(await resizeImage(file)));
            toast.success('Logo updated');
        } catch (error: any) {
            toast.error(error?.response ? errorMessage(error, 'Could not upload the logo') : (error?.message || 'Could not upload the logo'));
        } finally {
            setUploadingLogo(false);
        }
    };

    const removeLogo = async () => {
        try {
            setProfile(await platform.removeLogo());
            toast.success('Logo removed');
        } catch (error) {
            toast.error(errorMessage(error, 'Could not remove the logo'));
        }
    };

    const saveDelivery = async (event: React.FormEvent) => {
        event.preventDefault();
        setSavingDelivery(true);
        const numberOrNull = (value: string) => (value.trim() === '' ? null : Number(value));
        try {
            applyDelivery(await manage.saveDeliverySettings({
                base_fee: delivery.base_fee || '0',
                per_km_fee: delivery.per_km_fee || '0',
                free_delivery_over: delivery.free_delivery_over.trim() || null,
                max_distance_km: numberOrNull(delivery.max_distance_km),
                latitude: numberOrNull(delivery.latitude),
                longitude: numberOrNull(delivery.longitude),
            }));
            toast.success('Delivery fee saved');
        } catch (error) {
            toast.error(errorMessage(error, 'Could not save the delivery fee'));
        } finally {
            setSavingDelivery(false);
        }
    };

    const useMyLocation = () => {
        if (!navigator.geolocation) {
            toast.error('This device cannot share its location. Type the coordinates instead.');
            return;
        }
        setLocating(true);
        navigator.geolocation.getCurrentPosition(
            position => {
                setDelivery(current => ({
                    ...current,
                    latitude: position.coords.latitude.toFixed(6),
                    longitude: position.coords.longitude.toFixed(6),
                }));
                setLocating(false);
                toast.success('Location captured. Remember to save.');
            },
            () => {
                setLocating(false);
                toast.error('Could not get your location. Allow location access and try again.');
            },
            { enableHighAccuracy: true, timeout: 15000 },
        );
    };

    const subscribe = async (planId: string) => {
        setSubscribing(planId);
        try {
            const result = await manage.subscribe(planId);
            if (result.action === 'checkout' && result.checkout_url) {
                toast.loading('Taking you to PayFast...');
                redirectToHostedCheckout(result.checkout_url, result.checkout_fields);
                return;
            }
            toast.success(result.action === 'trial_started' ? 'Your free trial has started' : 'Plan activated');
            load();
        } catch (error) {
            toast.error(errorMessage(error, 'Could not start the subscription'));
        } finally {
            setSubscribing(null);
        }
    };

    if (loading || !billing || !payments) return <div className="p-8 text-gray-500">Loading settings...</div>;

    const subscription = billing.subscription;
    const closed = subscription.enforced && !subscription.is_live;
    const set = (changes: Partial<PaymentSettings>) => setPayments({ ...payments, ...changes });

    return (
        <div className="space-y-8 max-w-4xl animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">Settings</h1>
                <p className="text-gray-400 mt-1">Your restaurant and logo, how customers pay you, your delivery fee, and your plan.</p>
            </div>

            {closed && (
                <div className="flex items-start space-x-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-2xl px-5 py-4">
                    <AlertTriangle size={20} className="mt-0.5 flex-shrink-0" />
                    <p className="text-sm">Your restaurant is hidden from customers because there is no active plan. Choose a plan below to open again.</p>
                </div>
            )}
            {subscription.status === 'past_due' && (
                <div className="flex items-start space-x-3 bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 rounded-2xl px-5 py-4">
                    <AlertTriangle size={20} className="mt-0.5 flex-shrink-0" />
                    <p className="text-sm">Your plan ran out on {formatDate(subscription.current_period_end)}. You stay open for {subscription.grace_days} days after that date; pay before then to avoid being hidden.</p>
                </div>
            )}
            {subscription.limit_reached && (
                <div className="flex items-start space-x-3 bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 rounded-2xl px-5 py-4">
                    <AlertTriangle size={20} className="mt-0.5 flex-shrink-0" />
                    <p className="text-sm">You have used all {subscription.orders_limit} orders on your plan this month, so new orders are paused. Move to a bigger plan to keep taking orders.</p>
                </div>
            )}

            {/* Restaurant profile */}
            {profile && (
                <form onSubmit={saveProfile} className={card}>
                    <div>
                        <h2 className="text-xl font-bold text-white">Your restaurant</h2>
                        <p className="text-sm text-gray-500 mt-1">This is what customers see when they browse.</p>
                    </div>

                    <div className="flex flex-wrap items-center gap-5">
                        <div className="w-24 h-24 rounded-2xl bg-gray-950 border border-gray-800 overflow-hidden flex items-center justify-center text-gray-700 flex-shrink-0">
                            {profile.logo_img_url
                                ? <img src={assetUrl(profile.logo_img_url)} alt={`${profile.name} logo`} className="w-full h-full object-cover" />
                                : <Store size={36} />}
                        </div>
                        <div className="space-y-2">
                            <input ref={logoInput} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={chooseLogo} />
                            <div className="flex flex-wrap gap-2">
                                <button type="button" onClick={() => logoInput.current?.click()} disabled={uploadingLogo} className="flex items-center space-x-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 disabled:opacity-60 text-white font-bold rounded-xl text-sm">
                                    <Upload size={16} /><span>{uploadingLogo ? 'Uploading...' : profile.logo_img_url ? 'Change logo' : 'Upload logo'}</span>
                                </button>
                                {profile.logo_img_url && (
                                    <button type="button" onClick={removeLogo} className="px-4 py-2.5 text-gray-400 hover:text-red-500 font-bold rounded-xl text-sm">Remove</button>
                                )}
                            </div>
                            <p className="text-xs text-gray-600">A square photo or logo works best. PNG or JPG; it is resized for you.</p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className={label} htmlFor="shop-name">Restaurant name</label>
                            <input id="shop-name" required className={input} value={profile.name} onChange={e => setProfile({ ...profile, name: e.target.value })} />
                        </div>
                        <div>
                            <label className={label} htmlFor="shop-address">Address</label>
                            <input id="shop-address" required className={input} value={profile.address} onChange={e => setProfile({ ...profile, address: e.target.value })} />
                        </div>
                        <div className="md:col-span-2">
                            <label className={label} htmlFor="shop-description">Short description</label>
                            <input id="shop-description" maxLength={500} className={input} placeholder="What you are known for" value={profile.description ?? ''} onChange={e => setProfile({ ...profile, description: e.target.value })} />
                        </div>
                        <div className="md:col-span-2">
                            <span className={label}>What do you sell? (up to {profile.max_categories})</span>
                            <div className="flex flex-wrap gap-2" role="group" aria-label="Food types you sell">
                                {profile.category_options.map(option => {
                                    const position = profile.category_ids.indexOf(option.id);
                                    const picked = position >= 0;
                                    const full = !picked && profile.category_ids.length >= profile.max_categories;
                                    return (
                                        <button
                                            type="button"
                                            key={option.id}
                                            aria-pressed={picked}
                                            disabled={full}
                                            onClick={() => setProfile({
                                                ...profile,
                                                category_ids: picked ? profile.category_ids.filter(id => id !== option.id) : [...profile.category_ids, option.id],
                                            })}
                                            className={picked
                                                ? "px-3.5 py-2 rounded-full text-sm font-bold bg-brand-500 text-white"
                                                : "px-3.5 py-2 rounded-full text-sm font-bold bg-gray-950 border border-gray-800 text-gray-300 hover:border-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"}
                                        >
                                            {option.name}{position === 0 && profile.category_ids.length > 1 ? ' · main' : ''}
                                        </button>
                                    );
                                })}
                            </div>
                            <p className="text-xs text-gray-600 mt-1.5">Customers find you under each one. The first you pick shows on your card. Missing a type? Ask the platform team to add it.</p>
                        </div>
                        <div>
                            <label className={label} htmlFor="shop-phone">Phone number for customers</label>
                            <input id="shop-phone" type="tel" inputMode="tel" maxLength={20} className={input}
                                placeholder={profile.owner_phone || '072 123 4567'}
                                value={profile.phone ?? ''} onChange={e => setProfile({ ...profile, phone: e.target.value })} />
                            <p className="text-xs text-gray-600 mt-1">
                                Customers see this on their order and call it to change or cancel.
                                {profile.owner_phone && !profile.phone ? ` Leave it empty to use your own number (${profile.owner_phone}).` : ''}
                            </p>
                        </div>
                        <div>
                            <label className={label} htmlFor="shop-vat">VAT number (only if VAT registered)</label>
                            <input id="shop-vat" inputMode="numeric" maxLength={10} pattern="4[0-9]{9}" className={input} placeholder="4xxxxxxxxx"
                                value={profile.vat_number ?? ''} onChange={e => setProfile({ ...profile, vat_number: e.target.value.replace(/\D/g, '') || null })} />
                            <p className="text-xs text-gray-600 mt-1">With a VAT number your order invoices become tax invoices showing the VAT.</p>
                        </div>
                    </div>

                    <div className="border-t border-gray-800 pt-6 space-y-4">
                        <div>
                            <h3 className="font-bold text-white">Opening hours</h3>
                            <p className="text-sm text-gray-500">Customers can only order while you are open. Leave both empty to be open whenever your kitchen switch is on.</p>
                        </div>
                        <div className="grid grid-cols-2 gap-4 max-w-sm">
                            {([['shop-opens', 'Opens', 'opens_at'], ['shop-closes', 'Closes', 'closes_at']] as const).map(([id, text, key]) => (
                                <div key={id}>
                                    <label className={label} htmlFor={id}>{text}</label>
                                    <select id={id} className={input} value={profile[key] ?? ''} onChange={e => setProfile({ ...profile, [key]: e.target.value || null })}>
                                        <option value="">Not set</option>
                                        {/* keep an older saved time (e.g. 22:15) selectable */}
                                        {profile[key] && !HALF_HOURS.some(h => h.value === profile[key]) && <option value={profile[key]!}>{formatClock(profile[key])}</option>}
                                        {HALF_HOURS.map(h => <option key={h.value} value={h.value}>{h.label}</option>)}
                                    </select>
                                </div>
                            ))}
                        </div>
                        <p className={profile.opens_at && profile.closes_at ? "text-sm font-bold text-white" : "text-sm text-gray-500"}>
                            {profile.opens_at && profile.closes_at
                                ? `Open every day ${formatClock(profile.opens_at)} to ${formatClock(profile.closes_at)}${profile.closes_at <= profile.opens_at ? ' (closes after midnight)' : ''}`
                                : profile.opens_at || profile.closes_at ? 'Choose both an opening and a closing time.' : 'No hours set: open whenever your kitchen switch is on.'}
                        </p>
                        <p className="text-xs text-gray-600">Closing after midnight works too, for example 6:00 PM to 2:00 AM. Remember to save.</p>
                    </div>

                    <button disabled={savingProfile} className="px-6 py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold rounded-xl">
                        {savingProfile ? 'Saving...' : 'Save details'}
                    </button>
                </form>
            )}

            {/* Payment methods */}
            <form onSubmit={savePayments} className={card}>
                <div>
                    <h2 className="text-xl font-bold text-white">How customers pay you</h2>
                    <p className="text-sm text-gray-500 mt-1">The money goes straight to you. We never hold your order money.</p>
                </div>

                <div className="space-y-3">
                    <Toggle checked={payments.accepts_cash} onChange={value => set({ accepts_cash: value })} icon={<Banknote size={20} />}
                        title="Cash on delivery" hint="The driver collects cash at the door." />
                    <Toggle checked={payments.accepts_card_machine} onChange={value => set({ accepts_card_machine: value })} icon={<CreditCard size={20} />}
                        title="Card machine on delivery"
                        hint="Only switch this on if your speedpoint (FNB, Capitec, Yoco ...) is portable: the driver takes it to the customer's door. A countertop machine cannot go with the driver." />
                </div>

                <div className="space-y-2">
                    <p className={label}>Online payment (optional)</p>
                    <p className="text-sm text-gray-500">
                        The customer pays in the app before you cook, so you get no unpaid or fake orders. Each needs your own account with that
                        company, which pays the money into your bank account and charges a fee per payment. Your speedpoint account cannot be used for this.
                    </p>
                </div>
                <div className="space-y-3">
                    <Toggle checked={payments.payfast_enabled} onChange={value => set({ payfast_enabled: value })} icon={<Globe size={20} />}
                        title="PayFast" hint="Card, Instant EFT and more on one payment page." />
                    <Toggle checked={payments.ozow_enabled} onChange={value => set({ ozow_enabled: value })} icon={<Landmark size={20} />}
                        title="Ozow" hint="Instant EFT: the customer pays straight from their own bank app, no card needed." />
                    <Toggle checked={payments.peach_enabled} onChange={value => set({ peach_enabled: value })} icon={<CreditCard size={20} />}
                        title="Peach Payments" hint="Card payments, Apple Pay and more on Peach's secure page." />
                </div>

                {payments.payfast_enabled && (
                    <div className="space-y-4 border-t border-gray-800 pt-6">
                        <p className="text-sm text-gray-400">
                            Find these in your PayFast dashboard under Settings, then Integration. The passphrase must match the one set there exactly.
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className={label} htmlFor="pf-id">Merchant ID</label>
                                <input id="pf-id" className={input} value={payments.payfast_merchant_id ?? ''} onChange={e => set({ payfast_merchant_id: e.target.value })} placeholder="10000100" />
                            </div>
                            <div>
                                <label className={label} htmlFor="pf-key">Merchant key</label>
                                <input id="pf-key" type="password" autoComplete="off" className={input} value={payments.payfast_merchant_key ?? ''} onChange={e => set({ payfast_merchant_key: e.target.value })} placeholder="Enter your merchant key" />
                            </div>
                            <div>
                                <label className={label} htmlFor="pf-pass">Passphrase</label>
                                <input id="pf-pass" type="password" autoComplete="off" className={input} value={payments.payfast_passphrase ?? ''} onChange={e => set({ payfast_passphrase: e.target.value })} placeholder="Enter your passphrase" />
                            </div>
                            <label className="flex items-center space-x-3 text-sm text-gray-300 md:mt-7">
                                <input type="checkbox" checked={payments.payfast_sandbox} onChange={e => set({ payfast_sandbox: e.target.checked })} className="rounded bg-gray-950 border-gray-700 text-brand-600" />
                                <span>Test mode (sandbox, no real money)</span>
                            </label>
                        </div>
                        <p className="text-xs text-gray-600">Saved keys are stored encrypted and are never shown again. Leave the dots as they are to keep the saved key.</p>
                    </div>
                )}

                {payments.ozow_enabled && (
                    <div className="space-y-4 border-t border-gray-800 pt-6">
                        <p className="font-bold text-white">Ozow details</p>
                        <p className="text-sm text-gray-400">
                            In the Ozow Portal open One API, then Clients, and create a client: it gives you a client ID and client secret.
                            Your site code is on your Ozow site. We check these with Ozow when you save.
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className={label} htmlFor="oz-site">Site code</label>
                                <input id="oz-site" className={input} value={payments.ozow_site_code ?? ''} onChange={e => set({ ozow_site_code: e.target.value })} placeholder="ABC-ABC-001" />
                            </div>
                            <div>
                                <label className={label} htmlFor="oz-client">Client ID</label>
                                <input id="oz-client" autoComplete="off" className={input} value={payments.ozow_client_id ?? ''} onChange={e => set({ ozow_client_id: e.target.value })} />
                            </div>
                            <div>
                                <label className={label} htmlFor="oz-secret">Client secret</label>
                                <input id="oz-secret" type="password" autoComplete="off" className={input} value={payments.ozow_client_secret ?? ''} onChange={e => set({ ozow_client_secret: e.target.value })} placeholder="Enter your client secret" />
                            </div>
                            <label className="flex items-center space-x-3 text-sm text-gray-300 md:mt-7">
                                <input type="checkbox" checked={payments.ozow_sandbox} onChange={e => set({ ozow_sandbox: e.target.checked })} className="rounded bg-gray-950 border-gray-700 text-brand-600" />
                                <span>Test mode (Ozow staging, no real money)</span>
                            </label>
                        </div>
                    </div>
                )}

                {payments.peach_enabled && (
                    <div className="space-y-4 border-t border-gray-800 pt-6">
                        <p className="font-bold text-white">Peach Payments details</p>
                        <p className="text-sm text-gray-400">
                            In the Peach Payments Dashboard open Checkout, then API keys: copy the entity ID and the secret token.
                            Also add <span className="font-mono text-gray-200">{window.location.host}</span> to the allowed domains there,
                            otherwise Peach refuses to open its payment page from this app.
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className={label} htmlFor="peach-entity">Entity ID</label>
                                <input id="peach-entity" autoComplete="off" className={input} value={payments.peach_entity_id ?? ''} onChange={e => set({ peach_entity_id: e.target.value })} />
                            </div>
                            <div>
                                <label className={label} htmlFor="peach-secret">Secret token</label>
                                <input id="peach-secret" type="password" autoComplete="off" className={input} value={payments.peach_secret_token ?? ''} onChange={e => set({ peach_secret_token: e.target.value })} placeholder="Enter your secret token" />
                            </div>
                            <label className="flex items-center space-x-3 text-sm text-gray-300">
                                <input type="checkbox" checked={payments.peach_sandbox} onChange={e => set({ peach_sandbox: e.target.checked })} className="rounded bg-gray-950 border-gray-700 text-brand-600" />
                                <span>Test mode (sandbox, no real money)</span>
                            </label>
                        </div>
                    </div>
                )}

                <button disabled={saving} className="px-6 py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold rounded-xl">
                    {saving ? 'Saving...' : 'Save payment methods'}
                </button>
            </form>

            {/* Delivery fee */}
            <form onSubmit={saveDelivery} className={card}>
                <div>
                    <h2 className="text-xl font-bold text-white">Delivery fee</h2>
                    <p className="text-sm text-gray-500 mt-1">What customers pay for delivery. It is added to their order and goes to you with the rest.</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className={label} htmlFor="fee-base">Base fee (R)</label>
                        <input id="fee-base" type="number" min="0" step="0.5" className={input} value={delivery.base_fee} onChange={e => setDelivery({ ...delivery, base_fee: e.target.value })} />
                        <p className="text-xs text-gray-600 mt-1">Charged on every delivery. Use 0 for free delivery.</p>
                    </div>
                    <div>
                        <label className={label} htmlFor="fee-km">Extra per km (R)</label>
                        <input id="fee-km" type="number" min="0" step="0.5" className={input} value={delivery.per_km_fee} onChange={e => setDelivery({ ...delivery, per_km_fee: e.target.value })} />
                        <p className="text-xs text-gray-600 mt-1">Leave at 0 to charge the same fee whatever the distance.</p>
                    </div>
                    <div>
                        <label className={label} htmlFor="fee-free">Free delivery on orders from (R)</label>
                        <input id="fee-free" type="number" min="1" step="1" className={input} placeholder="Never free" value={delivery.free_delivery_over} onChange={e => setDelivery({ ...delivery, free_delivery_over: e.target.value })} />
                    </div>
                    <div>
                        <label className={label} htmlFor="fee-max">Furthest you deliver (km)</label>
                        <input id="fee-max" type="number" min="0.5" step="0.5" className={input} placeholder="No limit" value={delivery.max_distance_km} onChange={e => setDelivery({ ...delivery, max_distance_km: e.target.value })} />
                    </div>
                </div>

                <div className="border-t border-gray-800 pt-6 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <h3 className="font-bold text-white">Your shop's location</h3>
                            <p className="text-sm text-gray-500">Needed to charge per km or to limit how far you deliver.</p>
                        </div>
                        <button type="button" onClick={useMyLocation} disabled={locating} className="flex items-center space-x-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 disabled:opacity-60 text-white font-bold rounded-xl text-sm">
                            <MapPin size={16} /><span>{locating ? 'Finding you...' : 'Use my current location'}</span>
                        </button>
                    </div>
                    <p className="text-xs text-gray-600">Tap the button while you are standing at the shop, or type the coordinates.</p>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className={label} htmlFor="fee-lat">Latitude</label>
                            <input id="fee-lat" type="number" step="any" className={input} placeholder="-26.2485" value={delivery.latitude} onChange={e => setDelivery({ ...delivery, latitude: e.target.value })} />
                        </div>
                        <div>
                            <label className={label} htmlFor="fee-lng">Longitude</label>
                            <input id="fee-lng" type="number" step="any" className={input} placeholder="27.8540" value={delivery.longitude} onChange={e => setDelivery({ ...delivery, longitude: e.target.value })} />
                        </div>
                    </div>
                </div>

                <button disabled={savingDelivery} className="px-6 py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold rounded-xl">
                    {savingDelivery ? 'Saving...' : 'Save delivery fee'}
                </button>
            </form>

            {/* Subscription */}
            <section className={card}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                        <h2 className="text-xl font-bold text-white">Your plan</h2>
                        <p className="text-sm text-gray-500 mt-1">
                            {subscription.plan
                                ? `${subscription.plan.name}, ${formatRand(subscription.plan.price)} per ${intervalLabel(subscription.plan.interval_months)}`
                                : 'You are not on a plan yet.'}
                        </p>
                    </div>
                    <span className={clsx("px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border", STATUS_STYLE[subscription.status])}>
                        {STATUS_LABEL[subscription.status]}
                    </span>
                </div>

                {subscription.plan && (
                    <dl className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                        <div>
                            <dt className="text-gray-500">{subscription.status === 'trialing' ? 'Trial ends' : subscription.auto_renews ? 'Renews on' : 'Paid until'}</dt>
                            <dd className="text-white font-bold">{formatDate(subscription.current_period_end)}</dd>
                        </div>
                        <div>
                            <dt className="text-gray-500">Orders this month</dt>
                            <dd className="text-white font-bold">{subscription.orders_this_month}{subscription.orders_limit ? ` of ${subscription.orders_limit}` : ' (unlimited)'}</dd>
                        </div>
                    </dl>
                )}

                {billing.plans.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-gray-800 pt-6">
                        {billing.plans.map(plan => {
                            const current = subscription.plan?.id === plan.id;
                            const paidUp = current && subscription.status === 'active' && subscription.auto_renews;
                            const offersTrial = subscription.status === 'none' && plan.trial_days > 0;
                            return (
                                <div key={plan.id} className={clsx("rounded-xl border p-5 space-y-3", current ? "border-brand-500/50 bg-brand-500/5" : "border-gray-800 bg-gray-950")}>
                                    <div className="flex items-center justify-between">
                                        <h3 className="font-bold text-white">{plan.name}</h3>
                                        {current && <span className="flex items-center space-x-1 text-brand-400 text-xs font-bold"><CheckCircle2 size={14} /><span>Current</span></span>}
                                    </div>
                                    <p className="text-xl font-black text-brand-500">{formatRand(plan.price)} <span className="text-sm font-bold text-gray-500">/ {intervalLabel(plan.interval_months)}</span></p>
                                    {plan.description && <p className="text-sm text-gray-400">{plan.description}</p>}
                                    <p className="text-sm text-gray-500">{plan.max_orders_per_month ? `Up to ${plan.max_orders_per_month} orders a month` : 'Unlimited orders'}</p>
                                    {!paidUp && !subscription.recurring_active && (
                                        <button
                                            onClick={() => subscribe(plan.id)}
                                            disabled={subscribing !== null}
                                            className="w-full py-2.5 bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold rounded-lg text-sm"
                                        >
                                            {subscribing === plan.id ? 'Please wait...'
                                                : offersTrial ? `Start ${plan.trial_days}-day free trial`
                                                    : current ? 'Pay now' : 'Choose this plan'}
                                        </button>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
                {subscription.recurring_active && (
                    <p className="text-sm text-gray-400 p-4 rounded-xl bg-gray-950 border border-gray-800">
                        Your plan is paid automatically by PayFast. To change plan, contact us first so we can stop the
                        current debit order and you are never charged twice.
                    </p>
                )}
                {!billing.online_payment_available && (
                    <p className="text-sm text-gray-500">Online payment for plans is not available yet. Contact us to pay by EFT and we will activate your plan.</p>
                )}

                {history.length > 0 && (
                    <div className="border-t border-gray-800 pt-6">
                        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-3">Payments</h3>
                        <ul className="divide-y divide-gray-800 text-sm">
                            {history.map(payment => (
                                <li key={payment.id} className="flex justify-between py-2.5 text-gray-400">
                                    <span>{formatDate(payment.created_at)} <span className="text-gray-600">({payment.method === 'manual' ? 'EFT / cash' : 'PayFast'})</span></span>
                                    <span className="text-white font-bold">{formatRand(payment.amount)}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </section>

            {/* The signed-in person's own account (owner or staff) */}
            <AccountDetailsCard hint="New orders and plan reminders are sent to this number and email address." />
            <PasswordCard />
        </div>
    );
};

export default Settings;
