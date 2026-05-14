import React, { useState } from 'react';
import { X, Truck, Loader2 } from 'lucide-react';
import { adminService } from '../../services/adminService';
import type { DriverCreate } from '../../services/adminService';

import { toast } from 'react-hot-toast';

interface AddDriverModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

const AddDriverModal: React.FC<AddDriverModalProps> = ({ isOpen, onClose, onSuccess }) => {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState<DriverCreate>({
        email: '',
        name: '',
        sur_name: '',
        contact_number: '',
        password: '',
        vehicle_type: 'Bike',
        vehicle_number: ''
    });

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            setLoading(true);
            await adminService.createDriver(formData);
            toast.success('Driver created successfully');
            onSuccess();
            onClose();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to create driver');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-md overflow-hidden transform animate-in zoom-in duration-200">
                <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between bg-gray-900/50">
                    <div className="flex items-center space-x-2">
                        <div className="p-2 bg-gold-500/10 rounded-lg text-gold-500">
                            <Truck size={20} />
                        </div>
                        <h2 className="text-xl font-bold text-white">Add New Driver</h2>
                    </div>
                    <button onClick={onClose} className="p-2 text-gray-400 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">First Name</label>
                            <input
                                required
                                type="text"
                                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white focus:ring-1 focus:ring-gold-500 outline-none"
                                value={formData.name}
                                onChange={e => setFormData({ ...formData, name: e.target.value })}
                            />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Surname</label>
                            <input
                                required
                                type="text"
                                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white focus:ring-1 focus:ring-gold-500 outline-none"
                                value={formData.sur_name}
                                onChange={e => setFormData({ ...formData, sur_name: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Email Address</label>
                        <input
                            required
                            type="email"
                            className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white focus:ring-1 focus:ring-gold-500 outline-none"
                            value={formData.email}
                            onChange={e => setFormData({ ...formData, email: e.target.value })}
                        />
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Password</label>
                        <input
                            required
                            type="password"
                            className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white focus:ring-1 focus:ring-gold-500 outline-none"
                            value={formData.password}
                            onChange={e => setFormData({ ...formData, password: e.target.value })}
                        />
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Contact Number</label>
                        <input
                            required
                            type="tel"
                            className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white focus:ring-1 focus:ring-gold-500 outline-none"
                            value={formData.contact_number}
                            onChange={e => setFormData({ ...formData, contact_number: e.target.value })}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Vehicle Type</label>
                            <select
                                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white focus:ring-1 focus:ring-gold-500 outline-none"
                                value={formData.vehicle_type}
                                onChange={e => setFormData({ ...formData, vehicle_type: e.target.value })}
                            >
                                <option value="Bike">Bike</option>
                                <option value="Car">Car</option>
                                <option value="Scooter">Scooter</option>
                            </select>
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Vehicle Number</label>
                            <input
                                type="text"
                                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white focus:ring-1 focus:ring-gold-500 outline-none"
                                value={formData.vehicle_number}
                                onChange={e => setFormData({ ...formData, vehicle_number: e.target.value })}
                                placeholder="Optional"
                            />
                        </div>
                    </div>

                    <div className="pt-4 flex space-x-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-xl transition-all"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className="flex-1 px-4 py-2.5 bg-gold-500 hover:bg-gold-600 disabled:bg-gold-500/50 text-black font-bold rounded-xl transition-all shadow-lg shadow-gold-500/10 flex items-center justify-center space-x-2"
                        >
                            {loading ? <Loader2 size={20} className="animate-spin" /> : <span>Create Driver</span>}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AddDriverModal;
