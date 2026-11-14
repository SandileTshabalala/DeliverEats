import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Eye, EyeOff, Loader2, Lock, Mail } from 'lucide-react';
import AuthShell, { authButton, authInput, authLabel } from './AuthShell';
import { APP_NAME } from '../config/brand';
import { useAuth } from '../context/AuthContext';
import { useNavigation } from '../hooks/useNavigation';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const { loginUser: login, loading } = useAuth();
  const { loginRedirect } = useNavigation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const userData = await login(email, password);
      loginRedirect(userData.user.role);
    } catch (err) {
      // the error message is shown by AuthContext
      console.error('Login error:', err);
    }
  };

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to order, or to run your kitchen and deliveries."
      footer={<>New to {APP_NAME}? <Link to="/register" className="font-bold text-brand-500 hover:text-brand-400">Create an account</Link></>}
    >
      <form className="space-y-5" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email" className={authLabel}>Email address</label>
          <div className="relative">
            <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
            <input id="email" name="email" type="email" autoComplete="email" required autoFocus
              value={email} onChange={(e) => setEmail(e.target.value)} className={authInput} placeholder="you@example.com" />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="password" className="text-sm font-bold text-gray-300">Password</label>
            <Link to="/forgot-password" className="text-sm font-bold text-brand-500 hover:text-brand-400">Forgot password?</Link>
          </div>
          <div className="relative">
            <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
            <input id="password" name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" required
              value={password} onChange={(e) => setPassword(e.target.value)} className={`${authInput} pr-12`} placeholder="Your password" />
            <button type="button" onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-gray-500 hover:text-white">
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </div>

        <button type="submit" disabled={loading} className={authButton}>
          {loading ? <><Loader2 size={18} className="animate-spin" /> Signing in...</> : <>Sign in <ArrowRight size={18} /></>}
        </button>

        <p className="text-xs text-gray-500 text-center leading-relaxed">
          Restaurant staff and drivers: use the email and password your restaurant set up for you.
        </p>
      </form>
    </AuthShell>
  );
};

export default Login;
