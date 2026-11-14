import { useState } from 'react';
import ThemeToggle from '../components/ThemeToggle';
import NotificationBell from '../components/NotificationBell';
import { Link as ProfileLink } from 'react-router-dom';
import { Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Sidebar from '../components/admin/Sidebar';
import {
  Menu,
  ChevronDown,
  LogOut,
  User as UserIcon
} from 'lucide-react';

import { toast } from 'react-hot-toast';

const AdminLayout = () => {
  const { user, logoutUser } = useAuth();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  const handleLogout = async () => {
    try {
      setIsProfileOpen(false);
      await logoutUser();
      toast.success('Logged out successfully');
    } catch (error) {
      toast.error('Logout failed');
    }
  };

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        {/* Header */}
        <header className="h-16 bg-gray-900/50 backdrop-blur-md border-b border-gray-800 px-4 sm:px-6 flex items-center justify-between z-30">
          <div className="flex items-center space-x-4">
            <button
              className="lg:hidden p-2 text-gray-400 hover:text-white"
              onClick={() => setIsSidebarOpen(true)}
            >
              <Menu size={20} />
            </button>

          </div>

          <div className="flex items-center space-x-2 sm:space-x-4">

            <ThemeToggle />
            <NotificationBell />
            {/* Profile Dropdown */}
            <div className="relative">
              <button
                className="flex items-center space-x-2 p-1 rounded-full hover:bg-gray-800 transition-colors"
                onClick={() => setIsProfileOpen(!isProfileOpen)}
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-brand-600 to-brand-400 flex items-center justify-center text-black font-bold text-xs ring-2 ring-brand-500/20">
                  {user?.name?.charAt(0).toUpperCase() || 'A'}
                </div>
                <div className="hidden md:block text-left">
                  <p className="text-xs font-semibold leading-tight">{user?.name || 'Admin'}</p>
                  <p className="text-[10px] text-gray-500 leading-tight">Super Admin</p>
                </div>
                <ChevronDown size={14} className="text-gray-500 hidden md:block" />
              </button>

              {isProfileOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setIsProfileOpen(false)}></div>
                  <div className="absolute right-0 mt-2 w-48 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl py-2 z-20 animate-in fade-in zoom-in duration-200">
                    <ProfileLink to="/admin/settings" onClick={() => setIsProfileOpen(false)} className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors">
                      <UserIcon size={16} />
                      <span>My account</span>
                    </ProfileLink>
                    <button
                      className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors mt-1"
                      onClick={handleLogout}
                    >
                      <LogOut size={16} />
                      <span>Logout</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </header>

        {/* Main Scrolling Area */}
        <main className="flex-1 overflow-y-auto bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-gray-900 via-gray-950 to-gray-950">
          <div className="container mx-auto px-4 sm:px-6 py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;