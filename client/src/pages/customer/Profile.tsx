import { useState, useEffect, useRef, useMemo } from 'react';
import debounce from 'debounce';
import {
    User,
    MapPin,
    Phone,
    Mail,
    Plus,
    Trash2,
    Edit2,
    Navigation,
    CheckCircle2,
    Save,
    X,
    Search
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';
import api from '../../services/api';
import { clsx } from 'clsx';


interface Address {
    id: string;
    latitude: number;
    longitude: number;
    formatted_address: string;
    suburb: string | null;
    city: string | null;
    instructions: string | null;
    is_default: boolean;
}

const CustomerProfile = () => {
    const { user, reloadUser } = useAuth();
    const [addresses, setAddresses] = useState<Address[]>([]);
    const [loading, setLoading] = useState(true);
    const [isEditingProfile, setIsEditingProfile] = useState(false);
    const [profileForm, setProfileForm] = useState({
        name: user?.name || '',
        sur_name: user?.sur_name || '',
        contact_number: user?.contact_number || '',
        email: user?.email || ''
    });

    // Sync form with user data when user changes
    useEffect(() => {
        if (user) {
            setProfileForm({
                name: user.name || '',
                sur_name: user.sur_name || '',
                contact_number: user.contact_number || '',
                email: user.email || ''
            });
        }
    }, [user]);

    const [addressForm, setAddressForm] = useState({
        query: '',
        instructions: '',
        is_default: false
    });

    const [addressResults, setAddressResults] = useState<any[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const searchCache = useRef<Record<string, any[]>>({});

    useEffect(() => {
        fetchAddresses();
    }, []);

    // Debounced address search for autocomplete
    useEffect(() => {
        if (addressForm.query.length === 0) {
            setAddressResults([]);
            return;
        }

        handleSearchAddress(true);
    }, [addressForm.query]);

    // useEffect(() => {
    //     const timer = setTimeout(() => {
    //         if (addressForm.query.length > 3) {
    //             handleSearchAddress(true);
    //         } else if (addressForm.query.length === 0) {
    //             setAddressResults([]);
    //         }
    //     }, 500);

    //     return () => clearTimeout(timer);
    // }, [addressForm.query]);

    const fetchAddresses = async () => {
        try {
            const response = await api.get('/users/me');
            setAddresses(response.data.addresses || []);
        } catch (error) {
            console.error('Failed to fetch addresses');
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await api.patch('/users/me', profileForm);
            await reloadUser(); // Refresh global state
            toast.success("Profile updated successfully!");
            setIsEditingProfile(false);
        } catch (error: any) {
            toast.error(error.response?.data?.detail || "Failed to update profile");
        }
    };

    const handleAddAddressByLocation = () => {
        if (!navigator.geolocation) {
            toast.error("Geolocation is not supported by your browser");
            return;
        }

        toast.loading("Detecting location...");
        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const { latitude, longitude } = position.coords;
                try {
                    const response = await api.get(`/addresses/reverse-geocode?lat=${latitude}&lng=${longitude}`);
                    const result = {
                        display_name: response.data.display_name,
                        lat: latitude.toString(),
                        lon: longitude.toString(),
                        is_gps: true
                    };
                    setAddressResults([result]);
                    toast.dismiss();
                    toast.success("Location detected! See suggestion below.");
                } catch {
                    toast.dismiss();
                    toast.error("Failed to get address metadata");
                }
            },
            () => {
                toast.dismiss();
                toast.error("Could not get precise location. Try high accuracy or add manually.");
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    };
    const debouncedSearch = useMemo(
        () => debounce(async (query: string, silent: boolean) => {
            try {
                const response = await api.get(`/addresses/geocode?q=${query}`);
                searchCache.current[query] = response.data;
                setAddressResults(response.data);

                if (!silent && response.data.length === 0) {
                    toast.error("No addresses found. Try a different search.");
                }
            } catch {
                if (!silent) toast.error("Search failed");
            } finally {
                setIsSearching(false);
            }
        }, 350),
        []
    );

    const handleSearchAddress = (silent = false) => {
        const query = addressForm.query.trim().toLowerCase();
        if (query.length < 3) return;

        // cache check FIRST and synchronous
        if (searchCache.current[query]) {
            setAddressResults(searchCache.current[query]);
            setIsSearching(false);
            return;
        }

        setIsSearching(true);
        debouncedSearch(query, silent);
    };



    const handleSelectResult = async (result: any) => {
        try {
            const response = await api.post('/addresses', {
                latitude: parseFloat(result.lat),
                longitude: parseFloat(result.lon),
                instructions: addressForm.instructions,
                is_default: addresses.length === 0 || addressForm.is_default
            });
            setAddresses([...addresses, response.data]);
            setAddressForm({ query: '', instructions: '', is_default: false });
            setAddressResults([]);
            toast.success("Address added!");
        } catch (error: any) {
            toast.error("Failed to add address");
        }
    };

    const handleDeleteAddress = async (id: string) => {
        if (!confirm("Are you sure you want to delete this address?")) return;
        try {
            await api.delete(`/addresses/${id}`);
            setAddresses(addresses.filter(a => a.id !== id));
            toast.success("Address deleted");
        } catch (error: any) {
            toast.error("Failed to delete address");
        }
    };

    const handleSetDefaultAddress = async (id: string) => {
        try {
            const address = addresses.find(a => a.id === id);
            if (!address) return;

            const response = await api.put(`/addresses/${id}`, {
                ...address,
                is_default: true
            });

            setAddresses(addresses.map(a =>
                a.id === id ? response.data : { ...a, is_default: false }
            ));
            toast.success("Default address updated");
        } catch (error: any) {
            toast.error("Failed to set default address");
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-12 animate-in fade-in duration-500 pb-20">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-4xl font-black uppercase tracking-tighter italic">Your Profile</h1>
                    <p className="text-gray-500 font-medium">Manage your info and delivery spots</p>
                </div>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Profile Card */}
                <div className="md:col-span-1">
                    <div className="bg-gray-900 border border-gray-800 rounded-[32px] p-8 space-y-6 sticky top-24">
                        <div className="w-24 h-24 bg-brand-600 rounded-3xl flex items-center justify-center text-white shadow-xl shadow-brand-600/20 mx-auto">
                            <User size={48} />
                        </div>

                        <div className="text-center">
                            <h2 className="text-2xl font-black uppercase tracking-tight italic">{user?.name} {user?.sur_name}</h2>
                            <p className="text-gray-500 text-sm font-bold uppercase tracking-widest">{user?.role}</p>
                        </div>

                        {!isEditingProfile ? (
                            <div className="space-y-4 pt-4">
                                <div className="flex items-center space-x-3 text-gray-400">
                                    <Mail size={16} className="text-brand-500" />
                                    <span className="text-xs font-bold truncate">{user?.email}</span>
                                </div>
                                <div className="flex items-center space-x-3 text-gray-400">
                                    <Phone size={16} className="text-brand-500" />
                                    <span className="text-xs font-bold uppercase tracking-wider">{user?.contact_number || 'No contact set'}</span>
                                </div>
                                <button
                                    onClick={() => setIsEditingProfile(true)}
                                    className="w-full mt-4 flex items-center justify-center space-x-2 py-3 bg-gray-800 hover:bg-gray-700 text-white text-xs font-black uppercase tracking-widest rounded-xl transition-all"
                                >
                                    <Edit2 size={14} />
                                    <span>Edit Profile</span>
                                </button>
                            </div>
                        ) : (
                            <form onSubmit={handleUpdateProfile} className="space-y-4 pt-4">
                                <div className="space-y-1">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-gray-500">Name</label>
                                    <input
                                        type="text"
                                        value={profileForm.name}
                                        onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                                        className="w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-2 text-white text-sm outline-none focus:border-brand-500 transition-all font-bold"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-gray-500">Surname</label>
                                    <input
                                        type="text"
                                        value={profileForm.sur_name}
                                        onChange={(e) => setProfileForm({ ...profileForm, sur_name: e.target.value })}
                                        className="w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-2 text-white text-sm outline-none focus:border-brand-500 transition-all font-bold"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-gray-500">Contact</label>
                                    <input
                                        type="text"
                                        value={profileForm.contact_number}
                                        onChange={(e) => setProfileForm({ ...profileForm, contact_number: e.target.value })}
                                        className="w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-2 text-white text-sm outline-none focus:border-brand-500 transition-all font-bold"
                                    />
                                </div>
                                <div className="flex space-x-2 pt-2">
                                    <button
                                        type="submit"
                                        className="flex-1 py-3 bg-brand-600 hover:bg-brand-500 text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all flex items-center justify-center space-x-2"
                                    >
                                        <Save size={14} />
                                        <span>Save</span>
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setIsEditingProfile(false)}
                                        className="py-3 px-4 bg-gray-800 hover:bg-gray-700 text-white rounded-xl transition-all"
                                    >
                                        <X size={14} />
                                    </button>
                                </div>
                            </form>
                        )}
                    </div>
                </div>

                {/* Addresses Section */}
                <div className="md:col-span-2 space-y-8">
                    {/* Manual Entry Form */}
                    <div className="bg-gray-900 border border-gray-800 rounded-[32px] p-8 space-y-6">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xl font-black uppercase tracking-tighter italic flex items-center space-x-2">
                                <Plus className="text-brand-500" />
                                <span>Add New Spot</span>
                            </h3>
                            <button
                                onClick={handleAddAddressByLocation}
                                className="flex items-center space-x-2 px-4 py-2 bg-brand-600/10 hover:bg-brand-600/20 text-brand-500 text-[10px] font-black uppercase tracking-widest rounded-xl transition-all"
                            >
                                <Navigation size={14} />
                                <span>Use GPS</span>
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div className="relative">
                                <input
                                    type="text"
                                    placeholder="Enter street address, building or complex..."
                                    value={addressForm.query}
                                    onChange={(e) => setAddressForm({ ...addressForm, query: e.target.value })}
                                    onKeyDown={(e) => e.key === 'Enter' && handleSearchAddress()}
                                    className="w-full bg-gray-950 border border-gray-800 rounded-2xl pl-12 pr-4 py-4 text-white outline-none focus:border-brand-500 transition-all font-bold"
                                />
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600" size={20} />
                                <button
                                    onClick={() => handleSearchAddress(false)}
                                    disabled={isSearching || !addressForm.query}
                                    className="absolute right-2 top-2 bottom-2 px-4 bg-brand-600 hover:bg-brand-500 disabled:bg-gray-800 text-white rounded-xl text-[10px] font-black uppercase tracking-widest transition-all"
                                >
                                    {isSearching ? '...' : 'Search'}
                                </button>
                            </div>

                            <AnimatePresence>
                                {addressResults.length > 0 && (
                                    <motion.div
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: 'auto', opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        className="space-y-2 max-h-60 overflow-y-auto pr-2 custom-scrollbar"
                                    >
                                        <p className="text-[10px] font-black uppercase tracking-widest text-gray-500 ml-1">Search Results</p>
                                        {addressResults.map((result, idx) => (
                                            <button
                                                key={idx}
                                                onClick={() => handleSelectResult(result)}
                                                className={clsx(
                                                    "w-full text-left p-4 bg-gray-950 border rounded-2xl transition-all group",
                                                    result.is_gps ? "border-brand-500 bg-brand-500/5 shadow-lg shadow-brand-500/10" : "border-gray-800 hover:border-brand-500/50"
                                                )}
                                            >
                                                <div className="flex items-center space-x-3">
                                                    {result.is_gps && <Navigation size={14} className="text-brand-500 animate-pulse" />}
                                                    <p className="text-xs font-bold text-white group-hover:text-brand-500 transition-colors flex-1">{result.display_name}</p>
                                                    {result.is_gps && <span className="text-[8px] font-black uppercase text-brand-500 bg-brand-500/10 px-2 py-1 rounded">My Current Spot</span>}
                                                </div>
                                            </button>
                                        ))}
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            <input
                                type="text"
                                placeholder="Delivery instructions (e.g. Ring bell at gate 4)"
                                value={addressForm.instructions}
                                onChange={(e) => setAddressForm({ ...addressForm, instructions: e.target.value })}
                                className="w-full bg-gray-950 border border-gray-800 rounded-2xl px-4 py-4 text-white text-xs outline-none focus:border-brand-500 transition-all"
                            />
                        </div>
                    </div>

                    <div className="space-y-6">
                        <h3 className="text-xl font-black uppercase tracking-tighter italic flex items-center space-x-2">
                            <MapPin className="text-brand-500" />
                            <span>Saved Addresses</span>
                        </h3>

                        <div className="space-y-4">
                            {loading ? (
                                <div className="p-12 text-center text-gray-500 animate-pulse uppercase tracking-widest text-xs font-black">Loading spots...</div>
                            ) : addresses.length === 0 ? (
                                <div className="bg-gray-900/30 border-2 border-dashed border-gray-800 rounded-[32px] p-12 text-center space-y-4">
                                    <div className="w-16 h-16 bg-gray-800 rounded-2xl flex items-center justify-center mx-auto text-gray-600">
                                        <MapPin size={32} />
                                    </div>
                                    <p className="text-gray-500 font-bold uppercase tracking-tight">No delivery spots saved yet</p>
                                    <button
                                        onClick={handleAddAddressByLocation}
                                        className="px-6 py-3 bg-brand-600 text-white text-xs font-black uppercase tracking-widest rounded-xl hover:bg-brand-500 transition-all shadow-lg shadow-brand-600/20"
                                    >
                                        Add Your First Spot
                                    </button>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 gap-4">
                                    <AnimatePresence mode="popLayout">
                                        {addresses.map((address) => (
                                            <motion.div
                                                key={address.id}
                                                layout
                                                initial={{ opacity: 0, y: 20 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                exit={{ opacity: 0, scale: 0.95 }}
                                                className={clsx(
                                                    "bg-gray-900/50 border rounded-[24px] p-6 flex items-start justify-between group transition-all",
                                                    address.is_default ? "border-brand-500/50 bg-brand-500/5" : "border-gray-800 hover:border-gray-700"
                                                )}
                                            >
                                                <div className="flex items-start space-x-4">
                                                    <div className={clsx(
                                                        "w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 transition-all",
                                                        address.is_default ? "bg-brand-600 text-white" : "bg-gray-800 text-gray-500 group-hover:bg-gray-700"
                                                    )}>
                                                        <MapPin size={24} />
                                                    </div>
                                                    <div className="space-y-1">
                                                        <div className="flex items-center space-x-2">
                                                            <h4 className="font-black uppercase tracking-tight italic text-lg leading-tight truncate max-w-[200px] md:max-w-xs">{address.suburb || 'My Spot'}</h4>
                                                            {address.is_default && (
                                                                <span className="flex items-center space-x-1 px-2 py-0.5 bg-brand-600 text-white text-[8px] font-black uppercase tracking-widest rounded-full">
                                                                    <CheckCircle2 size={8} />
                                                                    <span>Default</span>
                                                                </span>
                                                            )}
                                                        </div>
                                                        <p className="text-gray-500 text-xs font-medium leading-relaxed">{address.formatted_address}</p>
                                                        {address.instructions && (
                                                            <p className="text-brand-500/70 text-[10px] font-bold uppercase tracking-wider mt-2 bg-brand-500/5 px-2 py-1 rounded-lg inline-block">
                                                                Note: {address.instructions}
                                                            </p>
                                                        )}
                                                    </div>
                                                </div>

                                                <div className="flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    {!address.is_default && (
                                                        <button
                                                            onClick={() => handleSetDefaultAddress(address.id)}
                                                            className="p-2 text-gray-500 hover:text-brand-500 hover:bg-brand-500/10 rounded-xl transition-all"
                                                            title="Set as Default"
                                                        >
                                                            <CheckCircle2 size={18} />
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => handleDeleteAddress(address.id)}
                                                        className="p-2 text-gray-500 hover:text-red-500 hover:bg-red-500/10 rounded-xl transition-all"
                                                        title="Delete"
                                                    >
                                                        <Trash2 size={18} />
                                                    </button>
                                                </div>
                                            </motion.div>
                                        ))}
                                    </AnimatePresence>

                                    <button
                                        onClick={handleAddAddressByLocation}
                                        className="w-full py-6 border-2 border-dashed border-gray-800 rounded-[24px] text-gray-600 hover:text-brand-500 hover:border-brand-500/50 hover:bg-brand-500/5 transition-all flex flex-col items-center justify-center space-y-2 group"
                                    >
                                        <div className="p-3 bg-gray-800 rounded-2xl group-hover:bg-brand-600 group-hover:text-white transition-all">
                                            <Plus size={24} />
                                        </div>
                                        <span className="text-[10px] font-black uppercase tracking-widest">Add New Delivery Location</span>
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CustomerProfile;
