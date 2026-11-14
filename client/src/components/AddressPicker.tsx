import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, ChevronDown, MapPin, Plus } from 'lucide-react';
import { clsx } from 'clsx';
import { addressLabel, useDeliveryAddress } from '../hooks/useDeliveryAddress';

/** "Deliver to ..." in the customer header: choose which saved address orders go to. */
const AddressPicker = () => {
    const { addresses, chosen, choose, loading } = useDeliveryAddress();
    const [open, setOpen] = useState(false);

    return (
        <div className="relative">
            <button
                onClick={() => setOpen(!open)}
                aria-expanded={open}
                className="flex items-center space-x-2 px-3 py-2 rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 text-sm max-w-[16rem]"
            >
                <MapPin size={16} className="text-brand-500 flex-shrink-0" />
                <span className="text-gray-400 hidden xl:inline">Deliver to</span>
                <span className="font-bold text-white truncate">
                    {loading ? '...' : chosen ? addressLabel(chosen) : 'Add an address'}
                </span>
                <ChevronDown size={14} className={clsx("text-gray-500 flex-shrink-0 transition-transform", open && "rotate-180")} />
            </button>
            {open && (
                <>
                    <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
                    <div className="absolute left-0 mt-2 w-80 bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl z-50 p-2">
                        <p className="px-3 py-2 text-xs font-black uppercase tracking-widest text-gray-500">Deliver to</p>
                        {addresses.map(address => (
                            <button
                                key={address.id}
                                onClick={() => { choose(address.id); setOpen(false); }}
                                className={clsx(
                                    "w-full flex items-start justify-between gap-3 px-3 py-2.5 rounded-xl text-left",
                                    chosen?.id === address.id ? "bg-gray-800" : "hover:bg-gray-800"
                                )}
                            >
                                <span className="min-w-0">
                                    <span className="block font-bold text-white text-sm truncate">{addressLabel(address)}</span>
                                    <span className="block text-xs text-gray-500 truncate">{address.formatted_address}</span>
                                </span>
                                {chosen?.id === address.id && <Check size={16} className="text-brand-500 mt-1 flex-shrink-0" />}
                            </button>
                        ))}
                        <Link
                            to="/customer/profile"
                            onClick={() => setOpen(false)}
                            className="flex items-center space-x-2 px-3 py-2.5 rounded-xl text-sm font-bold text-brand-500 hover:bg-gray-800"
                        >
                            <Plus size={16} /><span>{addresses.length ? 'Add or change addresses' : 'Add your delivery address'}</span>
                        </Link>
                    </div>
                </>
            )}
        </div>
    );
};

export default AddressPicker;
