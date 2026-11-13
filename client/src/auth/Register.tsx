import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import {
  User,
  Mail,
  Phone,
  Lock,
  ArrowRight,
  Loader2,
  CheckCircle2,
  Utensils
} from 'lucide-react';
import { Roles } from '../utils/roles';

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
    <div className="min-h-screen bg-gray-950 flex font-sans overflow-hidden">
      {/* Left Side: Illustration & Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-brand-600 relative overflow-hidden items-center justify-center p-12">
        <div className="absolute inset-0 opacity-20 pointer-events-none">
          <div className="absolute top-[-10%] left-[-10%] w-full h-full bg-[radial-gradient(circle,white_1px,transparent_1px)] bg-size-[:40px_40px]"></div>
        </div>

        <div className="relative z-10 text-white space-y-8 max-w-lg">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 bg-white/10 backdrop-blur-xl rounded-2xl flex items-center justify-center border border-white/20 shadow-2xl">
              <Utensils className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl font-black tracking-tighter uppercase italic">L'vovo</h1>
          </div>

          <div className="space-y-4">
            <h2 className="text-5xl font-black leading-tight tracking-tighter uppercase">
              Join our community <br />
              <span className="text-brand-200">of food lovers.</span>
            </h2>
            <p className="text-brand-100/80 text-lg leading-relaxed font-medium">
              Discover the best street food in Matafini. Quick delivery, fresh ingredients, and unforgettable taste.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-6 pt-8">
            {[
              { label: "10k+", sub: "Happy Customers" },
              { label: "50+", sub: "Local Vendors" }
            ].map((stat, i) => (
              <div key={i} className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/10 shadow-xl">
                <p className="text-3xl font-black leading-none mb-1">{stat.label}</p>
                <p className="text-brand-100/60 text-xs font-bold uppercase tracking-widest">{stat.sub}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Decorative blob */}
        <div className="absolute bottom-[-20%] right-[-10%] w-125 h-125 bg-brand-400 rounded-full blur-[120px] opacity-30 animate-pulse"></div>
      </div>

      {/* Right Side: Registration Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 md:p-12 relative">
        {/* Backdrop glow for mobile */}
        <div className="lg:hidden absolute top-0 left-1/2 -translate-x-1/2 w-64 h-64 bg-brand-600 rounded-full blur-[100px] opacity-20 pointer-events-none"></div>

        <div className="w-full max-w-md space-y-8 animate-in slide-in-from-bottom-8 duration-500">
          <div>
            <Link to="/" className="lg:hidden flex items-center space-x-2 mb-8">
              <Utensils className="w-8 h-8 text-brand-500" />
              <span className="text-2xl font-black tracking-tighter uppercase text-white">L'vovo</span>
            </Link>
            <h3 className="text-3xl font-black text-white tracking-tighter uppercase mb-2">Create Account</h3>
            <p className="text-gray-500 font-medium">Join us today and explore Matafini's finest flavors.</p>
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
          </form>

          <div className="pt-8 text-center">
            <p className="text-gray-500 font-bold">
              Already have an account?{' '}
              <Link to="/login" className="text-brand-500 hover:text-brand-400 transition-colors uppercase tracking-widest text-sm">
                Sign In
              </Link>
            </p>
          </div>

          <div className="pt-8 border-t border-gray-900 flex justify-center space-x-6">
            <div className="flex items-center space-x-2 text-gray-600">
              <CheckCircle2 size={16} />
              <span className="text-[10px] font-black uppercase tracking-wider leading-none">Security Verified</span>
            </div>
            <div className="flex items-center space-x-2 text-gray-600">
              <CheckCircle2 size={16} />
              <span className="text-[10px] font-black uppercase tracking-wider leading-none">256-bit SSL</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;