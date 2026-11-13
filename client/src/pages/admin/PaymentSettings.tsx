import React, { useState, useEffect } from 'react';
import {
    Plus,
    Trash2,
    Edit2,
    Save,
    CheckCircle,
    ToggleLeft,
    ToggleRight,
    Shield,
} from 'lucide-react';
import { adminService } from '../../services/adminService';
import type { PaymentProvider } from '../../services/adminService';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';

interface ProviderFormProps {
    id?: string;
    formData: Partial<PaymentProvider>;
    setFormData: React.Dispatch<React.SetStateAction<Partial<PaymentProvider>>>;
    onSave: (id?: string) => void;
    onCancel: () => void;
}

const ProviderForm: React.FC<ProviderFormProps> = ({ id, formData, setFormData, onSave, onCancel }) => (
    <div className="space-y-6 bg-gray-900 border border-brand-500/30 rounded-2xl p-6 shadow-2xl animate-in zoom-in-95 duration-300">
        <h3 className="text-xl font-bold text-brand-500 flex items-center gap-2">
            {id ? <Edit2 size={24} /> : <Plus size={24} />}
            {id ? 'Edit Gateway' : 'New Gateway'}
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
                <div>
                    <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5 ml-1">Gateway ID (payfast, stripe, cash_delivery)</label>
                    <input
                        type="text"
                        value={formData.provider_name || ''}
                        onChange={e => setFormData({ ...formData, provider_name: e.target.value })}
                        className="w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-3 text-sm text-white focus:border-brand-500 outline-none transition-all"
                        placeholder="Unique identifier"
                    />
                </div>
                <div>
                    <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5 ml-1">Display Name (e.g. Credit Card)</label>
                    <input
                        type="text"
                        value={formData.display_name || ''}
                        onChange={e => setFormData({ ...formData, display_name: e.target.value })}
                        className="w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-3 text-sm text-white focus:border-brand-500 outline-none transition-all"
                        placeholder="What customer sees"
                    />
                </div>
            </div>

            <div className="space-y-4">
                <div>
                    <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5 ml-1">Public Key (PayFast: Merchant ID)</label>
                    <input
                        type="text"
                        value={formData.public_key || ''}
                        onChange={e => setFormData({ ...formData, public_key: e.target.value })}
                        className="w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-3 text-sm text-white focus:border-brand-500 outline-none transition-all"
                        placeholder="PayFast merchant ID or pk_test_..."
                    />
                </div>
                <div>
                    <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-1.5 ml-1">Secret Key (PayFast: Merchant Key)</label>
                    <input
                        type="password"
                        value={formData.secret_key || ''}
                        onChange={e => setFormData({ ...formData, secret_key: e.target.value })}
                        className="w-full bg-gray-950 border border-gray-800 rounded-xl px-4 py-3 text-sm text-white focus:border-brand-500 outline-none transition-all"
                        placeholder="Leave as is to keep the saved key"
                    />
                </div>
            </div>
        </div>

        <div className="bg-gray-950 border border-gray-800 rounded-xl p-4">
            <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 ml-1">Advanced Config (JSON) - PayFast: passphrase and sandbox</label>
            <textarea
                value={formData.config ? JSON.stringify(formData.config, null, 2) : '{}'}
                onChange={e => {
                    try {
                        const json = JSON.parse(e.target.value);
                        setFormData({ ...formData, config: json });
                    } catch (err) { /* silent */ }
                }}
                rows={4}
                className="w-full bg-transparent border-none focus:ring-0 text-xs font-mono text-brand-400 resize-none h-24"
                placeholder='{ "passphrase": "...", "sandbox": true }'
            />
        </div>

        <div className="flex justify-end space-x-4 pt-2">
            <button
                onClick={onCancel}
                className="px-6 py-2.5 text-sm font-bold text-gray-500 hover:text-white transition-colors"
            >
                Cancel
            </button>
            <button
                onClick={() => onSave(id)}
                className="bg-brand-600 hover:bg-brand-500 text-black px-8 py-2.5 rounded-xl text-sm font-black uppercase tracking-widest shadow-lg shadow-brand-600/20 active:scale-95 transition-all flex items-center gap-2"
            >
                <Save size={18} />
                {id ? 'Update Gateway' : 'Save Gateway'}
            </button>
        </div>
    </div>
);

const PaymentSettings: React.FC = () => {
    const [providers, setProviders] = useState<PaymentProvider[]>([]);
    const [loading, setLoading] = useState(true);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [isAdding, setIsAdding] = useState(false);
    const [formData, setFormData] = useState<Partial<PaymentProvider>>({});

    useEffect(() => {
        fetchProviders();
    }, []);

    const fetchProviders = async () => {
        try {
            const data = await adminService.getPaymentProviders();
            setProviders(data);
        } catch (error) {
            toast.error('Failed to fetch payment providers');
        } finally {
            setLoading(false);
        }
    };

    const handleToggleEnabled = async (provider: PaymentProvider) => {
        try {
            const updatedProvider = await adminService.updatePaymentProvider(provider.id, { enabled: !provider.enabled });
            setProviders(providers.map(p => p.id === provider.id ? updatedProvider : p));
            toast.success(`${provider.display_name} ${!provider.enabled ? 'enabled' : 'disabled'}`);
        } catch (error) {
            toast.error('Failed to update provider status');
        }
    };

    const handleSave = async (id?: string) => {
        try {
            let updatedProvider: PaymentProvider;
            if (id) {
                updatedProvider = await adminService.updatePaymentProvider(id, formData);
                setProviders(providers.map(p => p.id === id ? updatedProvider : p));
                setEditingId(null);
            } else {
                updatedProvider = await adminService.createPaymentProvider(formData);
                setProviders([...providers, updatedProvider]);
                setIsAdding(false);
            }

            setFormData({});
            toast.success('Provider saved successfully');
        } catch (error) {
            toast.error('Failed to save provider');
        }
    };

    const handleDelete = async (id: string) => {
        if (!window.confirm('Are you sure you want to delete this provider?')) return;
        try {
            await adminService.deletePaymentProvider(id);
            setProviders(providers.filter(p => p.id !== id));
            toast.success('Provider deleted');
        } catch (error) {
            toast.error('Failed to delete provider');
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-4xl font-black text-white italic uppercase tracking-tighter">Gateways</h2>
                    <p className="text-gray-500 font-bold uppercase tracking-widest text-[10px] mt-1">Configure processing & manual methods</p>
                </div>
                {!isAdding && (
                    <button
                        onClick={() => {
                            setIsAdding(true);
                            setEditingId(null);
                            setFormData({ enabled: true, is_active: true });
                        }}
                        className="flex items-center space-x-2 bg-white hover:bg-brand-500 text-black px-6 py-3 rounded-2xl font-black uppercase tracking-widest text-xs transition-all shadow-xl active:scale-95 group"
                    >
                        <Plus size={18} className="group-hover:rotate-90 transition-transform duration-300" />
                        <span>Add Gateway</span>
                    </button>
                )}
            </div>

            <div className="grid grid-cols-1 gap-8">
                {isAdding && !editingId && (
                    <ProviderForm
                        formData={formData}
                        setFormData={setFormData}
                        onSave={handleSave}
                        onCancel={() => { setIsAdding(false); setEditingId(null); setFormData({}); }}
                    />
                )}

                {providers.map((provider) => (
                    <div key={provider.id}>
                        {editingId === provider.id ? (
                            <ProviderForm
                                id={provider.id}
                                formData={formData}
                                setFormData={setFormData}
                                onSave={handleSave}
                                onCancel={() => { setEditingId(null); setFormData({}); }}
                            />
                        ) : (
                            <div className="bg-gray-900/50 border border-gray-800 rounded-3xl overflow-hidden group hover:border-gray-700 transition-all duration-300">
                                <div className="p-8">
                                    <div className="flex items-start justify-between">
                                        <div className="flex items-center space-x-6">
                                            <div className="w-16 h-16 bg-gray-950 border border-gray-800 rounded-2xl flex items-center justify-center text-brand-500 shadow-inner group-hover:scale-110 transition-transform duration-500">
                                                <Shield size={32} />
                                            </div>
                                            <div>
                                                <h3 className="text-2xl font-black text-white italic uppercase tracking-tight">{provider.display_name}</h3>
                                                <div className="flex items-center gap-2 mt-1">
                                                    <span className="text-[10px] bg-gray-800 text-gray-500 px-2 py-0.5 rounded uppercase font-bold tracking-widest">{provider.provider_name}</span>
                                                    {provider.enabled ? (
                                                        <span className="text-[10px] bg-green-500/10 text-green-500 px-2 py-0.5 rounded uppercase font-bold tracking-widest flex items-center gap-1">
                                                            <CheckCircle size={10} /> Live
                                                        </span>
                                                    ) : (
                                                        <span className="text-[10px] bg-gray-800 text-gray-400 px-2 py-0.5 rounded uppercase font-bold tracking-widest">Paused</span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center space-x-3">
                                            <button
                                                onClick={() => handleToggleEnabled(provider)}
                                                className={clsx(
                                                    "p-3 rounded-2xl transition-all border",
                                                    provider.enabled
                                                        ? "bg-green-500/10 border-green-500/20 text-green-500"
                                                        : "bg-gray-800 border-gray-700 text-gray-500"
                                                )}
                                            >
                                                {provider.enabled ? <ToggleRight size={24} /> : <ToggleLeft size={24} />}
                                            </button>
                                            <button
                                                onClick={() => {
                                                    setEditingId(provider.id);
                                                    setIsAdding(false);
                                                    setFormData(provider);
                                                }}
                                                className="p-3 bg-gray-800 border border-gray-700 text-gray-400 hover:text-white hover:border-brand-500/50 rounded-2xl transition-all"
                                            >
                                                <Edit2 size={20} />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(provider.id)}
                                                className="p-3 bg-gray-800 border border-gray-700 text-gray-400 hover:text-red-500 hover:border-red-500/50 rounded-2xl transition-all"
                                            >
                                                <Trash2 size={20} />
                                            </button>
                                        </div>
                                    </div>

                                    <div className="mt-8 grid grid-cols-2 lg:grid-cols-4 gap-8 border-t border-gray-800/50 pt-8">
                                        <div className="space-y-1">
                                            <span className="text-[10px] font-black uppercase tracking-widest text-gray-600 block">Gateway Key</span>
                                            <span className="text-sm font-mono text-gray-400 truncate block">
                                                {provider.public_key ? `${provider.public_key.substring(0, 8)}...` : 'None'}
                                            </span>
                                        </div>
                                        <div className="space-y-1">
                                            <span className="text-[10px] font-black uppercase tracking-widest text-gray-600 block">Security Key</span>
                                            <span className="text-sm font-mono text-gray-400 block tracking-widest">
                                                {provider.secret_key ? '••••••••' : 'None'}
                                            </span>
                                        </div>
                                        <div className="space-y-1">
                                            <span className="text-[10px] font-black uppercase tracking-widest text-gray-600 block">Environment</span>
                                            <div className="flex items-center gap-1.5 text-xs font-bold text-brand-400">
                                                <div className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse"></div>
                                                Development
                                            </div>
                                        </div>
                                        <div className="space-y-1">
                                            <span className="text-[10px] font-black uppercase tracking-widest text-gray-600 block">Status</span>
                                            <span className={clsx(
                                                "text-xs font-bold px-2 py-0.5 rounded border block w-fit",
                                                provider.enabled ? "text-green-500 border-green-500/20 bg-green-500/5" : "text-gray-500 border-gray-800 bg-gray-950"
                                            )}>
                                                {provider.enabled ? "Active" : "Inactive"}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                ))}

                {providers.length === 0 && !isAdding && (
                    <div className="text-center py-20 bg-gray-900/50 border-2 border-dashed border-gray-800 rounded-2xl">
                        <div className="mx-auto w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center text-gray-600 mb-4">
                            <Shield size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-gray-400">No payment gateways configured</h3>
                        <p className="text-gray-500 mt-2 max-w-md mx-auto">Configure your payment providers like PayFast or Stripe to start receiving payments for orders.</p>
                        <button
                            onClick={() => {
                                setIsAdding(true);
                                setFormData({ provider_name: '', display_name: '', enabled: true, is_active: true });
                            }}
                            className="mt-6 text-brand-500 hover:text-brand-400 font-bold flex items-center space-x-2 mx-auto transition-colors"
                        >
                            <Plus size={20} />
                            <span>Configure your first gateway</span>
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default PaymentSettings;
