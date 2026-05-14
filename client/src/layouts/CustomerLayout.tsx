import { useState } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import {
  ShoppingBag,
  User,
  LogOut,
  Menu as MenuIcon,
  X,
  UtensilsCrossed,
  Clock,
  Search,
  ChevronDown
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { clsx } from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

const CustomerLayout = () => {
  const { user, logoutUser } = useAuth();
  const { totalItems } = useCart();
  const navigate = useNavigate();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  const navItems = [
    { label: 'Restaurants', path: '/customer', icon: UtensilsCrossed },
    { label: 'My Orders', path: '/customer/orders', icon: Clock },
  ];

  const handleLogout = async () => {
    await logoutUser();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white font-sans selection:bg-blue-500/30">
      {/* Top Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-gray-950/80 backdrop-blur-xl border-b border-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            {/* Logo */}
            <Link to="/customer" className="flex items-center space-x-3 group">
              <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-600/20 group-hover:rotate-12 transition-transform duration-300">
                <UtensilsCrossed className="text-white w-6 h-6" />
              </div>
              <span className="text-2xl font-black tracking-tighter uppercase italic">L'vovo</span>
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center space-x-1">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={clsx(
                    "px-4 py-2 rounded-xl text-sm font-bold uppercase tracking-widest transition-all flex items-center space-x-2",
                    location.pathname === item.path
                      ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
                      : "text-gray-400 hover:text-white hover:bg-gray-900"
                  )}
                >
                  <item.icon size={16} />
                  <span>{item.label}</span>
                </Link>
              ))}
            </div>

            {/* Action Bar */}
            <div className="flex items-center space-x-4">
              {/* Search Trigger */}
              <button className="p-2.5 text-gray-400 hover:text-white hover:bg-gray-900 rounded-xl transition-all">
                <Search size={22} />
              </button>

              {/* Cart Icon */}
              <Link
                to="/customer/cart"
                className="relative p-2.5 text-gray-400 hover:text-white hover:bg-gray-900 rounded-xl transition-all group"
              >
                <ShoppingBag size={22} />
                {totalItems > 0 && (
                  <span className="absolute top-1 right-1 w-5 h-5 bg-blue-600 text-white text-[10px] font-black rounded-full flex items-center justify-center border-2 border-gray-950 group-hover:scale-110 transition-transform">
                    {totalItems}
                  </span>
                )}
              </Link>

              {/* Profile Dropdown */}
              <div className="relative">
                <button
                  onClick={() => setIsProfileOpen(!isProfileOpen)}
                  className="flex items-center space-x-2 p-1.5 bg-gray-900 hover:bg-gray-800 rounded-xl transition-all border border-gray-800"
                >
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-black text-xs">
                    {user?.name?.[0].toUpperCase()}
                  </div>
                  <ChevronDown size={14} className={clsx("text-gray-500 transition-transform", isProfileOpen && "rotate-180")} />
                </button>

                <AnimatePresence>
                  {isProfileOpen && (
                    <>
                      <div
                        className="fixed inset-0 z-40"
                        onClick={() => setIsProfileOpen(false)}
                      ></div>
                      <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        className="absolute right-0 mt-3 w-56 bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl z-50 overflow-hidden"
                      >
                        <div className="p-4 border-b border-gray-800">
                          <p className="text-xs font-black text-gray-500 uppercase tracking-widest mb-1">Signed in as</p>
                          <p className="font-bold text-white truncate">{user?.name} {user?.sur_name}</p>
                        </div>
                        <div className="p-2">
                          <Link
                            to="/customer/profile"
                            onClick={() => setIsProfileOpen(false)}
                            className="w-full flex items-center space-x-3 px-3 py-2.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded-xl transition-all text-sm font-bold"
                          >
                            <User size={18} />
                            <span>Profile Settings</span>
                          </Link>
                          <button
                            onClick={handleLogout}
                            className="w-full flex items-center space-x-3 px-3 py-2.5 text-red-500 hover:bg-red-500/10 rounded-xl transition-all text-sm font-bold"
                          >
                            <LogOut size={18} />
                            <span>Sign Out</span>
                          </button>
                        </div>
                      </motion.div>
                    </>
                  )}
                </AnimatePresence>
              </div>

              {/* Mobile Menu Toggle */}
              <button
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                className="md:hidden p-2 text-gray-400 hover:text-white"
              >
                {isMenuOpen ? <X size={24} /> : <MenuIcon size={24} />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {isMenuOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="md:hidden bg-gray-900 border-b border-gray-800 overflow-hidden"
            >
              <div className="px-4 py-6 space-y-4">
                {navItems.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setIsMenuOpen(false)}
                    className="flex items-center space-x-4 p-4 rounded-2xl bg-gray-950 text-white font-bold"
                  >
                    <item.icon size={20} className="text-blue-500" />
                    <span>{item.label}</span>
                  </Link>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      {/* Main Content Area */}
      <main className="pt-28 pb-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default CustomerLayout;