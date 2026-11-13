import { useState, useEffect } from 'react';
import {
    Search,
    Filter,
    UserPlus,
    Shield,
    Mail,
    CheckCircle2,
    XCircle,
    MoreVertical,
    LogOut,
    RefreshCcw
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { adminService } from '../../services/adminService';
import type { AdminUser } from '../../services/adminService';
import { toast } from 'react-hot-toast';
import { clsx } from 'clsx';
import AddDriverModal from '../../components/admin/AddDriverModal';
import AddRestaurantModal from '../../components/admin/AddRestaurantModal';
import AddAdminModal from '../../components/admin/AddAdminModal';
import { Truck, Store } from 'lucide-react';

const Users = () => {
    const [users, setUsers] = useState<AdminUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [isActionsOpen, setIsActionsOpen] = useState<string | null>(null);
    const [isAddMenuOpen, setIsAddMenuOpen] = useState(false);

    // Modals state
    const [activeModal, setActiveModal] = useState<'driver' | 'restaurant' | 'admin' | null>(null);

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        try {
            setLoading(true);
            const data = await adminService.getUsers();
            setUsers(data);
        } catch (err) {
            toast.error('Failed to fetch users');
        } finally {
            setLoading(false);
        }
    };

    const toggleUserStatus = async (user: AdminUser) => {
        try {
            await adminService.updateUser(user.id, { is_active: !user.is_active });
            toast.success(`User ${user.is_active ? 'deactivated' : 'activated'} successfully`);
            fetchUsers();
        } catch (err) {
            toast.error('Failed to update user status');
        }
    };

    const handleForceLogout = async (userId: string) => {
        try {
            await adminService.forceLogoutUser(userId);
            toast.success('User logged out from all devices');
            setIsActionsOpen(null);
        } catch (err) {
            toast.error('Failed to force logout');
        }
    };

    const filteredUsers = users.filter(u =>
        u.email.toLowerCase().includes(search.toLowerCase()) ||
        u.name.toLowerCase().includes(search.toLowerCase()) ||
        u.sur_name.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-white tracking-tight">User Management</h1>
                    <p className="text-gray-400 mt-1">Manage platform users, roles, and sessions.</p>
                </div>

                <div className="relative">
                    <button
                        onClick={() => setIsAddMenuOpen(!isAddMenuOpen)}
                        className="flex items-center space-x-2 px-4 py-2.5 bg-brand-500 hover:bg-brand-600 text-black font-bold rounded-xl transition-all shadow-lg shadow-brand-500/10"
                    >
                        <UserPlus size={18} />
                        <span className="text-white ">Add New Account</span>
                    </button>

                    {isAddMenuOpen && (
                        <>
                            <div className="fixed inset-0 z-40" onClick={() => setIsAddMenuOpen(false)}></div>
                            <div className="absolute right-0 mt-2 w-56 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl py-2 z-50 animate-in fade-in zoom-in duration-200">
                                <button
                                    onClick={() => { setActiveModal('driver'); setIsAddMenuOpen(false); }}
                                    className="w-full flex items-center space-x-3 px-4 py-3 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
                                >
                                    <Truck size={18} className="text-brand-500" />
                                    <div className="text-left">
                                        <p className="font-bold">New Driver</p>
                                        <p className="text-[10px] text-gray-500">Create driver & profile</p>
                                    </div>
                                </button>
                                <button
                                    onClick={() => { setActiveModal('restaurant'); setIsAddMenuOpen(false); }}
                                    className="w-full flex items-center space-x-3 px-4 py-3 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
                                >
                                    <Store size={18} className="text-brand-400" />
                                    <div className="text-left">
                                        <p className="font-bold">New Restaurant</p>
                                        <p className="text-[10px] text-gray-500">Create restaurant & admin</p>
                                    </div>
                                </button>
                                <button
                                    onClick={() => { setActiveModal('admin'); setIsAddMenuOpen(false); }}
                                    className="w-full flex items-center space-x-3 px-4 py-3 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
                                >
                                    <Shield size={18} className="text-purple-400" />
                                    <div className="text-left">
                                        <p className="font-bold">Administrator</p>
                                        <p className="text-[10px] text-gray-500">Platform management</p>
                                    </div>
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* Filters & Search */}
            <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1 relative group">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-brand-500 transition-colors" size={20} />
                    <input
                        type="text"
                        placeholder="Search users by name, email..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full bg-gray-900/50 border border-gray-800 rounded-xl pl-10 pr-4 py-2.5 focus:ring-1 focus:ring-brand-500 focus:border-brand-500 outline-none transition-all placeholder-gray-600"
                    />
                </div>
                <button className="flex items-center space-x-2 px-4 py-2.5 bg-gray-900/50 border border-gray-800 text-gray-400 hover:text-white hover:border-gray-700 rounded-xl transition-all">
                    <Filter size={20} />
                    <span className="font-medium text-sm">Filters</span>
                </button>
                <button
                    onClick={fetchUsers}
                    className="p-2.5 bg-gray-900/50 border border-gray-800 text-gray-400 hover:text-white hover:border-gray-700 rounded-xl transition-all"
                >
                    <RefreshCcw size={20} className={loading ? "animate-spin" : ""} />
                </button>
            </div>

            {/* Users Table */}
            <div className="bg-gray-900/40 backdrop-blur-xl border border-gray-800 rounded-2xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="bg-gray-800/30 border-b border-gray-800">
                                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-widest">User</th>
                                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-widest">Role</th>
                                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-widest">Status</th>
                                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-widest text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800">
                            <AnimatePresence mode="popLayout">
                                {loading ? (
                                    [1, 2, 3].map(i => (
                                        <tr key={i} className="animate-pulse">
                                            <td className="px-6 py-4"><div className="h-10 bg-gray-800 rounded-lg w-48"></div></td>
                                            <td className="px-6 py-4"><div className="h-6 bg-gray-800 rounded-full w-24"></div></td>
                                            <td className="px-6 py-4"><div className="h-6 bg-gray-800 rounded-full w-20"></div></td>
                                            <td className="px-6 py-4"><div className="h-8 bg-gray-800 rounded-lg w-8 ml-auto"></div></td>
                                        </tr>
                                    ))
                                ) : filteredUsers.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} className="px-6 py-12 text-center text-gray-500 font-medium">
                                            No users found matching your search.
                                        </td>
                                    </tr>
                                ) : (
                                    filteredUsers.map((user) => (
                                        <motion.tr
                                            layout
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            exit={{ opacity: 0 }}
                                            key={user.id}
                                            className="hover:bg-gray-800/30 transition-colors group"
                                        >
                                            <td className="px-6 py-4">
                                                <div className="flex items-center space-x-3">
                                                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-gray-800 to-gray-700 flex items-center justify-center text-brand-500 font-bold">
                                                        {user.name.charAt(0)}
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-bold text-white">{user.name} {user.sur_name}</p>
                                                        <p className="text-xs text-gray-500">{user.email}</p>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={clsx(
                                                    "inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider",
                                                    user.role === 'super_admin' ? "bg-brand-500/10 text-brand-500" :
                                                        user.role === 'restaurant_admin' ? "bg-brand-500/10 text-brand-400" :
                                                            "bg-gray-700 text-gray-300"
                                                )}>
                                                    {user.role}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <button
                                                    onClick={() => toggleUserStatus(user)}
                                                    className={clsx(
                                                        "flex items-center space-x-1.5 transition-colors",
                                                        user.is_active ? "text-green-500 hover:text-green-400" : "text-gray-500 hover:text-gray-400"
                                                    )}
                                                >
                                                    {user.is_active ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                                                    <span className="text-xs font-bold">{user.is_active ? 'Active' : 'Inactive'}</span>
                                                </button>
                                            </td>
                                            <td className="px-6 py-4 text-right relative">
                                                <button
                                                    onClick={() => setIsActionsOpen(isActionsOpen === user.id ? null : user.id)}
                                                    className="p-2 text-gray-500 hover:text-white rounded-lg hover:bg-gray-800 transition-all"
                                                >
                                                    <MoreVertical size={20} />
                                                </button>

                                                {isActionsOpen === user.id && (
                                                    <>
                                                        <div className="fixed inset-0 z-40" onClick={() => setIsActionsOpen(null)}></div>
                                                        <div className="absolute right-6 top-12 w-48 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl py-2 z-50 animate-in fade-in zoom-in duration-200">
                                                            <button className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-brand-500 transition-colors">
                                                                <Shield size={16} />
                                                                <span>Edit Permissions</span>
                                                            </button>
                                                            <button className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors">
                                                                <Mail size={16} />
                                                                <span>Contact User</span>
                                                            </button>
                                                            <div className="h-px bg-gray-700 my-1"></div>
                                                            <button
                                                                onClick={() => handleForceLogout(user.id)}
                                                                className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                                                            >
                                                                <LogOut size={16} />
                                                                <span>Logout everywhere</span>
                                                            </button>
                                                        </div>
                                                    </>
                                                )}
                                            </td>
                                        </motion.tr>
                                    ))
                                )}
                            </AnimatePresence>
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Modals */}
            <AddDriverModal
                isOpen={activeModal === 'driver'}
                onClose={() => setActiveModal(null)}
                onSuccess={fetchUsers}
            />
            <AddRestaurantModal
                isOpen={activeModal === 'restaurant'}
                onClose={() => setActiveModal(null)}
                onSuccess={fetchUsers}
            />
            <AddAdminModal
                isOpen={activeModal === 'admin'}
                onClose={() => setActiveModal(null)}
                onSuccess={fetchUsers}
            />
        </div>
    );
};

export default Users;
