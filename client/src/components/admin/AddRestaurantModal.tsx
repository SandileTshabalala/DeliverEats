import React, { useState } from 'react';
import { X, Store, Loader2 } from 'lucide-react';
import { adminService } from '../../services/adminService';
import type { RestaurantCreate } from '../../services/adminService';
import { toast } from 'react-hot-toast';

interface AddRestaurantModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

const AddRestaurantModal: React.FC<AddRestaurantModalProps> = ({ isOpen, onClose, onSuccess }) => {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState<RestaurantCreate>({
        name: '',
        address: '',
        description: '',
        admin_email: '',
        admin_password: '',
        admin_name: '',
        admin_sur_name: '',
        admin_contact_number: ''
    });

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            setLoading(true);
            await adminService.createRestaurant(formData);
            toast.success('Restaurant and admin created successfully');
            onSuccess();
            onClose();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to create restaurant');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-gray-900 border border-gray-800 rounded-3xl w-full max-w-2xl overflow-hidden transform animate-in zoom-in duration-200 max-h-[90vh] flex flex-col">
                <div className="px-8 py-6 border-b border-gray-800 flex items-center justify-between bg-gray-900/50">
                    <div className="flex items-center space-x-3">
                        <div className="p-2.5 bg-blue-500/10 rounded-xl text-blue-400">
                            <Store size={24} />
                        </div>
                        <h2 className="text-2xl font-bold text-white tracking-tight">Add New Restaurant</h2>
                    </div>
                    <button onClick={onClose} className="p-2 text-gray-400 hover:text-white transition-colors">
                        <X size={24} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-8 overflow-y-auto custom-scrollbar">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        {/* Restaurant Details */}
                        <div className="space-y-5">
                            <h3 className="text-sm font-bold text-gold-500 uppercase tracking-widest flex items-center space-x-2">
                                <span>Restaurant Information</span>
                            </h3>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Restaurant Name</label>
                                <input
                                    required
                                    type="text"
                                    className="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white focus:ring-1 focus:ring-gold-500 outline-none transition-all"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Address</label>
                                <input
                                    required
                                    type="text"
                                    className="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white focus:ring-1 focus:ring-gold-500 outline-none transition-all"
                                    value={formData.address}
                                    onChange={e => setFormData({ ...formData, address: e.target.value })}
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Description</label>
                                <textarea
                                    className="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white focus:ring-1 focus:ring-gold-500 outline-none transition-all resize-none h-32"
                                    value={formData.description}
                                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                                    placeholder="Brief description of the restaurant..."
                                />
                            </div>
                        </div>

                        {/* Admin Details */}
                        <div className="space-y-5">
                            <h3 className="text-sm font-bold text-blue-400 uppercase tracking-widest flex items-center space-x-2">
                                <span>Admin Account</span>
                            </h3>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Admin Name</label>
                                    <input
                                        required
                                        type="text"
                                        className="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white focus:ring-1 focus:ring-gold-500 outline-none transition-all"
                                        value={formData.admin_name}
                                        onChange={e => setFormData({ ...formData, admin_name: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Admin Surname</label>
                                    <input
                                        required
                                        type="text"
                                        className="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white focus:ring-1 focus:ring-gold-500 outline-none transition-all"
                                        value={formData.admin_sur_name}
                                        onChange={e => setFormData({ ...formData, admin_sur_name: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Admin Email</label>
                                <input
                                    required
                                    type="email"
                                    className="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white focus:ring-1 focus:ring-gold-500 outline-none transition-all"
                                    value={formData.admin_email}
                                    onChange={e => setFormData({ ...formData, admin_email: e.target.value })}
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Admin Password</label>
                                <input
                                    required
                                    type="password"
                                    className="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white focus:ring-1 focus:ring-gold-500 outline-none transition-all"
                                    value={formData.admin_password}
                                    onChange={e => setFormData({ ...formData, admin_password: e.target.value })}
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Contact Number</label>
                                <input
                                    required
                                    type="tel"
                                    className="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white focus:ring-1 focus:ring-gold-500 outline-none transition-all"
                                    value={formData.admin_contact_number}
                                    onChange={e => setFormData({ ...formData, admin_contact_number: e.target.value })}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="mt-10 flex space-x-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 px-6 py-3.5 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-2xl transition-all"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className="flex-1 px-6 py-3.5 bg-gold-500 hover:bg-gold-600 disabled:bg-gold-500/50 text-black font-bold rounded-2xl transition-all shadow-xl shadow-gold-500/20 flex items-center justify-center space-x-2"
                        >
                            {loading ? <Loader2 size={24} className="animate-spin" /> : <span>Create Restaurant</span>}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AddRestaurantModal;
