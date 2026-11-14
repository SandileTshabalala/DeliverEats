import { useEffect, useState } from 'react';
import { Bike, Store } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { AccountDetailsCard, PasswordCard } from '../../components/AccountSettings';
import { errorMessage } from '../../services/billing';
import { driverService } from '../../services/drivers';
import type { DriverProfile } from '../../services/drivers';

const card = "bg-gray-900 border border-gray-800 rounded-2xl p-6 md:p-8 space-y-5";
const input = "w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-2.5 text-white placeholder-gray-600 focus:border-brand-500 outline-none";
const label = "block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5";

const VEHICLES = ['Motorbike', 'Bicycle', 'Car', 'Bakkie', 'On foot'];

const DriverSettings = () => {
    const [profile, setProfile] = useState<DriverProfile | null>(null);
    const [vehicle, setVehicle] = useState({ vehicle_type: '', vehicle_number: '' });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        driverService.getProfile()
            .then(loaded => {
                setProfile(loaded);
                setVehicle({ vehicle_type: loaded.vehicle_type ?? '', vehicle_number: loaded.vehicle_number ?? '' });
            })
            .catch(error => toast.error(errorMessage(error, 'Could not load your settings')))
            .finally(() => setLoading(false));
    }, []);

    const saveVehicle = async (event: React.FormEvent) => {
        event.preventDefault();
        setSaving(true);
        try {
            const saved = await driverService.updateProfile({
                vehicle_type: vehicle.vehicle_type.trim(),
                vehicle_number: vehicle.vehicle_number.trim() || undefined,
            });
            setProfile(saved);
            toast.success('Vehicle saved');
        } catch (error) {
            toast.error(errorMessage(error, 'Could not save your vehicle'));
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div className="p-8 text-gray-500">Loading settings...</div>;

    // a type saved before this list existed still shows up as an option
    const options = vehicle.vehicle_type && !VEHICLES.includes(vehicle.vehicle_type)
        ? [vehicle.vehicle_type, ...VEHICLES]
        : VEHICLES;

    return (
        <div className="space-y-8 max-w-3xl animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">Settings</h1>
                <p className="text-gray-400 mt-1">Your vehicle, your details and your password.</p>
            </div>

            <section className={card}>
                <div className="flex items-start space-x-4">
                    <span className="w-12 h-12 rounded-2xl bg-brand-500/10 text-brand-500 flex items-center justify-center flex-shrink-0"><Store size={22} /></span>
                    <div>
                        <h2 className="text-xl font-bold text-white">Who you deliver for</h2>
                        {profile?.restaurant_name ? (
                            <p className="text-sm text-gray-400 mt-1">
                                You deliver for <span className="text-white font-bold">{profile.restaurant_name}</span>. You only receive this restaurant's orders.
                                To stop, ask the restaurant to remove you from their team.
                            </p>
                        ) : (
                            <p className="text-sm text-gray-400 mt-1">
                                Your account is not linked to a restaurant yet. Ask the restaurant you work for to add you on their Team page.
                            </p>
                        )}
                    </div>
                </div>
            </section>

            <form onSubmit={saveVehicle} className={card}>
                <div className="flex items-start space-x-4">
                    <span className="w-12 h-12 rounded-2xl bg-brand-500/10 text-brand-500 flex items-center justify-center flex-shrink-0"><Bike size={22} /></span>
                    <div>
                        <h2 className="text-xl font-bold text-white">Your vehicle</h2>
                        <p className="text-sm text-gray-500 mt-1">The restaurant sees this next to your name on each order.</p>
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className={label} htmlFor="vehicle-type">Type</label>
                        <select id="vehicle-type" required className={input} value={vehicle.vehicle_type} onChange={e => setVehicle({ ...vehicle, vehicle_type: e.target.value })}>
                            <option value="" disabled>Choose...</option>
                            {options.map(option => <option key={option} value={option}>{option}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className={label} htmlFor="vehicle-plate">Number plate (optional)</label>
                        <input id="vehicle-plate" maxLength={20} className={input} placeholder="ABC 123 MP" value={vehicle.vehicle_number} onChange={e => setVehicle({ ...vehicle, vehicle_number: e.target.value })} />
                    </div>
                </div>
                <button disabled={saving} className="px-6 py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white font-bold rounded-xl">
                    {saving ? 'Saving...' : 'Save vehicle'}
                </button>
            </form>

            <AccountDetailsCard hint="Customers and the restaurant call this number about a delivery, and new jobs are sent to it by SMS." />
            <PasswordCard />
        </div>
    );
};

export default DriverSettings;
