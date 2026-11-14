import React from 'react';
import { APP_NAME } from '../../config/brand';
import Logo from '../Logo';
import { FileText as ReportsIcon, Tags } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import {
    LayoutDashboard,
    Users,
    Store,
    Settings,
    CreditCard,
    X
} from 'lucide-react';
import { clsx } from 'clsx';
import { useAuth } from '../../context/AuthContext';

interface SidebarProps {
    isOpen: boolean;
    onClose: () => void;
}

const navItems = [
    { name: 'Dashboard', icon: LayoutDashboard, path: '/admin/dashboard' },
    { name: 'Users', icon: Users, path: '/admin/users' },
    { name: 'Restaurants', icon: Store, path: '/admin/restaurants' },
    { name: 'Categories', icon: Tags, path: '/admin/categories' },
    { name: 'Subscriptions', icon: CreditCard, path: '/admin/billing' },
    { name: 'Reports', icon: ReportsIcon, path: '/admin/reports' },
    { name: 'Settings', icon: Settings, path: '/admin/settings' },
];

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
    const { user } = useAuth();
    const initials = user ? `${user.name?.[0] ?? ''}${user.sur_name?.[0] ?? ''}`.toUpperCase() || 'A' : 'A';
    return (
        <>
            {/* Mobile Backdrop */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-40 lg:hidden backdrop-blur-sm"
                    onClick={onClose}
                />
            )}

            {/* Sidebar Container */}
            <aside className={clsx(
                "fixed top-0 left-0 bottom-0 w-64 bg-gray-900 border-r border-gray-800 z-50 transition-transform duration-300 transform lg:translate-x-0 lg:static lg:inset-0",
                isOpen ? "translate-x-0" : "-translate-x-full"
            )}>
                <div className="flex flex-col h-full">
                    {/* Logo / Header */}
                    <div className="h-16 flex items-center justify-between px-6 border-b border-gray-800">
                        <h1 className="flex items-center gap-2"><Logo className="h-9" /><span className="sr-only">{APP_NAME}</span><span className="text-xs font-bold uppercase tracking-widest text-gray-500 mt-1">Admin</span></h1>
                        <button className="lg:hidden text-gray-400 hover:text-white" onClick={onClose}>
                            <X size={20} />
                        </button>
                    </div>

                    {/* Nav Items */}
                    <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-2">
                        {navItems.map((item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                onClick={() => onClose()}
                                className={({ isActive }) => clsx(
                                    "flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-all duration-200 group",
                                    isActive
                                        ? "bg-brand-500/10 text-brand-500 shadow-[inset_0_0_10px_rgba(242,100,24,0.1)]"
                                        : "text-gray-400 hover:text-white hover:bg-gray-800"
                                )}
                            >
                                <item.icon size={20} className={clsx(
                                    "transition-colors",
                                    "group-hover:text-brand-400"
                                )} />
                                <span className="font-medium">{item.name}</span>
                            </NavLink>
                        ))}
                    </nav>

                    {/* Footer User Info (Optional) */}
                    <div className="p-4 border-t border-gray-800">
                        <div className="flex items-center space-x-3 p-2 rounded-lg bg-gray-800/50">
                            <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-xs font-bold text-black">
                                {initials}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-white truncate">{user ? `${user.name} ${user.sur_name}` : 'Platform owner'}</p>
                                <p className="text-xs text-gray-400 truncate">{user?.email}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </aside>
        </>
    );
};

export default Sidebar;
