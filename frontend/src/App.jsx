import React, { Suspense, lazy, useLayoutEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './context/AuthContext';
import useAuth from './hooks/useAuth';

// Pages
const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ClientList = lazy(() => import('./pages/ClientList'));
const ClientDetail = lazy(() => import('./pages/ClientDetail'));
const TaskList = lazy(() => import('./pages/TaskList'));
const Chat = lazy(() => import('./pages/Chat'));
const Reconciliation = lazy(() => import('./pages/Reconciliation'));
const FinancialStatements = lazy(() => import('./pages/FinancialStatements'));
const AdminPanel = lazy(() => import('./pages/AdminPanel'));
const Reports = lazy(() => import('./pages/Reports'));
const RegulatoryUpdates = lazy(() => import('./pages/RegulatoryUpdates'));
const OrganizationManagement = lazy(() => import('./pages/OrganizationManagement'));
const ComplianceCalendar = lazy(() => import('./pages/ComplianceCalendar'));
const ReviewQueue = lazy(() => import('./pages/ReviewQueue'));
const WorkloadDashboard = lazy(() => import('./pages/WorkloadDashboard'));
const NotFound = lazy(() => import('./pages/NotFound'));

// Layout Assets
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import Loader from './components/Loader';

const queryClient = new QueryClient();

// Protected Routes
const ProtectedRoute = () => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) return <Loader fullScreen />;
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
};

// Admin Protection
const AdminRoute = () => {
  const { user, isAuthenticated, loading } = useAuth();
  
  if (loading) return <Loader fullScreen />;
  const hasAccess = isAuthenticated && (user?.role === 'admin' || user?.role === 'partner');
  return hasAccess ? <Outlet /> : <Navigate to="/dashboard" replace />;
};

const ManagerRoute = () => {
  const { user, isAuthenticated, loading } = useAuth();
  if (loading) return <Loader fullScreen />;
  const workRole = (user?.designation || user?.role || '').toLowerCase().replace(' ', '_');
  return isAuthenticated && ['manager', 'partner'].includes(workRole) ? <Outlet /> : <Navigate to="/dashboard" replace />;
};

const ScrollToTop = () => {
  const { pathname } = useLocation();

  useLayoutEffect(() => {
    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual';
    }
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }, [pathname]);

  return null;
};

const Layout = () => {
  return (
    <div className="min-h-screen bg-[#F7F8FA] text-[#101828]">
      <Sidebar />
      <div className="lg:pl-[236px]">
        <Navbar />
        <ScrollToTop />
        <main className="min-h-screen px-4 pb-28 pt-20 sm:px-6 lg:px-8 lg:pb-10">
          <div className="mx-auto max-w-[1280px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

const AppRoutes = () => {
  const { loading } = useAuth();

  if (loading) return <Loader fullScreen />;

  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Protected Routes */}
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/clients" element={<ClientList />} />
          <Route path="/clients/:id" element={<ClientDetail />} />
          <Route path="/tasks" element={<TaskList />} />
          <Route path="/review-queue" element={<ReviewQueue />} />
          <Route element={<ManagerRoute />}><Route path="/workload" element={<WorkloadDashboard />} /></Route>
          <Route path="/calendar" element={<ComplianceCalendar />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/reconciliation" element={<Reconciliation />} />
          <Route path="/financial-statements" element={<FinancialStatements />} />
          <Route path="/regulatory-updates" element={<RegulatoryUpdates />} />
          
          {/* Role Protected Panels */}
          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="/organization" element={<OrganizationManagement />} />
            <Route path="/reports" element={<Reports />} />
          </Route>
          
          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  );
};

import { WorkspaceProvider } from './context/WorkspaceContext';

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <AuthProvider>
          <WorkspaceProvider>
            <Suspense fallback={<Loader fullScreen />}>
              <AppRoutes />
            </Suspense>
          </WorkspaceProvider>
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: '#FFFFFF',
                color: '#0F172A',
                border: '1px solid #E5E7EB',
                boxShadow: '0 4px 16px rgba(15,23,42,0.08)',
              },
            }}
          />
        </AuthProvider>
      </Router>
    </QueryClientProvider>
  );
};

export default App;
