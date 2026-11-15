import { useCallback, useEffect, useState } from 'react';
import { Plus, Pencil, Trash2, Banknote, PauseCircle, PlayCircle, X } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { formatRand } from '../../context/CartContext';
import {
    adminBilling, errorMessage, formatDate, intervalLabel, STATUS_LABEL, STATUS_STYLE,
} from '../../services/billing';
import type { Plan, PlanInput, Subscription } from '../../services/billing';

import EnforcementSwitch from '../../components/admin/EnforcementSwitch';
const emptyPlan: PlanInput = {
    name: '', description: '', price: '', interval_months: 1, trial_days: 0,
    max_orders_per_month: null, is_active: true, sort_order: 0,
};

const input = "w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 focus:border-brand-500 outline-none";
const label = "block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5";

const Billing = () => {
    const [plans, setPlans] = useState<Plan[]>([]);
    const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState<{ id: string | null; form: PlanInput } | null>(null);
    const [saving, setSaving] = useState(false);
    // restaurant id -> plan chosen in that row's dropdown
    const [chosenPlan, setChosenPlan] = useState<Record<string, string>>({});

    const load = useCallback(async () => {
        try {
            const [planList, subscriptionList] = await Promise.all([adminBilling.plans(), adminBilling.subscriptions()]);
            setPlans(planList);
            setSubscriptions(subscriptionList);
        } catch (error) {
            toast.error(errorMessage(error, 'Could not load billing'));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const savePlan = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!editing) return;
        setSaving(true);
        const body = {
            ...editing.form,
            description: editing.form.description || null,
            max_orders_per_month: editing.form.max_orders_per_month || null,
        };
        try {
            if (editing.id) await adminBilling.updatePlan(editing.id, body);
            else await adminBilling.createPlan(body);
            toast.success(editing.id ? 'Plan updated' : 'Plan created');
            setEditing(null);
            load();
        } catch (error) {
            toast.error(errorMessage(error, 'Could not save the plan'));
        } finally {
            setSaving(false);
        }
    };

    const removePlan = async (plan: Plan) => {
        if (!window.confirm(`Remove the "${plan.name}" plan?`)) return;
        try {
            toast.success((await adminBilling.deletePlan(plan.id)).message);
            load();
        } catch (error) {
            toast.error(errorMessage(error, 'Could not remove the plan'));
        }
    };

    const planFor = (subscription: Subscription) =>
        chosenPlan[subscription.restaurant_id] || subscription.plan?.id || plans.find(p => p.is_active)?.id || '';

    const act = async (subscription: Subscription, action: 'assign' | 'paid' | 'suspend' | 'resume' | 'stop_recurring') => {
        const planId = planFor(subscription);
        if ((action === 'assign' || action === 'paid') && !planId) {
            toast.error('Create a plan first');
            return;
        }
        try {
            if (action === 'assign') await adminBilling.setSubscription(subscription.restaurant_id, { plan_id: planId });
            if (action === 'suspend') await adminBilling.setSubscription(subscription.restaurant_id, { status: 'suspended' });
            if (action === 'resume') await adminBilling.setSubscription(subscription.restaurant_id, { status: 'active' });
            if (action === 'stop_recurring') {
                const sure = window.confirm(
                    `Only do this AFTER cancelling ${subscription.restaurant_name}'s subscription in your PayFast dashboard.\n\n` +
                    'It lets the restaurant choose a plan and pay again. If the PayFast debit is still running, they would be charged twice.'
                );
                if (!sure) return;
                await adminBilling.setSubscription(subscription.restaurant_id, { stop_recurring: true });
            }
            if (action === 'paid') {
                const note = window.prompt(`Record a payment from ${subscription.restaurant_name}.\nReference or note (EFT ref, cash, ...):`, '');
                if (note === null) return;
                await adminBilling.recordPayment(subscription.restaurant_id, { plan_id: planId, note: note || undefined });
            }
            toast.success('Saved');
            load();
        } catch (error) {
            toast.error(errorMessage(error, 'Could not update the subscription'));
        }
    };

    const setField = (field: keyof PlanInput, value: any) =>
        setEditing(current => current && ({ ...current, form: { ...current.form, [field]: value } }));

    if (loading) return <div className="p-8 text-gray-500">Loading billing...</div>;

    return (
        <div className="space-y-10 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">Subscriptions</h1>
                <p className="text-gray-400 mt-1">Restaurants keep all of their order money. They pay you for a plan.</p>
            </div>

            <EnforcementSwitch onChanged={load} />

            {/* Plans */}
            <section className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white">Plans</h2>
                    <button
                        onClick={() => setEditing({ id: null, form: emptyPlan })}
                        className="flex items-center space-x-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white font-bold rounded-xl text-sm"
                    >
                        <Plus size={18} /><span>New plan</span>
                    </button>
                </div>

                {plans.length === 0 ? (
                    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-10 text-center text-gray-500">
                        No plans yet. Create your first plan to start charging restaurants.
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                        {plans.map(plan => (
                            <div key={plan.id} className={clsx("bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-3", !plan.is_active && "opacity-50")}>
                                <div className="flex items-start justify-between">
                                    <div>
                                        <h3 className="text-lg font-bold text-white">{plan.name}</h3>
                                        {!plan.is_active && <span className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">Retired</span>}
                                    </div>
                                    <div className="flex space-x-1">
                                        <button aria-label={`Edit ${plan.name}`} onClick={() => setEditing({ id: plan.id, form: { ...plan, description: plan.description ?? '' } })} className="p-2 text-gray-500 hover:text-white rounded-lg"><Pencil size={16} /></button>
                                        <button aria-label={`Remove ${plan.name}`} onClick={() => removePlan(plan)} className="p-2 text-gray-500 hover:text-red-500 rounded-lg"><Trash2 size={16} /></button>
                                    </div>
                                </div>
                                <p className="text-2xl font-black text-brand-500">
                                    {formatRand(plan.price)} <span className="text-sm font-bold text-gray-500">/ {intervalLabel(plan.interval_months)}</span>
                                </p>
                                {plan.description && <p className="text-sm text-gray-400">{plan.description}</p>}
                                <ul className="text-sm text-gray-400 space-y-1">
                                    <li>{plan.max_orders_per_month ? `Up to ${plan.max_orders_per_month} orders a month` : 'Unlimited orders'}</li>
                                    <li>{plan.trial_days ? `${plan.trial_days}-day free trial` : 'No free trial'}</li>
                                </ul>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* Restaurants */}
            <section className="space-y-4">
                <h2 className="text-xl font-bold text-white">Restaurants</h2>
                <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-x-auto">
                    <table className="w-full text-sm min-w-[820px]">
                        <thead>
                            <tr className="text-left text-xs uppercase tracking-widest text-gray-500 border-b border-gray-800">
                                <th className="px-5 py-4">Restaurant</th>
                                <th className="px-5 py-4">Status</th>
                                <th className="px-5 py-4">Paid until</th>
                                <th className="px-5 py-4">Orders this month</th>
                                <th className="px-5 py-4">Plan</th>
                                <th className="px-5 py-4 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {subscriptions.map(subscription => (
                                <tr key={subscription.restaurant_id} className="border-b border-gray-800 last:border-0">
                                    <td className="px-5 py-4 font-bold text-white">{subscription.restaurant_name}</td>
                                    <td className="px-5 py-4">
                                        <span className={clsx("px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border whitespace-nowrap", STATUS_STYLE[subscription.status])}>
                                            {STATUS_LABEL[subscription.status]}
                                        </span>
                                    </td>
                                    <td className="px-5 py-4 text-gray-400 whitespace-nowrap">
                                        {formatDate(subscription.current_period_end)}
                                        {subscription.recurring_active && (
                                            <span className="block text-[10px] text-gray-600 uppercase tracking-widest">
                                                PayFast debit order ·{' '}
                                                <button onClick={() => act(subscription, 'stop_recurring')} className="underline hover:text-white normal-case tracking-normal">mark stopped</button>
                                            </span>
                                        )}
                                    </td>
                                    <td className={clsx("px-5 py-4", subscription.limit_reached ? "text-red-500 font-bold" : "text-gray-400")}>
                                        {subscription.orders_this_month}{subscription.orders_limit ? ` / ${subscription.orders_limit}` : ''}
                                    </td>
                                    <td className="px-5 py-4">
                                        <select
                                            aria-label={`Plan for ${subscription.restaurant_name}`}
                                            value={planFor(subscription)}
                                            onChange={event => setChosenPlan({ ...chosenPlan, [subscription.restaurant_id]: event.target.value })}
                                            className="bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-white text-sm"
                                        >
                                            {plans.filter(p => p.is_active || p.id === subscription.plan?.id).map(plan => (
                                                <option key={plan.id} value={plan.id}>{plan.name}</option>
                                            ))}
                                        </select>
                                    </td>
                                    <td className="px-5 py-4">
                                        <div className="flex items-center justify-end space-x-2">
                                            {(subscription.status === 'none' || planFor(subscription) !== subscription.plan?.id) && (
                                                <button onClick={() => act(subscription, 'assign')} className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg text-xs font-bold whitespace-nowrap">Set plan</button>
                                            )}
                                            <button onClick={() => act(subscription, 'paid')} title="Record an EFT or cash payment" className="flex items-center space-x-1 px-3 py-2 bg-green-500/10 hover:bg-green-500/20 text-green-500 rounded-lg text-xs font-bold whitespace-nowrap">
                                                <Banknote size={14} /><span>Record payment</span>
                                            </button>
                                            {subscription.status === 'suspended' ? (
                                                <button onClick={() => act(subscription, 'resume')} aria-label={`Reactivate ${subscription.restaurant_name}`} title="Reactivate" className="p-2 text-green-500 hover:bg-green-500/10 rounded-lg"><PlayCircle size={18} /></button>
                                            ) : subscription.status !== 'none' && (
                                                <button onClick={() => act(subscription, 'suspend')} aria-label={`Suspend ${subscription.restaurant_name}`} title="Suspend" className="p-2 text-gray-500 hover:text-red-500 hover:bg-red-500/10 rounded-lg"><PauseCircle size={18} /></button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {subscriptions.length === 0 && (
                                <tr><td colSpan={6} className="px-5 py-10 text-center text-gray-500">No restaurants yet.</td></tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>

            {/* Plan form */}
            {editing && (
                <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setEditing(null)}>
                    <form onSubmit={savePlan} onClick={event => event.stopPropagation()} className="bg-gray-900 border border-gray-800 rounded-3xl p-8 w-full max-w-lg space-y-5 max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xl font-bold text-white">{editing.id ? 'Edit plan' : 'New plan'}</h3>
                            <button type="button" aria-label="Close" onClick={() => setEditing(null)} className="p-2 text-gray-500 hover:text-white"><X size={20} /></button>
                        </div>
                        <div>
                            <label className={label} htmlFor="plan-name">Name</label>
                            <input id="plan-name" required className={input} value={editing.form.name} onChange={e => setField('name', e.target.value)} placeholder="Starter" />
                        </div>
                        <div>
                            <label className={label} htmlFor="plan-description">Description</label>
                            <input id="plan-description" className={input} value={editing.form.description ?? ''} onChange={e => setField('description', e.target.value)} placeholder="For small kitchens getting started" />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className={label} htmlFor="plan-price">Price (R)</label>
                                <input id="plan-price" required type="number" min="0" step="0.01" className={input} value={editing.form.price} onChange={e => setField('price', e.target.value)} placeholder="199.00" />
                            </div>
                            <div>
                                <label className={label} htmlFor="plan-interval">Billed every</label>
                                <select id="plan-interval" className={input} value={editing.form.interval_months} onChange={e => setField('interval_months', Number(e.target.value))}>
                                    <option value={1}>Month</option>
                                    <option value={3}>3 months</option>
                                    <option value={6}>6 months</option>
                                    <option value={12}>Year</option>
                                </select>
                            </div>
                            <div>
                                <label className={label} htmlFor="plan-trial">Free trial (days)</label>
                                <input id="plan-trial" type="number" min="0" max="365" className={input} value={editing.form.trial_days} onChange={e => setField('trial_days', Number(e.target.value))} />
                            </div>
                            <div>
                                <label className={label} htmlFor="plan-limit">Orders per month</label>
                                <input id="plan-limit" type="number" min="1" className={input} value={editing.form.max_orders_per_month ?? ''} onChange={e => setField('max_orders_per_month', e.target.value ? Number(e.target.value) : null)} placeholder="Unlimited" />
                            </div>
                        </div>
                        <label className="flex items-center space-x-3 text-sm text-gray-300">
                            <input type="checkbox" checked={editing.form.is_active} onChange={e => setField('is_active', e.target.checked)} className="rounded bg-gray-950 border-gray-700 text-brand-600" />
                            <span>Offered to restaurants</span>
                        </label>
                        <button disabled={saving} className="w-full bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold py-3 rounded-xl">
                            {saving ? 'Saving...' : 'Save plan'}
                        </button>
                    </form>
                </div>
            )}
        </div>
    );
};

export default Billing;
