import React, { useState } from 'react';
import ThemeToggle from '../components/ThemeToggle';
import { APP_NAME } from '../config/brand';
import Logo from '../components/Logo';
import images from '../constant/images';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import {
  User,
  Mail,
  Phone,
  Lock,
  ArrowRight,
  Loader2
} from 'lucide-react';
import { Roles } from '../utils/roles';
import { usePublicStats } from '../hooks/usePublicStats';

const Register = () => {
  const [formData, setFormData] = useState({
    name: '',
    sur_name: '',
    email: '',
    contact_number: '',
    password: '',
    confirmPassword: '',
    role: Roles.CUSTOMER
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  // Real counters from the server; nothing is shown until there is something true to show
  const publicStats = usePublicStats();
  const liveNumbers = publicStats && publicStats.restaurants > 0
    ? [
      { label: String(publicStats.restaurants), sub: publicStats.restaurants === 1 ? "Local kitchen" : "Local kitchens" },
      { label: String(publicStats.orders_delivered), sub: "Orders delivered" },
    ]
    : [];
  const { registerUser } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (formData.password !== formData.confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    try {
      setIsSubmitting(true);
      // Send only required fields to backend
      const { confirmPassword, ...registerData } = formData;
      await registerUser(registerData);
      toast.success("Account created successfully! Please sign in.");
      navigate('/login');
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : "Registration failed. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-gray-950 flex font-sans overflow-hidden">
      <div className="absolute top-4 right-4 z-20"><ThemeToggle /></div>
      {/* Left Side: Illustration & Branding */}
      <div className="keep-dark hidden lg:flex lg:w-1/2 relative overflow-hidden items-center justify-center p-12">
        <img src={images.plates} alt="" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/60 to-black/45"></div>

        <div className="relative z-10 text-white space-y-8 max-w-lg">
          <Link to="/" className="inline-block"><Logo tone="dark" className="h-16" /><span className="sr-only">{APP_NAME}</span></Link>

          <div className="space-y-4">
            <h2 className="text-5xl font-black leading-tight tracking-tighter uppercase">
              Join our community <br />
              <span className="text-brand-500">of food lovers.</span>
            </h2>
            <p className="text-gray-200 text-lg leading-relaxed font-medium">
              Order from the restaurants, shisanyamas and kota spots in your area, and follow your food all the way to your door.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-6 pt-8">
            {liveNumbers.map((stat, i) => (
              <div key={i} className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/10 shadow-xl">
                <p className="text-3xl font-black leading-none mb-1">{stat.label}</p>
                <p className="text-gray-300 text-xs font-bold uppercase tracking-widest">{stat.sub}</p>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Right Side: Registration Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 md:p-12 relative">
        {/* Backdrop glow for mobile */}
        <div className="lg:hidden absolute top-0 left-1/2 -translate-x-1/2 w-64 h-64 bg-brand-600 rounded-full blur-[100px] opacity-20 pointer-events-none"></div>

        <div className="w-full max-w-md space-y-8 animate-in slide-in-from-bottom-8 duration-500">
          <div>
            <Link to="/" className="lg:hidden inline-block mb-8"><Logo className="h-12" /></Link>
            <h3 className="text-3xl font-black text-white tracking-tighter uppercase mb-2">Create Account</h3>
            <p className="text-gray-500 font-medium">Create your free account and start ordering from local kitchens.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center space-x-2">
                  <User size={14} className="text-brand-500" />
                  <span>First Name</span>
                </label>
                <input
                  type="text"
                  name="name"
                  required
                  value={formData.name}
                  onChange={handleChange}
                  className="w-full bg-gray-900/50 border border-gray-800 rounded-2xl px-4 py-3 text-white outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition-all placeholder-gray-600 font-medium"
                  placeholder="John"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center space-x-2">
                  <User size={14} className="text-brand-500" />
                  <span>Last Name</span>
                </label>
                <input
                  type="text"
                  name="sur_name"
                  required
                  value={formData.sur_name}
                  onChange={handleChange}
                  className="w-full bg-gray-900/50 border border-gray-800 rounded-2xl px-4 py-3 text-white outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition-all placeholder-gray-600 font-medium"
                  placeholder="Doe"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center space-x-2">
                <Mail size={14} className="text-brand-500" />
                <span>Email Address</span>
              </label>
              <input
                type="email"
                name="email"
                required
                value={formData.email}
                onChange={handleChange}
                className="w-full bg-gray-900/50 border border-gray-800 rounded-2xl px-4 py-3 text-white outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition-all placeholder-gray-600 font-medium"
                placeholder="john@example.com"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center space-x-2">
                <Phone size={14} className="text-brand-500" />
                <span>Contact Number</span>
              </label>
              <input
                type="tel"
                name="contact_number"
                required
                value={formData.contact_number}
                onChange={handleChange}
                className="w-full bg-gray-900/50 border border-gray-800 rounded-2xl px-4 py-3 text-white outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition-all placeholder-gray-600 font-medium"
                placeholder="+27 12 345 6789"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center space-x-2">
                  <Lock size={14} className="text-brand-500" />
                  <span>Password</span>
                </label>
                <input
                  type="password"
                  name="password"
                  required
                  value={formData.password}
                  onChange={handleChange}
                  className="w-full bg-gray-900/50 border border-gray-800 rounded-2xl px-4 py-3 text-white outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition-all placeholder-gray-600 font-medium"
                  placeholder="••••••••"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center space-x-2">
                  <Lock size={14} className="text-brand-500" />
                  <span>Confirm</span>
                </label>
                <input
                  type="password"
                  name="confirmPassword"
                  required
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  className="w-full bg-gray-900/50 border border-gray-800 rounded-2xl px-4 py-3 text-white outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500 transition-all placeholder-gray-600 font-medium"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div className="pt-4">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-brand-600 hover:bg-brand-500 text-white py-4 rounded-2xl font-black uppercase tracking-widest shadow-xl shadow-brand-600/20 active:scale-[0.98] transition-all disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center space-x-3 group"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Designing Profile...</span>
                  </>
                ) : (
                  <>
                    <span>Create Account</span>
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </>
                )}
              </button>
            </div>
            <p className="text-xs text-gray-500 text-center">
              By creating an account you agree to the <Link to="/terms" className="text-brand-500 hover:text-brand-400 font-bold">Terms of Use</Link> and
              the <Link to="/privacy" className="text-brand-500 hover:text-brand-400 font-bold">Privacy Policy</Link>.
            </p>
          </form>

          <div className="pt-8 text-center">
            <p className="text-gray-500 font-bold">
              Already have an account?{' '}
              <Link to="/login" className="text-brand-500 hover:text-brand-400 transition-colors uppercase tracking-widest text-sm">
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;