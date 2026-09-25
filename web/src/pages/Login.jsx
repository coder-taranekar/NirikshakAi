import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Envelope, Lock, CircleNotch } from '@phosphor-icons/react';
import useAuthStore from '../store/authStore';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(email, password);
      navigate(user.role === 'admin' ? '/' : '/scan');
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 -left-32 w-96 h-96 bg-accent/8 rounded-full blur-[120px] animate-pulse-glow" />
        <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-accent/5 rounded-full blur-[120px] animate-pulse-glow" style={{ animationDelay: '1s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-accent/3 rounded-full blur-[200px]" />
      </div>

      {/* Login card */}
      <div className="relative w-full max-w-md animate-scale-in">
        <div className="glass-card p-8 space-y-8">
          {/* Logo + Title */}
          <div className="text-center space-y-3">
            <div className="w-16 h-16 rounded-2xl bg-accent/15 border border-accent/20 flex items-center justify-center mx-auto mb-4 animate-pulse-glow">
              <ShieldCheck size={36} weight="duotone" className="text-accent-light" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">NirikshakAI</h1>
            <p className="text-sm text-white/30 leading-relaxed">
              Legal Metrology Compliance System<br />
              <span className="text-[11px] text-white/20">Packaged Commodities Rules, 2011</span>
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs text-white/40 font-medium ml-1" htmlFor="login-email">Email</label>
              <div className="relative">
                <Envelope size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/20" />
                <input id="login-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="inspector@lm.gov.in" className="glass-input w-full pl-10" required autoFocus />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-white/40 font-medium ml-1" htmlFor="login-password">Password</label>
              <div className="relative">
                <Lock size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-white/20" />
                <input id="login-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter password" className="glass-input w-full pl-10" required />
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-danger/10 border border-danger/20 text-danger-light text-sm animate-slide-up">{error}</div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 py-3.5">
              {loading ? <CircleNotch size={20} className="animate-spin" /> : null}
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          {/* Footer */}
          <p className="text-center text-[10px] text-white/15 leading-relaxed">
            Department of Consumer Affairs<br />
            Government of India
          </p>
        </div>
      </div>
    </div>
  );
}
