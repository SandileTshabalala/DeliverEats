import { useCallback, useEffect, useState } from 'react';
import { Bike, Plus, Trash2, UserRound, X } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import { errorMessage, manage } from '../../services/billing';
import type { NewTeamMember, TeamDriver, TeamMember } from '../../services/billing';

const input = "w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 focus:border-brand-500 outline-none";
const label = "block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5";

const emptyMember: NewTeamMember = { email: '', password: '', name: '', sur_name: '', contact_number: '', vehicle_type: 'Motorbike', vehicle_number: '' };

const Team = () => {
    const [drivers, setDrivers] = useState<TeamDriver[]>([]);
    const [staff, setStaff] = useState<TeamMember[]>([]);
    const [loading, setLoading] = useState(true);
    const [adding, setAdding] = useState<'driver' | 'staff' | null>(null);
    const [form, setForm] = useState<NewTeamMember>(emptyMember);
    const [saving, setSaving] = useState(false);

    const load = useCallback(async () => {
        try {
            const [driverList, staffList] = await Promise.all([manage.drivers(), manage.staff()]);
            setDrivers(driverList);
            setStaff(staffList);
        } catch (error) {
            toast.error(errorMessage(error, 'Could not load your team'));
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const open = (kind: 'driver' | 'staff') => { setForm(emptyMember); setAdding(kind); };

    const save = async (event: React.FormEvent) => {
        event.preventDefault();
        setSaving(true);
        try {
            if (adding === 'driver') {
                await manage.addDriver({ ...form, vehicle_number: form.vehicle_number || undefined });
            } else {
                const { vehicle_type: _type, vehicle_number: _number, ...member } = form;
                await manage.addStaff(member);
            }
            toast.success(adding === 'driver' ? 'Driver added. They can sign in now.' : 'Staff member added. They can sign in now.');
            setAdding(null);
            load();
        } catch (error) {
            toast.error(errorMessage(error, 'Could not add this person'));
        } finally {
            setSaving(false);
        }
    };

    const remove = async (kind: 'driver' | 'staff', person: TeamMember) => {
        if (!window.confirm(`Remove ${person.name} ${person.sur_name}? They will no longer be able to sign in.`)) return;
        try {
            if (kind === 'driver') await manage.removeDriver(person.id);
            else await manage.removeStaff(person.id);
            toast.success('Removed');
            load();
        } catch (error) {
            toast.error(errorMessage(error, 'Could not remove this person'));
        }
    };

    const field = (key: keyof NewTeamMember) => ({
        value: form[key] ?? '',
        onChange: (event: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: event.target.value }),
    });

    if (loading) return <div className="p-8 text-gray-500">Loading team...</div>;

    const activeDrivers = drivers.filter(driver => driver.is_active);
    const activeStaff = staff.filter(member => member.is_active);

    return (
        <div className="space-y-10 max-w-4xl animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">Team</h1>
                <p className="text-gray-400 mt-1">Your own drivers and staff. Only your restaurant can see them, and your drivers only get your orders.</p>
            </div>

            <section className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white">Drivers</h2>
                    <button onClick={() => open('driver')} className="flex items-center space-x-2 px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white font-bold rounded-xl text-sm">
                        <Plus size={18} /><span>Add driver</span>
                    </button>
                </div>
                {activeDrivers.length === 0 ? (
                    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 text-center text-gray-500">
                        No drivers yet. Add one so accepted orders can be delivered.
                    </div>
                ) : (
                    <ul className="bg-gray-900 border border-gray-800 rounded-2xl divide-y divide-gray-800">
                        {activeDrivers.map(driver => (
                            <li key={driver.id} className="flex items-center justify-between px-5 py-4">
                                <div className="flex items-center space-x-4 min-w-0">
                                    <span className="w-10 h-10 rounded-xl bg-gray-800 text-gray-400 flex items-center justify-center flex-shrink-0"><Bike size={18} /></span>
                                    <div className="min-w-0">
                                        <p className="font-bold text-white truncate">{driver.name} {driver.sur_name}</p>
                                        <p className="text-sm text-gray-500 truncate">{driver.contact_number} · {driver.vehicle_type}{driver.vehicle_number ? ` (${driver.vehicle_number})` : ''}</p>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-3 flex-shrink-0">
                                    <span className={clsx("px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border", driver.is_available ? "bg-green-500/10 text-green-500 border-green-500/20" : "bg-gray-500/10 text-gray-400 border-gray-500/20")}>
                                        {driver.is_available ? 'Free' : 'Busy / offline'}
                                    </span>
                                    <button aria-label={`Remove ${driver.name}`} onClick={() => remove('driver', driver)} className="p-2 text-gray-500 hover:text-red-500 rounded-lg"><Trash2 size={16} /></button>
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </section>

            <section className="space-y-4">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-xl font-bold text-white">Staff</h2>
                        <p className="text-sm text-gray-500">Staff can handle orders and the menu, but not payments, your plan or the team.</p>
                    </div>
                    <button onClick={() => open('staff')} className="flex items-center space-x-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-xl text-sm flex-shrink-0">
                        <Plus size={18} /><span>Add staff</span>
                    </button>
                </div>
                <ul className="bg-gray-900 border border-gray-800 rounded-2xl divide-y divide-gray-800">
                    {activeStaff.map(member => (
                        <li key={member.id} className="flex items-center justify-between px-5 py-4">
                            <div className="flex items-center space-x-4 min-w-0">
                                <span className="w-10 h-10 rounded-xl bg-gray-800 text-gray-400 flex items-center justify-center flex-shrink-0"><UserRound size={18} /></span>
                                <div className="min-w-0">
                                    <p className="font-bold text-white truncate">{member.name} {member.sur_name}</p>
                                    <p className="text-sm text-gray-500 truncate">{member.email}</p>
                                </div>
                            </div>
                            {member.is_owner ? (
                                <span className="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border bg-brand-500/10 text-brand-400 border-brand-500/20">Owner</span>
                            ) : (
                                <button aria-label={`Remove ${member.name}`} onClick={() => remove('staff', member)} className="p-2 text-gray-500 hover:text-red-500 rounded-lg"><Trash2 size={16} /></button>
                            )}
                        </li>
                    ))}
                </ul>
            </section>

            {adding && (
                <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={() => setAdding(null)}>
                    <form onSubmit={save} onClick={event => event.stopPropagation()} className="bg-gray-900 border border-gray-800 rounded-3xl p-8 w-full max-w-lg space-y-5 max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xl font-bold text-white">{adding === 'driver' ? 'Add a driver' : 'Add a staff member'}</h3>
                            <button type="button" aria-label="Close" onClick={() => setAdding(null)} className="p-2 text-gray-500 hover:text-white"><X size={20} /></button>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className={label} htmlFor="member-name">First name</label>
                                <input id="member-name" required className={input} {...field('name')} />
                            </div>
                            <div>
                                <label className={label} htmlFor="member-surname">Surname</label>
                                <input id="member-surname" required className={input} {...field('sur_name')} />
                            </div>
                        </div>
                        <div>
                            <label className={label} htmlFor="member-phone">Cell number</label>
                            <input id="member-phone" required type="tel" className={input} placeholder="072 123 4567" {...field('contact_number')} />
                        </div>
                        <div>
                            <label className={label} htmlFor="member-email">Email (used to sign in)</label>
                            <input id="member-email" required type="email" className={input} {...field('email')} />
                        </div>
                        <div>
                            <label className={label} htmlFor="member-password">Password (at least 8 characters)</label>
                            <input id="member-password" required minLength={8} type="password" autoComplete="new-password" className={input} {...field('password')} />
                        </div>
                        {adding === 'driver' && (
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className={label} htmlFor="member-vehicle">Vehicle</label>
                                    <input id="member-vehicle" required className={input} placeholder="Motorbike, bicycle, car" {...field('vehicle_type')} />
                                </div>
                                <div>
                                    <label className={label} htmlFor="member-plate">Number plate (optional)</label>
                                    <input id="member-plate" className={input} {...field('vehicle_number')} />
                                </div>
                            </div>
                        )}
                        <button disabled={saving} className="w-full bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold py-3 rounded-xl">
                            {saving ? 'Saving...' : adding === 'driver' ? 'Add driver' : 'Add staff member'}
                        </button>
                    </form>
                </div>
            )}
        </div>
    );
};

export default Team;
