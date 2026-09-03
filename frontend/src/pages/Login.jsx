import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import { useWorkspace } from '../context/WorkspaceContext';
import { Eye, EyeOff, Lock, Mail, AlertTriangle, ShieldCheck } from 'lucide-react';

const Login = () => {
  const { login, isAuthenticated } = useAuth();
  const { setWorkspaceMode } = useWorkspace();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!email || !password) {
      setError('Please fill in all fields');
      return;
    }
    
    setLoading(true);
    try {
      const loggedUser = await login(email, password);
      if (loggedUser?.role === 'ca') {
        setWorkspaceMode('ca');
      } else {
        setWorkspaceMode('cs');
      }
      navigate('/dashboard');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-[#F8FAFC] flex items-center justify-center p-4 relative overflow-hidden">
      
      {/* Animated floating orbs */}
      <div className="absolute top-[-10%] left-[-8%] w-[500px] h-[500px] rounded-full bg-[#2563EB] opacity-[0.04] blur-[130px] pointer-events-none animate-float-orb" />
      <div className="absolute bottom-[-10%] right-[-5%] w-[400px] h-[400px] rounded-full bg-[#1D4ED8] opacity-[0.04] blur-[120px] pointer-events-none animate-float-orb-slow" />
      <div className="absolute top-[40%] right-[15%] w-[250px] h-[250px] rounded-full bg-[#3B82F6] opacity-[0.03] blur-[90px] pointer-events-none animate-float-orb" style={{ animationDelay: '4s' }} />

      {/* Main Content: split layout */}
      <div className="w-full max-w-4xl flex items-center justify-between gap-12 relative z-10">
        
        {/* Left side — branding + feature list */}
        <div className="hidden lg:flex flex-col justify-center space-y-6 flex-1 page-transition">
          {/* Logo */}
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-[#2563EB] rounded-xl flex items-center justify-center shadow-lg shadow-[#2563EB]/25">
                <ShieldCheck className="w-5 h-5 text-white" />
              </div>
              <span className="text-[#2563EB] font-mono font-extrabold text-base tracking-widest">
                COMPLIANCE HUB
              </span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#0F172A] leading-tight">
              Regulatory Compliance<br />
              <span className="brand-gradient-text">Unified Workspaces.</span>
            </h1>
            <p className="text-sm text-[#64748B] leading-relaxed max-w-sm">
              Integrated platforms for Company Secretaries (CS) and Chartered Accountants (CA) to manage corporate and tax portfolios.
            </p>
          </div>

          {/* Feature highlights */}
          <div className="space-y-2.5">
            {[
              { label: 'Dedicated workspaces for ROC (CS) and Tax (CA) compliances' },
              { label: 'Advance Tax, GST Filing and TDS obligation calendars' },
              { label: 'Unified Client Management supporting PAN, GSTIN and CIN' },
              { label: 'Role-based access and automatic dashboard routing' },
            ].map((f, i) => (
              <div key={i} className="flex items-center gap-2.5 text-xs text-[#64748B]">
                <div className="w-1.5 h-1.5 rounded-full bg-[#2563EB] shrink-0" />
                {f.label}
              </div>
            ))}
          </div>

        </div>

        {/* Right side — login card */}
        <div className="w-full max-w-[440px] bg-white border border-[#E5E7EB] rounded-2xl p-8 shadow-xl shadow-[#0F172A]/8 page-transition">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="lg:hidden flex items-center justify-center gap-2 mb-4">
              <div className="w-8 h-8 bg-[#2563EB] rounded-lg flex items-center justify-center">
                <ShieldCheck className="w-4 h-4 text-white" />
              </div>
              <span className="text-[#2563EB] font-mono font-extrabold text-sm tracking-widest">COMPLIANCE HUB</span>
            </div>
            <h2 className="text-[#0F172A] text-xl font-bold">Sign in to your account</h2>
            <p className="text-[#64748B] text-xs mt-1.5 font-medium">
              ROC Corporate & Tax Compliance Hub
            </p>
          </div>

          {/* Error inline banner */}
          {error && (
            <div className="mb-5 bg-[#EF4444]/8 border border-[#EF4444]/20 text-[#EF4444] p-3 rounded-lg flex items-start gap-2.5 text-xs font-medium leading-relaxed">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email field */}
            <div>
              <label className="block text-xs font-semibold text-[#64748B] mb-2 uppercase tracking-wide">
                Email Address
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-[#94A3B8]">
                  <Mail className="w-4 h-4" />
                </span>
                <input
                  id="login-email"
                  type="email"
                  placeholder="you@csdashboard.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full h-10 pl-9 pr-3 bg-[#F8FAFC] border border-[#E5E7EB] rounded-lg text-[#0F172A] placeholder-[#94A3B8] outline-none text-sm transition-all focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/10"
                  required
                />
              </div>
            </div>

            {/* Password field */}
            <div>
              <label className="block text-xs font-semibold text-[#64748B] mb-2 uppercase tracking-wide">
                Password
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-[#94A3B8]">
                  <Lock className="w-4 h-4" />
                </span>
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full h-10 pl-9 pr-10 bg-[#F8FAFC] border border-[#E5E7EB] rounded-lg text-[#0F172A] placeholder-[#94A3B8] outline-none text-sm transition-all focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/10"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-[#94A3B8] hover:text-[#64748B] transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Sign In Button */}
            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="w-full h-10 bg-[#2563EB] hover:bg-[#1D4ED8] active:scale-[0.98] text-white text-sm font-semibold rounded-lg flex items-center justify-center transition-all shadow-lg shadow-[#2563EB]/20 mt-6 disabled:opacity-50 disabled:cursor-not-allowed animate-glow-pulse"
            >
              {loading ? (
                <div className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Authenticating...
                </div>
              ) : "Sign in →"}
            </button>
          </form>

          {/* Footer info */}
          <div className="text-center text-[10px] text-[#94A3B8] mt-6">
            Compliance Command Hub · Phase 2 · July 2026
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
