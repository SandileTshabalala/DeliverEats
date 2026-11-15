import { useEffect, useState } from 'react';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { adminBilling, errorMessage, type Enforcement } from '../../services/billing';

/**
 * The subscription switch. Off: every restaurant is open whether it paid or not
 * (free pilot). On: restaurants without a paid plan, or past their grace days,
 * are hidden from customers and cannot take orders.
 */
const EnforcementSwitch = ({ onChanged }: { onChanged?: () => void }) => {
    const [state, setState] = useState<Enforcement | null>(null);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        adminBilling.enforcement().then(setState).catch(() => undefined);
    }, []);

    if (!state) return null;

    const flip = async () => {
        const turningOn = !state.enforced;
        if (turningOn) {
            const closing = state.would_close;
            const sure = window.confirm(
                'Start charging restaurants for their plans?\n\n' +
                (closing.length
                    ? `These ${closing.length} restaurant${closing.length > 1 ? 's have' : ' has'} no paid plan and will be HIDDEN from customers right away:\n• ${closing.slice(0, 15).join('\n• ')}${closing.length > 15 ? `\n…and ${closing.length - 15} more` : ''}`
                    : 'Every restaurant has a paid plan, so none will be hidden.')
            );
            if (!sure) return;
        }
        setSaving(true);
        try {
            const next = await adminBilling.setEnforcement(turningOn);
            setState(next);
            toast.success(turningOn ? 'Subscriptions are now enforced' : 'Subscriptions switched off: every restaurant is open');
            onChanged?.();
        } catch (error) {
            toast.error(errorMessage(error, 'Could not change the setting'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <section className={clsx(
            'rounded-2xl border px-5 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4',
            state.enforced ? 'bg-gray-900/40 border-gray-800' : 'bg-yellow-500/10 border-yellow-500/20'
        )}>
            <div className="space-y-1">
                <p className="font-bold text-white">Charge restaurants for their plans</p>
                <p className={clsx('text-sm', state.enforced ? 'text-gray-400' : 'text-yellow-500')}>
                    {state.enforced
                        ? `On. Restaurants without a paid plan are hidden from customers ${state.grace_days} days after their plan ends.`
                        : 'Off. Every restaurant is open whether it has paid or not (good for a free pilot).'}
                </p>
                {state.enforced && state.would_close.length > 0 && (
                    <p className="text-xs text-gray-500">Hidden right now: {state.would_close.join(', ')}</p>
                )}
            </div>
            <button
                type="button"
                role="switch"
                aria-checked={state.enforced}
                aria-label="Charge restaurants for their plans"
                disabled={saving}
                onClick={flip}
                className={clsx(
                    'relative shrink-0 w-14 h-8 rounded-full transition-colors disabled:opacity-50 self-start sm:self-auto',
                    state.enforced ? 'bg-green-500' : 'bg-gray-700'
                )}
            >
                {/* real white in both themes (light mode turns "white" into dark ink) */}
                <span style={{ background: '#ffffff' }} className={clsx(
                    'absolute top-1 left-1 w-6 h-6 rounded-full shadow transition-transform',
                    state.enforced && 'translate-x-6'
                )} />
            </button>
        </section>
    );
};

export default EnforcementSwitch;
