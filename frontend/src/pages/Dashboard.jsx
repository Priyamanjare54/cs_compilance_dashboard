import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertTriangle, ArrowRight, BookOpen, Building2, CalendarClock,
  CheckCircle2, CircleDot, Plus, Sparkles, UsersRound, FileSpreadsheet, RefreshCw
} from 'lucide-react';
import { getPartnerDashboard, getReportsSummary } from '../services/reports';
import { getTasks } from '../services/tasks';
import { useAuth } from '../context/AuthContext';
import { useWorkspace } from '../context/WorkspaceContext';
import api from '../services/api';
import { DashboardSkeleton } from '../components/Loader';
import StatusBadge from '../components/StatusBadge';
import { formatDate } from '../utils/dateUtils';
import TaskDetail from './TaskDetail';

const Metric = ({ label, value, helper, icon: Icon, tone = 'blue' }) => {
  const tones = {
    blue: 'bg-blue-50 text-blue-600',
    red: 'bg-rose-50 text-rose-600',
    amber: 'bg-amber-50 text-amber-600',
    green: 'bg-emerald-50 text-emerald-600',
  };
  return (
    <div className="premium-card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="eyebrow">{label}</p>
          <p className="mt-3 text-[28px] font-semibold tracking-[-0.04em] text-slate-950">
            {typeof value === 'number' ? value.toLocaleString() : (value || 0)}
          </p>
          <p className="mt-1 text-[10px] text-slate-500">{helper}</p>
        </div>
        <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${tones[tone]}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
};

const ExecutiveTaskGroup = ({ title, helper, tasks, icon: Icon, tone, onOpen }) => {
  const tones = {
    blue: 'bg-blue-50 text-blue-600',
    amber: 'bg-amber-50 text-amber-600',
    red: 'bg-rose-50 text-rose-600',
    green: 'bg-emerald-50 text-emerald-600',
  };
  return (
    <section className="premium-card overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <div>
          <p className="text-sm font-semibold text-slate-950">{title}</p>
          <p className="mt-0.5 text-[10px] text-slate-500">{helper}</p>
        </div>
        <div className={`flex h-9 min-w-9 items-center justify-center gap-2 rounded-xl px-2.5 ${tones[tone]}`}>
          <Icon className="h-4 w-4" />
          <span className="text-xs font-bold">{tasks.length}</span>
        </div>
      </div>
      <div className="divide-y divide-slate-100">
        {tasks.length === 0 ? (
          <p className="px-5 py-8 text-center text-xs text-slate-400">No tasks in this section.</p>
        ) : tasks.map((task) => (
          <button key={task.id} type="button" onClick={() => onOpen(task.id)} className="w-full px-5 py-4 text-left transition hover:bg-slate-50/80">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-slate-900">{task.title}</p>
                <p className="mt-1 truncate text-[10px] text-slate-500">{task.company?.name || 'Client company'}</p>
              </div>
              <StatusBadge status={task.status} />
            </div>
            <p className="mt-2 text-[10px] text-slate-400">Due {formatDate(task.due_date)}</p>
          </button>
        ))}
      </div>
    </section>
  );
};

const Dashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { mode, isCS, isCA } = useWorkspace();
  const [taskId, setTaskId] = useState(null);
  const isPartner = user?.role === 'partner';
  const workRole = (user?.designation || user?.role || '').toLowerCase().replaceAll(' ', '_');
  const isExecutive = ['executive', 'intern', 'staff'].includes(workRole);

  const { data: partnerDashboard, isLoading: partnerDashboardLoading } = useQuery({
    queryKey: ['partner-dashboard', mode],
    queryFn: () => getPartnerDashboard({ category: mode }),
    enabled: isPartner,
    staleTime: 30000,
  });

  const { data: summary, isLoading: summaryLoading } = useQuery({ 
    queryKey: ['reports-summary', mode], 
    queryFn: () => getReportsSummary({ category: mode }),
    enabled: !isPartner && !isExecutive,
  });
  const { data: tasks = [], isLoading: tasksLoading } = useQuery({ 
    queryKey: ['tasks', mode], 
    queryFn: () => getTasks({ category: mode }), 
    staleTime: 30000,
    enabled: !isPartner,
  });
  const { data: logs = [], isLoading: logsLoading } = useQuery({ 
    queryKey: ['system-audit-logs'], 
    queryFn: async () => (await api.get('/reports/audit-logs?limit=6')).data,
    enabled: !isPartner && !isExecutive,
  });

  if (
    (isPartner && partnerDashboardLoading) ||
    (isExecutive && tasksLoading) ||
    (!isPartner && !isExecutive && (summaryLoading || tasksLoading || logsLoading))
  ) return <DashboardSkeleton />;

  if (isPartner) {
    const data = partnerDashboard || {};
    const cards = [
      ['Total Clients', data.clients, 'Active portfolio', Building2, 'blue'],
      ['Pending Compliance', data.pending_filings, 'Open tasks across all clients', FileSpreadsheet, 'amber'],
      ['Completed', data.completed, 'Tasks that are fully closed', CheckCircle2, 'green'],
      ['Delayed', data.delayed, 'Overdue filings needing action', AlertTriangle, 'red'],
      ["Today's Due", data.todays_due, 'Filings due today', CalendarClock, 'amber'],
      ['Team Productivity', `${data.team_productivity ?? 0}%`, 'Closed filings rate', UsersRound, 'green'],
    ];
    const delayedTasks = data.delayed_tasks || [];
    return (
      <div className="page-transition space-y-6">
        <section className="overflow-hidden rounded-[24px] bg-[#0B1220] px-6 py-7 text-white shadow-[0_20px_60px_rgba(11,18,32,0.18)] sm:px-8">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-blue-300">Partner dashboard</p>
          <h1 className="mt-3 text-2xl font-semibold tracking-[-0.035em] sm:text-[32px]">Portfolio health at a glance.</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Focus on client risk, filing delivery and team performance—not individual task lists.</p>
        </section>

        <section className="grid grid-cols-2 gap-3 xl:grid-cols-3">
          {cards.map(([label, value, helper, icon, tone]) => <Metric key={label} label={label} value={value} helper={helper} icon={icon} tone={tone} />)}
        </section>

        <section className="grid gap-5 lg:grid-cols-3">
          <Link to="/clients" className="premium-card group p-6 transition hover:-translate-y-0.5 hover:border-blue-200">
            <p className="eyebrow">Top Delayed Team</p>
            <p className="mt-4 text-xl font-semibold text-slate-950">{data.top_delayed_team}</p>
            <p className="mt-2 text-xs text-slate-500">Prioritize this team’s overdue client work.</p>
            <span className="mt-5 inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600">View clients <ArrowRight className="h-3.5 w-3.5" /></span>
          </Link>
          <div className="premium-card p-6">
            <p className="eyebrow">Top Performer</p>
            <p className="mt-4 text-xl font-semibold text-emerald-700">{data.top_performer}</p>
            <p className="mt-2 text-xs text-slate-500">Most closed filings in the current portfolio.</p>
          </div>
          <Link to="/clients" className="premium-card group p-6 transition hover:-translate-y-0.5 hover:border-rose-200">
            <p className="eyebrow">Most Delayed Client</p>
            <p className="mt-4 text-xl font-semibold text-rose-700">{data.most_delayed_client}</p>
            <p className="mt-2 text-xs text-slate-500">Client with the highest number of overdue filings.</p>
            <span className="mt-5 inline-flex items-center gap-1 text-[11px] font-semibold text-rose-600">Open portfolio <ArrowRight className="h-3.5 w-3.5" /></span>
          </Link>
        </section>

        <section className="premium-card p-6">
          <div className="flex items-center justify-between gap-3 pb-4 border-b border-slate-200">
            <div>
              <p className="eyebrow">Delayed compliance work</p>
              <p className="mt-1 text-sm text-slate-500">Drill into overdue filings and see who is assigned.</p>
            </div>
            <span className="rounded-full bg-rose-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-rose-700">{delayedTasks.length} overdue</span>
          </div>
          <div className="mt-5 space-y-3">
            {delayedTasks.length === 0 ? (
              <p className="text-sm text-slate-500">No overdue filings in your current portfolio.</p>
            ) : delayedTasks.map((task) => (
              <button
                key={task.id}
                type="button"
                onClick={() => setTaskId(task.id)}
                className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left transition hover:border-slate-300 hover:shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-900 truncate">{task.title}</p>
                    <p className="mt-1 text-xs text-slate-500 truncate">{task.company_name}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Delay</p>
                    <p className="mt-1 text-sm font-semibold text-rose-700">{task.delay_days} days</p>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-500">
                  <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-2.5 py-1">Assigned: {task.assigned_name}</span>
                  <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-2.5 py-1">Due {new Date(task.due_date).toLocaleDateString('en-IN')}</span>
                </div>
              </button>
            ))}
          </div>
        </section>
      </div>
    );
  }

  if (isExecutive) {
    const now = new Date();
    const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    const isCompleted = (task) => ['completed_by_executive', 'waiting_for_review', 'approved', 'closed', 'completed'].includes(task.status);
    const groups = [
      ['Today’s Tasks', 'Due before the day ends', tasks.filter((task) => task.due_date === today && !isCompleted(task)), CalendarClock, 'blue'],
      ['Upcoming', 'Your next assigned obligations', tasks.filter((task) => task.due_date > today && !isCompleted(task)), ArrowRight, 'amber'],
      ['Overdue', 'Past deadline and still open', tasks.filter((task) => task.due_date < today && !isCompleted(task)), AlertTriangle, 'red'],
      ['Completed', 'Work fully approved and closed', tasks.filter(isCompleted).reverse(), CheckCircle2, 'green'],
    ];
    return (
      <div className="page-transition space-y-6">
        <section className="overflow-hidden rounded-[24px] bg-[#0B1220] px-6 py-7 text-white shadow-[0_20px_60px_rgba(11,18,32,0.18)] sm:px-8">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-blue-300">Executive dashboard</p>
          <h1 className="mt-3 text-2xl font-semibold tracking-[-0.035em] sm:text-[32px]">My Tasks</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
            A focused view of work assigned directly to you. Other executives’ tasks and company portfolios are not shown.
          </p>
        </section>
        <section className="grid gap-5 lg:grid-cols-2">
          {groups.map(([title, helper, groupTasks, icon, tone]) => (
            <ExecutiveTaskGroup key={title} title={title} helper={helper} tasks={groupTasks} icon={icon} tone={tone} onOpen={setTaskId} />
          ))}
        </section>
        <TaskDetail taskId={taskId} isOpen={Boolean(taskId)} onClose={() => setTaskId(null)} />
      </div>
    );
  }

  const urgentTasks = [...tasks]
    .filter((task) => task.status !== 'completed')
    .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
    .slice(0, 6);
  const total = summary?.total_tasks || 0;
  const completed = summary?.completed_count || 0;
  const overdue = summary?.overdue_count || 0;
  const health = total ? Math.max(0, Math.round(((total - overdue) / total) * 100)) : 100;
  const completion = total ? Math.round((completed / total) * 100) : 0;
  const firstName = (user?.full_name || 'there').split(' ')[0];

  return (
    <div className="page-transition space-y-6">
      <section className="overflow-hidden rounded-[24px] bg-[#0B1220] px-6 py-7 text-white shadow-[0_20px_60px_rgba(11,18,32,0.18)] sm:px-8 sm:py-8">
        <div className="relative z-10 flex flex-col gap-7 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-3 py-1.5 text-[10px] text-slate-300">
              <CircleDot className={`h-3 w-3 ${isCS ? 'text-blue-400' : 'text-emerald-400'}`} /> 
              {isCS ? 'CS corporate law monitoring is active' : 'CA tax & ledger monitoring is active'}
            </div>
            <h1 className="text-2xl font-semibold tracking-[-0.035em] sm:text-[32px]">Good day, {firstName}.</h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">
              {isCS 
                ? 'Your compliance position is clear. Focus on the obligations needing attention, then move to the regulatory library for source-backed research.'
                : 'Your taxation and ledger accounts are up to date. Monitor GSTR/ITR returns, review invoice reconciliation mismatches, or generate audit statement drafts.'
              }
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button 
              onClick={() => navigate('/clients', { state: { openAddDrawer: true } })} 
              className={`premium-button-light flex items-center gap-2 ${isCA ? 'hover:text-emerald-600 hover:border-emerald-600' : ''}`}
            >
              <Plus className="h-4 w-4" /> {isCS ? 'Add company' : 'Add client'}
            </button>
            {isCS ? (
              <button onClick={() => navigate('/regulatory-updates')} className="premium-button-dark">
                <BookOpen className="h-4 w-4" /> Research updates
              </button>
            ) : (
              <button onClick={() => navigate('/reconciliation')} className="premium-button-dark flex items-center gap-2">
                <RefreshCw className="h-4 w-4 text-emerald-400" /> Run Reconciliation
              </button>
            )}
          </div>
        </div>
        <div className={`pointer-events-none absolute right-16 top-0 h-48 w-48 rounded-full ${isCS ? 'bg-blue-500/10' : 'bg-emerald-500/10'} blur-3xl`} />
      </section>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Metric 
          label={isCS ? 'Active companies' : 'Active clients'} 
          value={summary?.total_companies} 
          helper="Managed portfolio" 
          icon={Building2} 
          tone={isCS ? 'blue' : 'green'} 
        />
        <Metric label="Needs attention" value={overdue} helper="Past statutory deadline" icon={AlertTriangle} tone="red" />
        <Metric label="Due in 7 days" value={summary?.due_soon_count} helper="Plan this week" icon={CalendarClock} tone="amber" />
        <Metric label="Completed" value={completed} helper={`${completion}% completion rate`} icon={CheckCircle2} tone="green" />
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.65fr_0.85fr]">
        <div className="premium-card overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6">
            <div>
              <p className="text-sm font-semibold text-slate-950">Priority obligations</p>
              <p className="mt-0.5 text-[10px] text-slate-500">Ordered by nearest deadline</p>
            </div>
            <Link to="/tasks" className={`inline-flex items-center gap-1 text-[11px] font-semibold ${isCS ? 'text-blue-600 hover:text-blue-700' : 'text-emerald-600 hover:text-emerald-700'}`}>
              View all <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <div className="divide-y divide-slate-100">
            {urgentTasks.length === 0 ? (
              <div className="px-6 py-12 text-center">
                <CheckCircle2 className="mx-auto h-7 w-7 text-emerald-500" />
                <p className="mt-3 text-sm font-medium text-slate-900">All clear</p>
                <p className="mt-1 text-xs text-slate-500">No open obligations require attention.</p>
              </div>
            ) : urgentTasks.map((task) => (
              <button key={task.id} onClick={() => setTaskId(task.id)} className="grid w-full gap-3 px-5 py-4 text-left transition hover:bg-slate-50/80 sm:grid-cols-[1fr_150px_110px] sm:items-center sm:px-6">
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold text-slate-900">{task.title}</p>
                  <p className="mt-1 truncate text-[10px] text-slate-500">{task.company?.name || 'Client company'}</p>
                </div>
                <div>
                  <p className="text-[9px] uppercase tracking-wider text-slate-400">Due date</p>
                  <p className="mt-1 text-[11px] font-medium text-slate-700">{formatDate(task.due_date)}</p>
                </div>
                <StatusBadge status={task.status} />
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-5">
          <div className="premium-card p-5 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-950">Portfolio health</p>
                <p className="mt-0.5 text-[10px] text-slate-500">Deadline risk indicator</p>
              </div>
              <span className={`text-2xl font-semibold tracking-[-0.04em] ${health >= 80 ? 'text-emerald-600' : health >= 60 ? 'text-amber-600' : 'text-rose-600'}`}>
                {health}%
              </span>
            </div>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className={`h-full rounded-full ${health >= 80 ? 'bg-emerald-500' : health >= 60 ? 'bg-amber-500' : 'bg-rose-500'}`} style={{ width: `${health}%` }} />
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-slate-50 p-3">
                <p className="text-[9px] uppercase tracking-wider text-slate-400">Open</p>
                <p className="mt-1 text-lg font-semibold text-slate-900">{Math.max(0, total - completed)}</p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <p className="text-[9px] uppercase tracking-wider text-slate-400">Completion</p>
                <p className="mt-1 text-lg font-semibold text-slate-900">{completion}%</p>
              </div>
            </div>
          </div>

          {isCS ? (
            <Link to="/regulatory-updates" className="group block overflow-hidden rounded-2xl bg-gradient-to-br from-[#3157D5] to-[#2242A4] p-5 text-white shadow-lg shadow-blue-900/10 transition hover:-translate-y-0.5 hover:shadow-xl">
              <Sparkles className="h-5 w-5 text-blue-200" />
              <p className="mt-5 text-sm font-semibold">Regulatory intelligence</p>
              <p className="mt-1 text-[11px] leading-5 text-blue-100/75">Search every collected MCA, SEBI, NSE, IBBI, RBI and related source from one place.</p>
              <span className="mt-4 inline-flex items-center gap-1 text-[10px] font-semibold">
                Explore library <ArrowRight className="h-3 w-3 transition group-hover:translate-x-1" />
              </span>
            </Link>
          ) : (
            <Link to="/financial-statements" className="group block overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-600 to-emerald-800 p-5 text-white shadow-lg shadow-emerald-900/10 transition hover:-translate-y-0.5 hover:shadow-xl">
              <FileSpreadsheet className="h-5 w-5 text-emerald-200" />
              <p className="mt-5 text-sm font-semibold">Financial Statements</p>
              <p className="mt-1 text-[11px] leading-5 text-emerald-100/75">View Balance Sheets, Profit & Loss summaries, Trial Balances, and Audit Reports instantly.</p>
              <span className="mt-4 inline-flex items-center gap-1 text-[10px] font-semibold">
                Check Statements <ArrowRight className="h-3 w-3 transition group-hover:translate-x-1" />
              </span>
            </Link>
          )}
        </div>
      </section>

      <section className="premium-card p-5 sm:p-6">
        <div className="mb-4 flex items-center gap-2">
          <UsersRound className={`h-4 w-4 ${isCS ? 'text-blue-600' : 'text-emerald-600'}`} />
          <p className="text-sm font-semibold text-slate-950">Recent team activity</p>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {logs.map((log) => (
            <div key={log.id} className="rounded-xl border border-slate-100 bg-slate-50/70 p-3.5">
              <p className="text-[11px] font-medium text-slate-800">
                {log.user?.full_name || 'System'} {(log.action || 'updated').replace(/_/g, ' ')}
              </p>
              <p className="mt-1.5 text-[9px] text-slate-400">{new Date(log.created_at).toLocaleString('en-IN')}</p>
            </div>
          ))}
        </div>
      </section>

      <TaskDetail taskId={taskId} isOpen={Boolean(taskId)} onClose={() => setTaskId(null)} />
    </div>
  );
};

export default Dashboard;
