import { useCallback, useEffect, useState } from 'react';
import { Plus, Pencil, Store, X } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import AddRestaurantModal from '../../components/admin/AddRestaurantModal';
import { errorMessage, formatDate, STATUS_LABEL, STATUS_STYLE } from '../../services/billing';
import type { SubscriptionStatus } from '../../services/billing';
import { assetUrl, platform } from '../../services/platform';
import type { AdminRestaurant } from '../../services/platform';

const input = "w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 focus:border-brand-500 outline-none";
const label = "block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5";

const Restaurants = () => {
    const [restaurants, setRestaurants] = useState<AdminRestaurant[]>([]);
    const [loading, setLoading] = useState(true);
    const [adding, setAdding] = useState(false);
    const [editing, setEditing] = useState<AdminRestaurant | null>(null);
    const [saving, setSaving] = useState(false);

    const load = useCallback(async () => {
        try {
            setRestaurants(await platform.restaurants());
        } catch (error) {
            toast.error(errorMessage(error, 'Could not load restaurants'));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const toggleOpen = async (restaurant: AdminRestaurant) => {
        const closing = restaurant.is_active;
        if (closing && !window.confirm(`Close ${restaurant.name}? Customers will no longer see it or be able to order from it.`)) return;
        try {
            await platform.updateRestaurant(restaurant.id, { is_active: !restaurant.is_active });
            toast.success(closing ? `${restaurant.name} is closed` : `${restaurant.name} is open again`);
            load();
        } catch (error) {
            toast.error(errorMessage(error, 'Could not update the restaurant'));
        }
    };

    const saveEdit = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!editing) return;
        setSaving(true);
        try {
            await platform.updateRestaurant(editing.id, {
                name: editing.name, address: editing.address, description: editing.description || null,
            });
            toast.success('Restaurant updated');
            setEditing(null);
            load();
        } catch (error) {
            toast.error(errorMessage(error, 'Could not save the restaurant'));
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div className="p-8 text-gray-500">Loading restaurants...</div>;

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">Restaurants</h1>
                    <p className="text-gray-400 mt-1">Every shop on the platform, its owner and whether customers can see it.</p>
                </div>
                <button onClick={() => setAdding(true)} className="flex items-center justify-center space-x-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white font-bold rounded-xl text-sm">
                    <Plus size={18} /><span>Add restaurant</span>
                </button>
            </div>

            {restaurants.length === 0 ? (
                <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center text-gray-500">
                    No restaurants yet. Add the first one to get started.
                </div>
            ) : (
                <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-x-auto">
                    <table className="w-full text-sm min-w-[860px]">
                        <thead>
                            <tr className="text-left text-xs uppercase tracking-widest text-gray-500 border-b border-gray-800">
                                <th className="px-5 py-4">Restaurant</th>
                                <th className="px-5 py-4">Owner</th>
                                <th className="px-5 py-4">Plan</th>
                                <th className="px-5 py-4">Orders this month</th>
                                <th className="px-5 py-4">Customers see it</th>
                                <th className="px-5 py-4 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {restaurants.map(restaurant => {
                                const status = restaurant.subscription_status as SubscriptionStatus;
                                return (
                                    <tr key={restaurant.id} className="border-b border-gray-800 last:border-0">
                                        <td className="px-5 py-4">
                                            <div className="flex items-center space-x-3">
                                                <div className="w-10 h-10 rounded-xl bg-gray-800 overflow-hidden flex items-center justify-center flex-shrink-0 text-gray-600">
                                                    {restaurant.logo_img_url
                                                        ? <img src={assetUrl(restaurant.logo_img_url)} alt="" className="w-full h-full object-cover" />
                                                        : <Store size={18} />}
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="font-bold text-white truncate">{restaurant.name}</p>
                                                    <p className="text-xs text-gray-500 truncate">{restaurant.address}</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-5 py-4">
                                            <p className="text-gray-300">{restaurant.owner_name ?? 'No owner'}</p>
                                            <p className="text-xs text-gray-500">{restaurant.owner_phone}{restaurant.owner_email ? ` · ${restaurant.owner_email}` : ''}</p>
                                        </td>
                                        <td className="px-5 py-4">
                                            <span className={clsx("px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border whitespace-nowrap", STATUS_STYLE[status])}>
                                                {STATUS_LABEL[status]}
                                            </span>
                                            <p className="text-xs text-gray-500 mt-1.5">
                                                {restaurant.plan_name ? `${restaurant.plan_name}, until ${formatDate(restaurant.paid_until)}` : 'Not on a plan'}
                                            </p>
                                        </td>
                                        <td className="px-5 py-4 text-gray-300">{restaurant.orders_this_month}</td>
                                        <td className="px-5 py-4">
                                            {restaurant.is_live
                                                ? <span className="text-green-500 font-bold">Yes</span>
                                                : <span className="text-red-500 font-bold">{restaurant.is_active ? 'No (plan)' : 'No (closed)'}</span>}
                                        </td>
                                        <td className="px-5 py-4">
                                            <div className="flex items-center justify-end space-x-2">
                                                <button aria-label={`Edit ${restaurant.name}`} onClick={() => setEditing(restaurant)} className="p-2 text-gray-500 hover:text-white rounded-lg"><Pencil size={16} /></button>
                                                <button onClick={() => toggleOpen(restaurant)} className={clsx("px-3 py-2 rounded-lg text-xs font-bold whitespace-nowrap", restaurant.is_active ? "bg-gray-800 hover:bg-red-500/10 text-gray-300 hover:text-red-500" : "bg-green-500/10 hover:bg-green-500/20 text-green-500")}>
                                                    {restaurant.is_active ? 'Close' : 'Reopen'}
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            <AddRestaurantModal isOpen={adding} onClose={() => setAdding(false)} onSuccess={load} />

            {editing && (
                <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setEditing(null)}>
                    <form onSubmit={saveEdit} onClick={event => event.stopPropagation()} className="bg-gray-900 border border-gray-800 rounded-3xl p-8 w-full max-w-lg space-y-5">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xl font-bold text-white">Edit restaurant</h3>
                            <button type="button" aria-label="Close" onClick={() => setEditing(null)} className="p-2 text-gray-500 hover:text-white"><X size={20} /></button>
                        </div>
                        <div>
                            <label className={label} htmlFor="edit-name">Name</label>
                            <input id="edit-name" required className={input} value={editing.name} onChange={e => setEditing({ ...editing, name: e.target.value })} />
                        </div>
                        <div>
                            <label className={label} htmlFor="edit-address">Address</label>
                            <input id="edit-address" required className={input} value={editing.address} onChange={e => setEditing({ ...editing, address: e.target.value })} />
                        </div>
                        <div>
                            <label className={label} htmlFor="edit-description">Description</label>
                            <input id="edit-description" className={input} value={editing.description ?? ''} onChange={e => setEditing({ ...editing, description: e.target.value })} />
                        </div>
                        <p className="text-xs text-gray-500">The owner changes the logo, payment methods and delivery fee from their own Settings screen.</p>
                        <button disabled={saving} className="w-full bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold py-3 rounded-xl">
                            {saving ? 'Saving...' : 'Save'}
                        </button>
                    </form>
                </div>
            )}
        </div>
    );
};

export default Restaurants;
