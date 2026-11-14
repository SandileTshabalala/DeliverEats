import { useEffect, useState } from 'react';
import { CheckCircle2, XCircle, Send } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';
import { errorMessage } from '../../services/billing';
import { platform } from '../../services/platform';
import type { SystemStatus } from '../../services/platform';

const card = "bg-gray-900 border border-gray-800 rounded-2xl p-6 md:p-8 space-y-5";
const input = "w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 focus:border-brand-500 outline-none";
const label = "block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5";

const Row = ({ ok, title, detail }: { ok: boolean; title: string; detail: string }) => (
    <li className="flex items-start space-x-3 py-3">
        {ok ? <CheckCircle2 size={20} className="text-green-500 mt-0.5 flex-shrink-0" /> : <XCircle size={20} className="text-red-500 mt-0.5 flex-shrink-0" />}
        <div>
            <p className="font-bold text-white">{title}</p>
            <p className="text-sm text-gray-500">{detail}</p>
        </div>
    </li>
);

const EMPTY_BUSINESS = { business_name: '', business_address: '', support_email: '', support_phone: '', vat_number: '' };

/** Who runs the platform: printed on subscription invoices, the legal pages and the landing page. */
const BusinessDetailsCard = ({ onSaved }: { onSaved: () => void }) => {
    const [form, setForm] = useState(EMPTY_BUSINESS);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        platform.business()
            .then(saved => setForm({
                business_name: saved.business_name ?? '', business_address: saved.business_address ?? '',
                support_email: saved.support_email ?? '', support_phone: saved.support_phone ?? '', vat_number: saved.vat_number ?? '',
            }))
            .catch(error => toast.error(errorMessage(error, 'Could not load your business details')));
    }, []);

    const save = async (event: React.FormEvent) => {
        event.preventDefault();
        setSaving(true);
        try {
            await platform.saveBusiness(form);
            toast.success(form.vat_number ? 'Saved. New invoices are tax invoices showing VAT.' : 'Business details saved');
            onSaved();
        } catch (error) {
            toast.error(errorMessage(error, 'Could not save your business details'));
        } finally {
            setSaving(false);
        }
    };

    const field = (key: keyof typeof EMPTY_BUSINESS) => ({
        value: form[key],
        onChange: (event: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: event.target.value }),
    });

    return (
        <form onSubmit={save} className={card}>
            <div>
                <h2 className="text-xl font-bold text-white">Business details</h2>
                <p className="text-sm text-gray-500 mt-1">
                    Printed on the invoices restaurants get for their plan, and shown on the Privacy and Terms pages and the landing page.
                </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label className={label} htmlFor="biz-name">Registered business name</label>
                    <input id="biz-name" className={input} placeholder="Deliver Eats (Pty) Ltd" maxLength={120} {...field('business_name')} />
                </div>
                <div>
                    <label className={label} htmlFor="biz-vat">VAT number (only if VAT registered)</label>
                    <input id="biz-vat" className={input} inputMode="numeric" maxLength={10} pattern="4[0-9]{9}" placeholder="4xxxxxxxxx"
                        value={form.vat_number} onChange={e => setForm({ ...form, vat_number: e.target.value.replace(/\D/g, '') })} />
                </div>
                <div className="md:col-span-2">
                    <label className={label} htmlFor="biz-address">Business address</label>
                    <input id="biz-address" className={input} placeholder="Street, area, city, postal code" maxLength={300} {...field('business_address')} />
                </div>
                <div>
                    <label className={label} htmlFor="biz-email">Support email</label>
                    <input id="biz-email" type="email" className={input} placeholder="help@yourdomain.co.za" maxLength={120} {...field('support_email')} />
                </div>
                <div>
                    <label className={label} htmlFor="biz-phone">Support phone</label>
                    <input id="biz-phone" type="tel" className={input} placeholder="011 555 0123" maxLength={30} {...field('support_phone')} />
                </div>
            </div>
            <p className="text-xs text-gray-600">
                With a VAT number, subscription invoices become tax invoices showing the 15% VAT included in the price.
                Leave it empty if you are not VAT registered.
            </p>
            <button disabled={saving} className="px-6 py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold rounded-xl">
                {saving ? 'Saving...' : 'Save business details'}
            </button>
        </form>
    );
};

const Settings = () => {
    const { user, reloadUser } = useAuth();
    const [account, setAccount] = useState({ name: '', sur_name: '', contact_number: '', email: '' });
    const [savingAccount, setSavingAccount] = useState(false);

    useEffect(() => {
        if (user) {
            setAccount({ name: user.name ?? '', sur_name: user.sur_name ?? '', contact_number: user.contact_number ?? '', email: user.email ?? '' });
        }
    }, [user]);

    const saveAccount = async (event: React.FormEvent) => {
        event.preventDefault();
        setSavingAccount(true);
        try {
            await api.patch('/users/me', account);
            await reloadUser();
            toast.success('Your details were saved. Use the new email address next time you sign in.');
        } catch (error) {
            toast.error(errorMessage(error, 'Could not save your details'));
        } finally {
            setSavingAccount(false);
        }
    };
    const [status, setStatus] = useState<SystemStatus | null>(null);
    const [testing, setTesting] = useState(false);
    const [passwords, setPasswords] = useState({ current: '', next: '', confirm: '' });
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        platform.system().then(setStatus).catch(error => toast.error(errorMessage(error, 'Could not load the settings')));
    }, []);

    const sendTest = async () => {
        setTesting(true);
        try {
            const sent = await platform.sendTestMessage();
            if (!sent.sms && !sent.email) toast.error('Neither SMS nor email is set up yet, so nothing was sent.');
            else toast.success(`Test sent by ${[sent.sms && 'SMS', sent.email && 'email'].filter(Boolean).join(' and ')} to your own number and address.`);
        } catch (error) {
            toast.error(errorMessage(error, 'Could not send the test'));
        } finally {
            setTesting(false);
        }
    };

    const changePassword = async (event: React.FormEvent) => {
        event.preventDefault();
        if (passwords.next !== passwords.confirm) {
            toast.error('The two new passwords do not match');
            return;
        }
        setSaving(true);
        try {
            await platform.changePassword(passwords.current, passwords.next);
            toast.success('Password changed');
            setPasswords({ current: '', next: '', confirm: '' });
        } catch (error) {
            toast.error(errorMessage(error, 'Could not change the password'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="space-y-8 max-w-3xl animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">Settings</h1>
                <p className="text-gray-400 mt-1">What is switched on for the platform, and your own account.</p>
            </div>

            <BusinessDetailsCard onSaved={() => platform.system().then(setStatus).catch(() => undefined)} />

            <section className={card}>
                <div>
                    <h2 className="text-xl font-bold text-white">Platform status</h2>
                    <p className="text-sm text-gray-500 mt-1">Connections to SMS, email and PayFast are set in the server's env file, so their keys never pass through the browser. Change them there and restart the server.</p>
                </div>
                {!status ? <p className="text-gray-500 text-sm">Loading...</p> : (
                    <>
                        <ul className="divide-y divide-gray-800">
                            <Row ok={status.sms.configured} title="SMS (Africa's Talking)"
                                detail={status.sms.configured ? `On${status.sms.sandbox ? ', sandbox mode: messages go to the simulator' : ''}${status.sms.sender_id ? `, sent as ${status.sms.sender_id}` : ''}` : 'Off. Set AT_USERNAME and AT_API_KEY.'} />
                            <Row ok={status.email.configured} title="Email (Resend)"
                                detail={status.email.configured ? `On, sent from ${status.email.from}` : 'Off. Set RESEND_API_KEY and EMAIL_FROM. Password reset needs this.'} />
                            <Row ok={status.payfast.configured} title="Subscription payments (your PayFast account)"
                                detail={status.payfast.configured ? (status.payfast.sandbox ? 'On, in sandbox mode: no real money is taken' : 'On, live') : 'Off. Restaurants can only pay by EFT or cash, which you record under Subscriptions.'} />
                            <Row ok={status.subscriptions.enforced} title="Subscriptions enforced"
                                detail={status.subscriptions.enforced ? `Yes. Unpaid restaurants are hidden ${status.subscriptions.grace_days} days after their plan ends.` : 'No. Every restaurant is open whether it has paid or not. Set SUBSCRIPTIONS_ENFORCED=true when your plans are assigned.'} />
                            <Row ok={status.legal_contact_set} title="Business details on the Privacy and Terms pages"
                                detail={status.legal_contact_set ? 'Set' : 'Not set. Fill in Business details above: PayFast and POPIA expect them to be published.'} />
                            <Row ok={status.secrets_encryption_key_set} title="Encryption key for restaurants' PayFast keys"
                                detail={status.secrets_encryption_key_set ? 'Set' : 'Not set: a key derived from the JWT secret is used. Set ENCRYPTION_KEY before restaurants save PayFast details.'} />
                        </ul>
                        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm border-t border-gray-800 pt-5">
                            <div><dt className="text-gray-500">Environment</dt><dd className="text-white font-bold">{status.environment}</dd></div>
                            <div><dt className="text-gray-500">Default delivery fee</dt><dd className="text-white font-bold">R {status.default_delivery_fee.toFixed(2)}</dd></div>
                            <div className="min-w-0"><dt className="text-gray-500">Website address</dt><dd className="text-white font-bold truncate">{status.frontend_url}</dd></div>
                            <div className="min-w-0"><dt className="text-gray-500">API address (PayFast calls this)</dt><dd className="text-white font-bold truncate">{status.public_api_url}</dd></div>
                        </dl>
                        <button onClick={sendTest} disabled={testing} className="flex items-center space-x-2 px-5 py-2.5 bg-gray-800 hover:bg-gray-700 disabled:opacity-60 text-white font-bold rounded-xl text-sm">
                            <Send size={16} /><span>{testing ? 'Sending...' : 'Send me a test SMS and email'}</span>
                        </button>
                    </>
                )}
            </section>


            <form onSubmit={saveAccount} className={card}>
                <div>
                    <h2 className="text-xl font-bold text-white">Your account</h2>
                    <p className="text-sm text-gray-500 mt-1">Use a real email address and cell number: test messages, password resets and alerts are sent here.</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className={label} htmlFor="acc-name">First name</label>
                        <input id="acc-name" required className={input} value={account.name} onChange={e => setAccount({ ...account, name: e.target.value })} />
                    </div>
                    <div>
                        <label className={label} htmlFor="acc-surname">Surname</label>
                        <input id="acc-surname" required className={input} value={account.sur_name} onChange={e => setAccount({ ...account, sur_name: e.target.value })} />
                    </div>
                    <div>
                        <label className={label} htmlFor="acc-email">Email (used to sign in)</label>
                        <input id="acc-email" required type="email" autoComplete="email" className={input} value={account.email} onChange={e => setAccount({ ...account, email: e.target.value })} />
                    </div>
                    <div>
                        <label className={label} htmlFor="acc-phone">Cell number</label>
                        <input id="acc-phone" required type="tel" autoComplete="tel" className={input} placeholder="072 123 4567" value={account.contact_number} onChange={e => setAccount({ ...account, contact_number: e.target.value })} />
                    </div>
                </div>
                <button disabled={savingAccount} className="px-6 py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold rounded-xl">
                    {savingAccount ? 'Saving...' : 'Save my details'}
                </button>
            </form>

            <form onSubmit={changePassword} className={card}>
                <div>
                    <h2 className="text-xl font-bold text-white">Your password</h2>
                    <p className="text-sm text-gray-500 mt-1">Signed in as {user?.email}. If this account still has the password it was created with, change it now.</p>
                </div>
                <div>
                    <label className={label} htmlFor="pw-current">Current password</label>
                    <input id="pw-current" type="password" required autoComplete="current-password" className={input} value={passwords.current} onChange={e => setPasswords({ ...passwords, current: e.target.value })} />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className={label} htmlFor="pw-next">New password (at least 8 characters)</label>
                        <input id="pw-next" type="password" required minLength={8} autoComplete="new-password" className={input} value={passwords.next} onChange={e => setPasswords({ ...passwords, next: e.target.value })} />
                    </div>
                    <div>
                        <label className={label} htmlFor="pw-confirm">Type it again</label>
                        <input id="pw-confirm" type="password" required minLength={8} autoComplete="new-password" className={input} value={passwords.confirm} onChange={e => setPasswords({ ...passwords, confirm: e.target.value })} />
                    </div>
                </div>
                <button disabled={saving} className="px-6 py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold rounded-xl">
                    {saving ? 'Saving...' : 'Change password'}
                </button>
            </form>
        </div>
    );
};

export default Settings;
