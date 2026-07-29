import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Filter, Calendar, User, Building, CheckSquare, Edit3, X, CheckCircle, RefreshCcw } from 'lucide-react';
import { getTasks } from '../services/tasks';
import { getCompanies } from '../services/clients';
import { getUsers } from '../services/auth';
import { useCompleteTaskMutation, useUpdateTaskMutation } from '../hooks/useTasks';
import Loader, { TableRowSkeleton } from '../components/Loader';
import EmptyState from '../components/EmptyState';
import StatusBadge from '../components/StatusBadge';
import TaskDetail from './TaskDetail';
import { formatDate, getDeadlineColorClass } from '../utils/dateUtils';
import api from '../services/api';
import { toast } from 'react-hot-toast';
import { useWorkspace } from '../context/WorkspaceContext';
import { useAuth } from '../context/AuthContext';

const TaskList = () => {
  const location = useLocation();
  const queryClient = useQueryClient();
  const { mode, isCS, isCA } = useWorkspace();
  const { user } = useAuth();
  const workRole = (user?.designation || user?.role || '').toLowerCase().replaceAll(' ', '_');
  const isExecutive = ['executive', 'intern', 'staff'].includes(workRole);
  const [searchQuery, setSearchQuery] = useState('');
  
  const [selectedStatuses, setSelectedStatuses] = useState([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState('');
  const [selectedAssigneeId, setSelectedAssigneeId] = useState('');
  const [dueStart, setDueStart] = useState('');
  const [dueEnd, setDueEnd] = useState('');
  
  const [selectedTaskIds, setSelectedTaskIds] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [bulkAssigneeId, setBulkAssigneeId] = useState('');

  useEffect(() => {
    if (location.state?.filterStatus) {
      setSelectedStatuses([location.state.filterStatus]);
    }
  }, [location]);

  const { data: tasks, isLoading: isTasksLoading } = useQuery({
    queryKey: ['tasks', mode],
    queryFn: () => getTasks({ category: mode }),
    staleTime: 30000,
  });

  const { data: companies } = useQuery({
    queryKey: ['companies', mode],
    queryFn: () => getCompanies({ client_type: mode }),
    enabled: !isExecutive,
  });

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: getUsers,
    enabled: !isExecutive,
  });

  const completeMutation = useCompleteTaskMutation();
  const updateMutation = useUpdateTaskMutation();

  const toggleStatusFilter = (status) => {
    setSelectedStatuses((prev) =>
      prev.includes(status) ? prev.filter((s) => s !== status) : [...prev, status]
    );
  };

  const handleRowClick = (taskId) => {
    setSelectedTaskId(taskId);
    setDrawerOpen(true);
  };

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedTaskIds(filteredTasks.map((t) => t.id));
    } else {
      setSelectedTaskIds([]);
    }
  };

  const handleSelectTask = (e, taskId) => {
    e.stopPropagation();
    if (e.target.checked) {
      setSelectedTaskIds((prev) => [...prev, taskId]);
    } else {
      setSelectedTaskIds((prev) => prev.filter((id) => id !== taskId));
    }
  };

  const handleBulkComplete = async () => {
    try {
      toast.loading('Completing tasks...', { id: 'bulk' });
      await Promise.all(selectedTaskIds.map((id) => api.post(`/tasks/${id}/complete`)));
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['reports-summary'] });
      setSelectedTaskIds([]);
      toast.success('Tasks completed successfully', { id: 'bulk' });
    } catch (err) {
      toast.error('Failed to complete some tasks', { id: 'bulk' });
    }
  };

  const handleBulkReassign = async (e) => {
    const assigneeId = e.target.value;
    if (!assigneeId) return;
    try {
      toast.loading('Reassigning tasks...', { id: 'bulk' });
      await Promise.all(
        selectedTaskIds.map((id) => api.put(`/tasks/${id}`, { assigned_to: assigneeId }))
      );
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setSelectedTaskIds([]);
      setBulkAssigneeId('');
      toast.success('Tasks reassigned successfully', { id: 'bulk' });
    } catch (err) {
      toast.error('Failed to reassign tasks', { id: 'bulk' });
    }
  };

  const filteredTasks = tasks?.filter((task) => {
    const searchMatch =
      task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      task.company?.name?.toLowerCase().includes(searchQuery.toLowerCase());
    const statusMatch = selectedStatuses.length === 0 || selectedStatuses.includes(task.status);
    const companyMatch = !selectedCompanyId || task.company_id === selectedCompanyId;
    const assigneeMatch = !selectedAssigneeId || task.assigned_to === selectedAssigneeId;
    const taskDateStr = task.due_date;
    const dateStartMatch = !dueStart || taskDateStr >= dueStart;
    const dateEndMatch = !dueEnd || taskDateStr <= dueEnd;
    return searchMatch && statusMatch && companyMatch && assigneeMatch && dateStartMatch && dateEndMatch;
  }) || [];

  return (
    <div className="space-y-6 page-transition relative pb-20">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-bold text-[#0F172A] tracking-tight">{isExecutive ? 'My Tasks' : 'Compliance Obligations'}</h1>
        <p className="text-xs text-[#64748B] mt-0.5">{isExecutive ? 'Review and complete the compliance work assigned to you.' : 'Filter, reassign, and finalize regulatory filings across all clients.'}</p>
      </div>

      {/* Advanced Filter Bar */}
      <div className="bg-white border border-[#E5E7EB] rounded-lg p-4 space-y-4 sticky top-14 z-20 shadow-sm">
        <div className={`grid grid-cols-1 gap-3 ${isExecutive ? 'md:grid-cols-2' : 'md:grid-cols-4'}`}>
          <div className="flex items-center bg-[#F8FAFC] border border-[#E5E7EB] rounded-md px-3 py-2 text-xs focus-within:border-[#2563EB] transition-colors">
            <Search className="w-4 h-4 text-[#64748B] mr-2 shrink-0" />
            <input
              type="text"
              placeholder="Search tasks or company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-transparent border-none text-[#0F172A] placeholder-[#94A3B8] outline-none w-full"
            />
          </div>

          {!isExecutive && <div className="flex items-center bg-[#F8FAFC] border border-[#E5E7EB] rounded-md px-2 py-1">
            <Building className="w-3.5 h-3.5 text-[#64748B] mr-2 shrink-0" />
            <select
              value={selectedCompanyId}
              onChange={(e) => setSelectedCompanyId(e.target.value)}
              className="bg-transparent border-none text-[#0F172A] text-xs outline-none w-full"
            >
              <option value="">All Companies</option>
              {companies?.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>}

          {!isExecutive && <div className="flex items-center bg-[#F8FAFC] border border-[#E5E7EB] rounded-md px-2 py-1">
            <User className="w-3.5 h-3.5 text-[#64748B] mr-2 shrink-0" />
            <select
              value={selectedAssigneeId}
              onChange={(e) => setSelectedAssigneeId(e.target.value)}
              className="bg-transparent border-none text-[#0F172A] text-xs outline-none w-full"
            >
              <option value="">All Assignees</option>
              {users?.map((u) => (
                <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
              ))}
            </select>
          </div>}

          <div className="flex items-center bg-[#F8FAFC] border border-[#E5E7EB] rounded-md px-2 py-1 space-x-1 min-w-0">
            <Calendar className="w-3.5 h-3.5 text-[#64748B] shrink-0" />
            <input
              type="date"
              value={dueStart}
              onChange={(e) => setDueStart(e.target.value)}
              className="bg-transparent border-none text-[#0F172A] text-[10px] outline-none w-full"
            />
            <span className="text-[#94A3B8] font-mono text-[10px]">to</span>
            <input
              type="date"
              value={dueEnd}
              onChange={(e) => setDueEnd(e.target.value)}
              className="bg-transparent border-none text-[#0F172A] text-[10px] outline-none w-full"
            />
          </div>
        </div>

        {/* Status Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-[#F1F5F9]">
          <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider mr-2">Status:</span>
          {['pending', 'in_progress', 'completed_by_executive', 'waiting_for_review', 'approved', 'returned_with_comments', 'closed'].map((status) => {
            const isSelected = selectedStatuses.includes(status);
            const label = status.replace('_', ' ').toUpperCase();
            
            let pillClass = '';
            if (status === 'returned_with_comments') pillClass = isSelected ? 'bg-[#F59E0B] text-white' : 'border border-[#F59E0B]/25 text-[#F59E0B] hover:bg-[#F59E0B]/8';
            else if (status === 'waiting_for_review') pillClass = isSelected ? 'bg-purple-600 text-white' : 'border border-purple-200 text-purple-700 hover:bg-purple-50';
            else if (status === 'closed') pillClass = isSelected ? 'bg-slate-700 text-white' : 'border border-slate-200 text-slate-700 hover:bg-slate-50';
            else pillClass = isSelected ? 'bg-[#2563EB] text-white' : 'border border-[#2563EB]/25 text-[#2563EB] hover:bg-[#2563EB]/8';

            return (
              <button
                key={status}
                onClick={() => toggleStatusFilter(status)}
                className={`px-2.5 py-1 text-[10px] font-mono font-bold tracking-wider rounded-md uppercase transition-all duration-150 ${pillClass}`}
              >
                {label}
              </button>
            );
          })}
          {(selectedStatuses.length > 0 || selectedCompanyId || selectedAssigneeId || dueStart || dueEnd) && (
            <button
              onClick={() => {
                setSelectedStatuses([]);
                setSelectedCompanyId('');
                setSelectedAssigneeId('');
                setDueStart('');
                setDueEnd('');
              }}
              className="text-[10px] font-mono text-[#64748B] hover:text-[#0F172A] hover:underline inline-flex items-center gap-1 ml-auto"
            >
              <X className="w-3.5 h-3.5" />
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Task Table */}
      {isTasksLoading ? (
        <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden shadow-sm">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#E5E7EB] bg-[#F8FAFC] h-10">
                {!isExecutive && <th className="p-4 w-10"></th>}
                <th className="p-4 text-[#64748B] font-bold uppercase text-[10px] tracking-wider">Title</th>
                <th className="p-4 text-[#64748B] font-bold uppercase text-[10px] tracking-wider">Company</th>
                <th className="p-4 text-[#64748B] font-bold uppercase text-[10px] tracking-wider">Due Date</th>
                <th className="p-4 text-[#64748B] font-bold uppercase text-[10px] tracking-wider">Status</th>
                <th className="p-4 text-[#64748B] font-bold uppercase text-[10px] tracking-wider">Assigned</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 5 }).map((_, idx) => (
                <TableRowSkeleton key={idx} cols={6} />
              ))}
            </tbody>
          </table>
        </div>
      ) : filteredTasks.length === 0 ? (
        <EmptyState title="No tasks found" description="Adjust your filters or query settings to fetch active compliance tasks." />
      ) : (
        <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#E5E7EB] bg-[#F8FAFC] text-[10px] font-bold text-[#64748B] uppercase tracking-wider h-11">
                  {!isExecutive && <th className="p-4 w-10">
                    <input
                      type="checkbox"
                      onChange={handleSelectAll}
                      checked={selectedTaskIds.length === filteredTasks.length && filteredTasks.length > 0}
                      className="rounded border-[#E5E7EB] text-[#2563EB]"
                    />
                  </th>}
                  <th className="p-4">Obligation Title</th>
                  <th className="p-4">Company</th>
                  <th className="p-4">Due Date</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Assigned</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F1F5F9]">
                {filteredTasks.map((task) => {
                  const isChecked = selectedTaskIds.includes(task.id);
                  const deadlineColor = getDeadlineColorClass(task.due_date, task.status === 'closed');
                  const assigned = users?.find((u) => u.id === task.assigned_to) || task.assigned_user;

                  return (
                    <tr
                      key={task.id}
                      onClick={() => handleRowClick(task.id)}
                      className={`h-12 hover:bg-[#F8FAFC] cursor-pointer transition-all duration-150 group ${
                        isChecked ? 'bg-[#EFF6FF]' : ''
                      }`}
                    >
                      {!isExecutive && <td className="p-4" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => handleSelectTask(e, task.id)}
                          className="rounded border-[#E5E7EB] text-[#2563EB]"
                        />
                      </td>}
                      <td className="p-4 font-semibold text-[#0F172A] group-hover:text-[#2563EB] transition-colors max-w-xs truncate">
                        {task.title}
                      </td>
                      <td className="p-4 text-[#64748B] font-medium truncate max-w-[150px]">
                        {task.company?.name || 'Client Company'}
                      </td>
                      <td className={`p-4 font-mono ${deadlineColor}`}>
                        {formatDate(task.due_date)}
                      </td>
                      <td className="p-4">
                        <StatusBadge status={task.status} />
                      </td>
                      <td className="p-4 text-[#0F172A]">
                        {assigned ? assigned.full_name || assigned.email : 'Unassigned'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Floating Bulk Action Bar */}
      {!isExecutive && selectedTaskIds.length > 0 && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-white border border-[#E5E7EB] px-6 py-3.5 rounded-full shadow-2xl shadow-[#0F172A]/15 z-30 flex items-center gap-6 text-xs page-transition">
          <span className="text-[#64748B] font-medium">
            <span className="text-[#0F172A] font-bold font-mono mr-1">{selectedTaskIds.length}</span>
            tasks selected
          </span>
          
          <div className="h-4 w-[1px] bg-[#E5E7EB]" />

          <div className="flex items-center space-x-2">
            <span className="text-[#64748B] text-[10px] uppercase font-bold tracking-wider">Reassign:</span>
            <select
              value={bulkAssigneeId}
              onChange={handleBulkReassign}
              className="bg-[#F8FAFC] border border-[#E5E7EB] rounded-md h-8 text-[#0F172A] px-2"
            >
              <option value="">Select Assignee</option>
              {users?.map((u) => (
                <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
              ))}
            </select>
          </div>

          <button
            onClick={handleBulkComplete}
            className="h-8 bg-[#2563EB] hover:bg-[#1D4ED8] text-white px-4 rounded-md font-semibold inline-flex items-center gap-1.5 transition-colors"
          >
            <CheckCircle className="w-4 h-4" />
            Complete Selected
          </button>

          <button onClick={() => setSelectedTaskIds([])} className="p-1 hover:bg-[#F1F5F9] rounded-full text-[#64748B] hover:text-[#0F172A]">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <TaskDetail taskId={selectedTaskId} isOpen={drawerOpen} onClose={() => { setDrawerOpen(false); setSelectedTaskId(null); }} />
    </div>
  );
};

export default TaskList;
