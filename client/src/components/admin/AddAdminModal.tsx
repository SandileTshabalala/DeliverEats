import React, { useState } from 'react';
import { X, Shield, Loader2 } from 'lucide-react';
import { adminService } from '../../services/adminService';
import type { SuperAdminCreate } from '../../services/adminService';

import { Roles } from '../../utils/roles';
import { toast } from 'react-hot-toast';

interface AddAdminModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

const AddAdminModal: React.FC<AddAdminModalProps> = ({ isOpen, onClose, onSuccess }) => {
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState<SuperAdminCreate>({
        email: '',
        name: '',
        sur_name: '',
        contact_number: '',
        password: '',
        role: Roles.SUPER_ADMIN
    });

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            setLoading(true);
            await adminService.createSuperAdmin(formData);
            toast.success('Administrator created successfully');
            onSuccess();
            onClose();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to create administrator');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-md overflow-hidden transform animate-in zoom-in duration-200">
                <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between bg-gray-900/50">
                    <div className="flex items-center space-x-2">
                        <div className="p-2 bg-purple-500/10 rounded-lg text-purple-400">
                            <Shield size={20} />
                        </div>
                        <h2 className="text-xl font-bold text-white">Add Administrator</h2>
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
                                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white focus:ring-1 focus:ring-brand-500 outline-none"
                                value={formData.name}
                                onChange={e => setFormData({ ...formData, name: e.target.value })}
                            />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Surname</label>
                            <input
                                required
                                type="text"
                                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white focus:ring-1 focus:ring-brand-500 outline-none"
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
                            className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white focus:ring-1 focus:ring-brand-500 outline-none"
                            value={formData.email}
                            onChange={e => setFormData({ ...formData, email: e.target.value })}
                        />
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Password</label>
                        <input
                            required
                            type="password"
                            className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white focus:ring-1 focus:ring-brand-500 outline-none"
                            value={formData.password}
                            onChange={e => setFormData({ ...formData, password: e.target.value })}
                        />
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Contact Number</label>
                        <input
                            required
                            type="tel"
                            className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white focus:ring-1 focus:ring-brand-500 outline-none"
                            value={formData.contact_number}
                            onChange={e => setFormData({ ...formData, contact_number: e.target.value })}
                        />
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Access Level</label>
                        <select
                            className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-white focus:ring-1 focus:ring-brand-500 outline-none"
                            value={formData.role}
                            onChange={e => setFormData({ ...formData, role: e.target.value as any })}
                        >
                            <option value={Roles.SUPER_ADMIN}>Super Admin</option>
                            <option value={Roles.ADMIN}>Admin</option>
                        </select>
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
                            className="flex-1 px-4 py-2.5 bg-brand-500 hover:bg-brand-600 disabled:bg-brand-500/50 text-black font-bold rounded-xl transition-all shadow-lg shadow-brand-500/10 flex items-center justify-center space-x-2"
                        >
                            {loading ? <Loader2 size={20} className="animate-spin" /> : <span>Create Account</span>}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AddAdminModal;
