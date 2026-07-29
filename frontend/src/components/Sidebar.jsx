import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Building2, ListChecks, BookOpen, Settings,
  BarChart3, LogOut, ShieldCheck, MessageSquareText,
  FileSpreadsheet, RefreshCw, CalendarDays, UsersRound
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useWorkspace } from '../context/WorkspaceContext';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';

const Sidebar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { isCS, title } = useWorkspace();
  const { data: organization } = useQuery({
    queryKey: ['organization'],
    queryFn: async () => (await api.get('/organizations/current')).data,
    staleTime: 300000,
  });
  const workRole = (user?.designation || user?.role || '').toLowerCase().replaceAll(' ', '_');
  const isExecutive = ['executive', 'intern', 'staff'].includes(workRole);

  const links = isExecutive ? [
    { to: '/dashboard', label: 'Overview', icon: LayoutDashboard },
    { to: '/tasks', label: 'My Tasks', icon: ListChecks },
  ] : isCS ? [
    { to: '/dashboard', label: 'Overview', icon: LayoutDashboard },
    { to: '/clients', label: 'Companies', icon: Building2 },
    { to: '/tasks', label: 'Obligations', icon: ListChecks },
    { to: '/review-queue', label: 'Review Queue', icon: ShieldCheck },
    { to: '/calendar', label: 'Calendar', icon: CalendarDays },
    { to: '/regulatory-updates', label: 'Intelligence', icon: BookOpen },
    { to: '/chat', label: 'Assistant', icon: MessageSquareText },
  ] : [
    { to: '/dashboard', label: 'Overview', icon: LayoutDashboard },
    { to: '/clients', label: 'Clients', icon: Building2 },
    { to: '/tasks', label: 'Obligations', icon: ListChecks },
    { to: '/review-queue', label: 'Review Queue', icon: ShieldCheck },
    { to: '/calendar', label: 'Calendar', icon: CalendarDays },
    { to: '/reconciliation', label: 'Reconciliation', icon: RefreshCw },
    { to: '/financial-statements', label: 'Statements', icon: FileSpreadsheet },
    { to: '/regulatory-updates', label: 'Intelligence', icon: BookOpen },
    { to: '/chat', label: 'Assistant', icon: MessageSquareText },
  ];

  if (user?.role === 'admin') {
    links.push({ to: '/reports', label: 'Reports', icon: BarChart3 });
    links.push({ to: '/admin', label: 'Administration', icon: Settings });
    links.push({ to: '/organization', label: 'Firm settings', icon: UsersRound });
  } else if (user?.role === 'partner') {
    links.push({ to: '/reports', label: 'Reports', icon: BarChart3 });
    links.push({ to: '/organization', label: 'Firm settings', icon: UsersRound });
  }
  if (workRole === 'manager' || workRole === 'partner') links.splice(2, 0, { to: '/workload', label: 'Workload', icon: UsersRound });

  const initials = (user?.full_name || user?.email || 'CS')
    .split(/[\s@]+/).filter(Boolean).map((part) => part[0]).join('').slice(0, 2).toUpperCase();

  const signOut = () => {
    logout();
    navigate('/login');
  };

  const linkClass = ({ isActive }) => `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition-all ${
    isActive
      ? isCS
        ? 'bg-white text-[#101828] shadow-[0_8px_24px_rgba(5,12,25,0.18)]'
        : 'bg-emerald-600 text-white shadow-[0_8px_24px_rgba(5,150,105,0.18)]'
      : 'text-slate-400 hover:bg-white/[0.06] hover:text-white'
  }`;

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[236px] flex-col bg-[#0B1220] px-3 py-4 lg:flex">
        <div className="flex h-12 items-center gap-3 px-2">
          <div className={`flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br ${
            isCS ? 'from-[#6D8EFF] to-[#3157D5]' : 'from-emerald-400 to-emerald-600'
          } shadow-lg shadow-blue-950/30`}>
            <ShieldCheck className="h-[18px] w-[18px] text-white" />
          </div>
          <div>
            <p className="max-w-[154px] truncate text-[13px] font-semibold tracking-wide text-white">{organization?.name || title}</p>
            <p className="text-[10px] text-slate-500">{isCS ? 'CS workspace' : 'CA workspace'} · Private tenant</p>
          </div>
        </div>

        <nav className="flex-grow space-y-1 mt-6" aria-label="Primary navigation">
          <p className="mb-2 px-3 text-[9px] font-semibold uppercase tracking-[0.18em] text-slate-600">Workspace</p>
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} className={linkClass}>
              <link.icon className="h-4 w-4 shrink-0" strokeWidth={1.8} />
              <span>{link.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="rounded-2xl border border-white/[0.07] bg-white/[0.04] p-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#263653] text-[10px] font-semibold text-blue-100">{initials}</div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-white">{user?.full_name || user?.email}</p>
              <p className="mt-0.5 text-[9px] uppercase tracking-wider text-slate-500">{user?.role || 'member'}</p>
            </div>
            <button onClick={signOut} className="rounded-lg p-2 text-slate-500 transition hover:bg-white/[0.06] hover:text-white" aria-label="Sign out">
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </aside>

      <nav className="fixed inset-x-3 bottom-3 z-50 flex items-center justify-around rounded-2xl border border-white/10 bg-[#0B1220]/95 p-1.5 shadow-2xl backdrop-blur lg:hidden" aria-label="Mobile navigation">
        {links.slice(0, 5).map((link) => (
          <NavLink key={link.to} to={link.to} className={({ isActive }) => `flex min-w-[52px] flex-col items-center gap-1 rounded-xl px-2 py-2 text-[9px] ${
            isActive 
              ? isCS 
                ? 'bg-white text-[#101828]'
                : 'bg-emerald-600 text-white'
              : 'text-slate-400'
          }`}>
            <link.icon className="h-4 w-4" />
            <span>{link.label}</span>
          </NavLink>
        ))}
      </nav>
    </>
  );
};

export default Sidebar;
