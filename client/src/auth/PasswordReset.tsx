import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import api from '../services/api';
import { errorMessage } from '../services/billing';

const field = "appearance-none block w-full px-3 py-2 border border-gray-700 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-brand-500 focus:border-brand-500 bg-gray-700 text-white sm:text-sm";
const button = "w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500 transition-colors disabled:opacity-70 disabled:cursor-not-allowed";

const Shell = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div className="min-h-screen bg-gray-900 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
            <h1 className="text-center text-3xl font-extrabold text-white">{title}</h1>
        </div>
        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
            <div className="bg-gray-800 py-8 px-4 shadow sm:rounded-lg sm:px-10 space-y-6">
                {children}
                <p className="text-center text-sm">
                    <Link to="/login" className="font-medium text-brand-500 hover:text-brand-400">Back to sign in</Link>
                </p>
            </div>
        </div>
    </div>
);

export const ForgotPassword = () => {
    const [email, setEmail] = useState('');
    const [sending, setSending] = useState(false);
    const [sent, setSent] = useState(false);

    const submit = async (event: React.FormEvent) => {
        event.preventDefault();
        setSending(true);
        try {
            await api.post('/auth/forgot-password', { email });
            setSent(true);
        } catch (error) {
            toast.error(errorMessage(error, 'Could not send the email. Please try again.'));
        } finally {
            setSending(false);
        }
    };

    if (sent) {
        return (
            <Shell title="Check your email">
                <p className="text-gray-300 text-sm">
                    If <span className="font-medium text-white">{email}</span> has an account, we have sent a link to choose a new password.
                    The link works for 30 minutes. Check your spam folder if you do not see it.
                </p>
            </Shell>
        );
    }

    return (
        <Shell title="Forgot your password?">
            <form className="space-y-6" onSubmit={submit}>
                <p className="text-gray-400 text-sm">Enter the email address you signed up with and we will send you a link to choose a new password.</p>
                <div>
                    <label htmlFor="reset-email" className="block text-sm font-medium text-gray-300">Email address</label>
                    <div className="mt-1">
                        <input id="reset-email" type="email" autoComplete="email" required value={email}
                            onChange={event => setEmail(event.target.value)} className={field} placeholder="you@example.com" />
                    </div>
                </div>
                <button type="submit" disabled={sending} className={button}>{sending ? 'Sending...' : 'Send reset link'}</button>
            </form>
        </Shell>
    );
};

export const ResetPassword = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const token = searchParams.get('token') ?? '';
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [saving, setSaving] = useState(false);

    const submit = async (event: React.FormEvent) => {
        event.preventDefault();
        if (password !== confirm) {
            toast.error('The two passwords do not match');
            return;
        }
        setSaving(true);
        try {
            await api.post('/auth/reset-password', { token, password });
            toast.success('Password changed. Please sign in.');
            navigate('/login', { replace: true });
        } catch (error) {
            toast.error(errorMessage(error, 'Could not change the password'));
        } finally {
            setSaving(false);
        }
    };

    if (!token) {
        return (
            <Shell title="Link not valid">
                <p className="text-gray-300 text-sm">
                    This reset link is incomplete. <Link to="/forgot-password" className="text-brand-500 hover:text-brand-400 font-medium">Request a new one</Link>.
                </p>
            </Shell>
        );
    }

    return (
        <Shell title="Choose a new password">
            <form className="space-y-6" onSubmit={submit}>
                <div>
                    <label htmlFor="new-password" className="block text-sm font-medium text-gray-300">New password (at least 8 characters)</label>
                    <div className="mt-1">
                        <input id="new-password" type="password" autoComplete="new-password" required minLength={8}
                            value={password} onChange={event => setPassword(event.target.value)} className={field} />
                    </div>
                </div>
                <div>
                    <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-300">Type it again</label>
                    <div className="mt-1">
                        <input id="confirm-password" type="password" autoComplete="new-password" required minLength={8}
                            value={confirm} onChange={event => setConfirm(event.target.value)} className={field} />
                    </div>
                </div>
                <button type="submit" disabled={saving} className={button}>{saving ? 'Saving...' : 'Change password'}</button>
            </form>
        </Shell>
    );
};
