import { useEffect, useState } from 'react';
import { toast } from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { errorMessage } from '../services/billing';
import { platform } from '../services/platform';

const card = "bg-gray-900 border border-gray-800 rounded-2xl p-6 md:p-8 space-y-5";
const input = "w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 focus:border-brand-500 outline-none";
const label = "block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5";

/** The signed-in person's own name, cell number and sign-in email. Works for every role. */
export const AccountDetailsCard = ({ hint }: { hint?: string }) => {
    const { user, reloadUser } = useAuth();
    const [account, setAccount] = useState({ name: '', sur_name: '', contact_number: '', email: '' });
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (user) {
            setAccount({ name: user.name ?? '', sur_name: user.sur_name ?? '', contact_number: user.contact_number ?? '', email: user.email ?? '' });
        }
    }, [user]);

    const save = async (event: React.FormEvent) => {
        event.preventDefault();
        setSaving(true);
        const emailChanged = account.email !== user?.email;
        try {
            await api.patch('/users/me', account);
            await reloadUser();
            toast.success(emailChanged ? 'Saved. Use the new email address next time you sign in.' : 'Your details were saved');
        } catch (error) {
            toast.error(errorMessage(error, 'Could not save your details'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <form onSubmit={save} className={card}>
            <div>
                <h2 className="text-xl font-bold text-white">Your details</h2>
                <p className="text-sm text-gray-500 mt-1">{hint ?? 'Keep your cell number correct: order messages are sent to it.'}</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label className={label} htmlFor="account-name">First name</label>
                    <input id="account-name" required className={input} autoComplete="given-name" value={account.name} onChange={e => setAccount({ ...account, name: e.target.value })} />
                </div>
                <div>
                    <label className={label} htmlFor="account-surname">Surname</label>
                    <input id="account-surname" required className={input} autoComplete="family-name" value={account.sur_name} onChange={e => setAccount({ ...account, sur_name: e.target.value })} />
                </div>
                <div>
                    <label className={label} htmlFor="account-phone">Cell number</label>
                    <input id="account-phone" required type="tel" autoComplete="tel" className={input} placeholder="072 123 4567" value={account.contact_number} onChange={e => setAccount({ ...account, contact_number: e.target.value })} />
                </div>
                <div>
                    <label className={label} htmlFor="account-email">Email (used to sign in)</label>
                    <input id="account-email" required type="email" autoComplete="email" className={input} value={account.email} onChange={e => setAccount({ ...account, email: e.target.value })} />
                </div>
            </div>
            <button disabled={saving} className="px-6 py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold rounded-xl">
                {saving ? 'Saving...' : 'Save my details'}
            </button>
        </form>
    );
};

/** Change the signed-in person's own password. */
export const PasswordCard = () => {
    const [passwords, setPasswords] = useState({ current: '', next: '', confirm: '' });
    const [saving, setSaving] = useState(false);

    const save = async (event: React.FormEvent) => {
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
        <form onSubmit={save} className={card}>
            <div>
                <h2 className="text-xl font-bold text-white">Password</h2>
                <p className="text-sm text-gray-500 mt-1">If someone else created your account, change the password they gave you.</p>
            </div>
            <div>
                <label className={label} htmlFor="password-current">Current password</label>
                <input id="password-current" type="password" required autoComplete="current-password" className={input} value={passwords.current} onChange={e => setPasswords({ ...passwords, current: e.target.value })} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label className={label} htmlFor="password-next">New password (at least 8 characters)</label>
                    <input id="password-next" type="password" required minLength={8} autoComplete="new-password" className={input} value={passwords.next} onChange={e => setPasswords({ ...passwords, next: e.target.value })} />
                </div>
                <div>
                    <label className={label} htmlFor="password-confirm">Type it again</label>
                    <input id="password-confirm" type="password" required minLength={8} autoComplete="new-password" className={input} value={passwords.confirm} onChange={e => setPasswords({ ...passwords, confirm: e.target.value })} />
                </div>
            </div>
            <button disabled={saving} className="px-6 py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold rounded-xl">
                {saving ? 'Saving...' : 'Change password'}
            </button>
        </form>
    );
};
