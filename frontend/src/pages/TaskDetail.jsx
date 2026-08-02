import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { X, Calendar, User, FileText, CheckCircle, AlertTriangle } from 'lucide-react';
import { useTaskDetails, useUpdateTaskMutation, useTransitionTaskMutation, useAddCommentMutation } from '../hooks/useTasks';
import { getUsers } from '../services/auth';
import { useAuth } from '../context/AuthContext';
import { formatDate, getDeadlineColorClass, getDeadlineLabel } from '../utils/dateUtils';
import StatusBadge from '../components/StatusBadge';
import Loader from '../components/Loader';
import api from '../services/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const TaskDetail = ({ taskId, isOpen, onClose }) => {
  const { user: currentUser, isAdmin } = useAuth();
  const [notesText, setNotesText] = useState('');
  const [refDocUrl, setRefDocUrl] = useState('');
  const [selectedAssignee, setSelectedAssignee] = useState('');
  const [workflowComment, setWorkflowComment] = useState('');
  const [newCommentText, setNewCommentText] = useState('');
  const [newRemarkText, setNewRemarkText] = useState('');

  const { data: task, isLoading, isError } = useTaskDetails(taskId);
  const queryClient = useQueryClient();

  const addRemarkMutation = useMutation({
    mutationFn: async ({ id, content }) => {
      return (await api.post(`/tasks/${id}/remarks`, { content })).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
      setNewRemarkText('');
    }
  });

  const { data: usersList } = useQuery({
    queryKey: ['users'],
    queryFn: getUsers,
    enabled: !!isOpen && isAdmin,
  });

  const updateTaskMutation = useUpdateTaskMutation();
  const transitionMutation = useTransitionTaskMutation();
  const addCommentMutation = useAddCommentMutation();

  useEffect(() => {
    if (task) {
      setNotesText(task.notes || '');
      setRefDocUrl(task.reference_doc || '');
      setSelectedAssignee(task.assigned_to || '');
    }
  }, [task]);

  if (!isOpen) return null;

  const workRole = (currentUser?.designation || currentUser?.role || '').toLowerCase().replace(' ', '_');
  const userPermissions = currentUser?.permissions || [];
  
  const canReviewAtLeadStage = isAdmin || workRole === 'team_lead' || workRole === 'manager' || userPermissions.includes('can_review_tasks');
  const canCloseApprovedWork = isAdmin || workRole === 'partner' || userPermissions.includes('can_approve_tasks');

  const handleWorkflowAction = (action) => {
    transitionMutation.mutate({
      id: taskId,
      action,
      comment: workflowComment
    }, {
      onSuccess: () => {
        setWorkflowComment('');
      }
    });
  };

  const handleAddComment = () => {
    if (!newCommentText.trim()) return;
    addCommentMutation.mutate({
      id: taskId,
      content: newCommentText
    }, {
      onSuccess: () => {
        setNewCommentText('');
      }
    });
  };

  const handleAddRemark = () => {
    if (!newRemarkText.trim()) return;
    addRemarkMutation.mutate({
      id: taskId,
      content: newRemarkText
    });
  };

  const handleSaveNotes = () => {
    updateTaskMutation.mutate({ id: taskId, data: { notes: notesText } });
  };

  const handleSaveRefDoc = () => {
    updateTaskMutation.mutate({ id: taskId, data: { reference_doc: refDocUrl } });
  };

  const handleAssigneeChange = (e) => {
    const newAssigneeId = e.target.value;
    setSelectedAssignee(newAssigneeId);
    updateTaskMutation.mutate({ id: taskId, data: { assigned_to: newAssigneeId || null } });
  };

  const deadlineColor = task ? getDeadlineColorClass(task.due_date, task.status === 'closed') : '';
  const deadlineLabel = task ? getDeadlineLabel(task.due_date) : '';

  const inputCls = "w-full h-9 bg-[#F8FAFC] border border-[#E5E7EB] rounded-md text-[#0F172A] text-xs px-3 focus:border-[#2563EB] outline-none";

  return (
    <>
      <div
        className="fixed inset-0 bg-[#0F172A]/30 backdrop-blur-[2px] z-40 transition-opacity duration-200"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 z-50 w-[480px] h-screen bg-white border-l border-[#E5E7EB] shadow-2xl flex flex-col">
        <div className="p-4 border-b border-[#E5E7EB] flex items-center justify-between bg-[#F8FAFC]">
          <div className="flex items-center space-x-3 min-w-0 pr-4">
            <StatusBadge status={task?.status} />
            <span className="text-[11px] text-[#64748B] font-mono select-all truncate">ID: {taskId.slice(0, 8)}</span>
          </div>
          <button
            onClick={onClose}
            className="text-[#64748B] hover:text-[#0F172A] p-1 rounded-md hover:bg-[#F1F5F9] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoading ? (
            <Loader />
          ) : isError || !task ? (
            <div className="p-8 text-center text-[#EF4444] text-xs font-semibold flex items-center gap-2 justify-center">
              <AlertTriangle className="w-5 h-5" />
              Failed to load task details.
            </div>
          ) : (
            <>
              <div>
                <h3 className="text-[#0F172A] text-lg font-bold leading-snug">{task.title}</h3>
                <div className="mt-2 text-xs flex flex-wrap items-center gap-1.5 text-[#64748B]">
                  <span className="font-semibold text-[#0F172A]">Company:</span>
                  <Link
                    to={`/clients/${task.company_id}`}
                    onClick={onClose}
                    className="text-[#2563EB] hover:underline"
                  >
                    {task.company?.name}
                  </Link>
                  {task.rule && (
                    <>
                      <span className="text-[#CBD5E1] font-mono">/</span>
                      <span>Rule: {task.rule.name}</span>
                      {task.rule.form_number && (
                        <span className="bg-[#2563EB]/10 text-[#2563EB] px-1.5 py-0.5 rounded font-mono text-[10px] font-bold">
                          {task.rule.form_number}
                        </span>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* Reviews & Remarks Section */}
              <div className="space-y-3 bg-amber-50/50 border border-amber-200/60 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="block text-xs font-bold text-amber-900 uppercase tracking-wide">Reviews & Remarks</span>
                  <span className="text-[10px] font-mono text-amber-700 bg-amber-100/80 px-2 py-0.5 rounded">Append-only Log</span>
                </div>
                <p className="text-[11px] text-amber-800 leading-normal">
                  Record delay reasons, pending actions, or issues encountered during filing. Accessible by any authorized user.
                </p>

                {task.remarks && task.remarks.length > 0 ? (
                  <div className="space-y-2 pt-1">
                    {task.remarks.map((remark) => (
                      <div key={remark.id} className="bg-white border border-amber-200 rounded-md p-3 text-xs shadow-sm">
                        <div className="flex justify-between items-center mb-1">
                          <span className="font-bold text-[#0F172A]">{remark.user_name}</span>
                          <span className="text-[10px] text-[#94A3B8] font-mono">
                            {new Date(remark.created_at).toLocaleString('en-IN')}
                          </span>
                        </div>
                        <p className="text-slate-700 leading-relaxed break-words">{remark.content}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-amber-800/70 italic text-center py-2 bg-white/60 border border-dashed border-amber-200 rounded-md">
                    No remarks recorded yet.
                  </p>
                )}

                <div className="flex gap-2 pt-1">
                  <input
                    type="text"
                    placeholder="Add a remark (delay reason, review note, issue)..."
                    value={newRemarkText}
                    onChange={(e) => setNewRemarkText(e.target.value)}
                    className="flex-grow h-8 bg-white border border-amber-300 rounded-md px-3 text-[#0F172A] placeholder-amber-400 outline-none text-xs focus:border-amber-600"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleAddRemark();
                    }}
                  />
                  <button
                    onClick={handleAddRemark}
                    disabled={addRemarkMutation.isPending || !newRemarkText.trim()}
                    className="h-8 bg-amber-600 hover:bg-amber-700 text-white px-3 rounded-md text-xs font-bold transition-colors disabled:opacity-50 shadow-sm"
                  >
                    Add Remark
                  </button>
                </div>
              </div>

              <div className="bg-[#F8FAFC] border border-[#E5E7EB] rounded-lg p-4 flex items-center justify-between">
                <div className="space-y-1">
                  <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider block">Due Date</span>
                  <div className="flex items-center space-x-2">
                    <Calendar className={`w-4 h-4 ${deadlineColor}`} />
                    <span className={`text-base font-bold font-mono ${deadlineColor}`}>{formatDate(task.due_date)}</span>
                  </div>
                </div>
                {task.status !== 'closed' && (
                  <span className={`text-xs font-bold font-mono px-2 py-1 rounded bg-[#F1F5F9] ${deadlineColor}`}>
                    {deadlineLabel}
                  </span>
                )}
              </div>

              <div className="space-y-2">
                <label className="block text-xs font-bold text-[#64748B] uppercase tracking-wide">Assignee</label>
                {isAdmin ? (
                  <select
                    value={selectedAssignee}
                    onChange={handleAssigneeChange}
                    disabled={updateTaskMutation.isPending}
                    className={inputCls}
                  >
                    <option value="">Unassigned</option>
                    {usersList?.map((u) => (
                      <option key={u.id} value={u.id}>{u.full_name || u.email} ({u.role})</option>
                    ))}
                  </select>
                ) : (
                  <div className="flex items-center space-x-2.5 px-3 py-2 bg-[#F8FAFC] border border-[#E5E7EB] rounded-md">
                    <User className="w-4 h-4 text-[#64748B]" />
                    <span className="text-xs text-[#0F172A]">
                      {task.assigned_user?.full_name || task.assigned_user?.email || 'Unassigned'}
                    </span>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <label className="block text-xs font-bold text-[#64748B] uppercase tracking-wide">Notes</label>
                <textarea
                  rows={4}
                  value={notesText}
                  onChange={(e) => setNotesText(e.target.value)}
                  placeholder="Enter compliance notes, filing details, or internal steps..."
                  className="w-full bg-[#F8FAFC] border border-[#E5E7EB] rounded-md p-3 text-[#0F172A] placeholder-[#94A3B8] outline-none text-xs leading-relaxed focus:border-[#2563EB]"
                />
                <button
                  onClick={handleSaveNotes}
                  disabled={updateTaskMutation.isPending}
                  className="h-8 bg-[#F1F5F9] border border-[#E5E7EB] text-[#0F172A] px-4 py-1.5 rounded-md hover:bg-[#2563EB]/8 hover:text-[#2563EB] text-xs font-medium transition-colors"
                >
                  Save Notes
                </button>
              </div>

              <div className="space-y-2">
                <label className="block text-xs font-bold text-[#64748B] uppercase tracking-wide">Reference Document (URL)</label>
                <div className="flex gap-2">
                  <input
                    type="url"
                    placeholder="https://example.com/filing-receipt"
                    value={refDocUrl}
                    onChange={(e) => setRefDocUrl(e.target.value)}
                    className="flex-1 h-9 bg-[#F8FAFC] border border-[#E5E7EB] rounded-md px-3 text-[#0F172A] placeholder-[#94A3B8] outline-none text-xs focus:border-[#2563EB]"
                  />
                  <button
                    onClick={handleSaveRefDoc}
                    disabled={updateTaskMutation.isPending}
                    className="h-9 bg-[#F1F5F9] border border-[#E5E7EB] text-[#0F172A] px-3 rounded-md hover:bg-[#2563EB]/8 hover:text-[#2563EB] text-xs font-medium transition-colors"
                  >
                    Set URL
                  </button>
                </div>
                {task.reference_doc && (
                  <a
                    href={task.reference_doc}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-[#2563EB] hover:underline flex items-center gap-1.5 font-mono pt-1"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    Open Receipt / Proof Document
                  </a>
                )}
              </div>

              {task.status !== 'closed' && (
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-4">
                  <span className="text-[11px] font-bold text-[#64748B] uppercase tracking-wider block">Workflow Review Stage</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-800">Current Stage:</span>
                    <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider font-mono rounded bg-blue-100 text-blue-800">
                      {(task.current_stage || 'executive').replace('_', ' ')}
                    </span>
                  </div>

                  {(task.status === 'pending' || task.status === 'returned_with_comments' || task.status === 'in_progress' || task.status === 'completed_by_executive') && (
                    <div className="space-y-3">
                      <textarea
                        rows={2}
                        value={workflowComment}
                        onChange={(e) => setWorkflowComment(e.target.value)}
                        placeholder="Add completion or submission notes (optional)..."
                        className="w-full bg-white border border-[#E5E7EB] rounded-md p-2 text-xs outline-none focus:border-[#2563EB]"
                      />
                      <button
                        onClick={() => handleWorkflowAction(task.status === 'in_progress' ? 'complete' : task.status === 'completed_by_executive' ? 'submit' : 'start')}
                        disabled={transitionMutation.isPending}
                        className="w-full h-8 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-bold transition-colors disabled:opacity-50"
                      >
                        {task.status === 'in_progress' ? 'Mark Completed by Executive' : task.status === 'completed_by_executive' ? 'Submit for Team Lead Review' : 'Start Work'}
                      </button>
                    </div>
                  )}

                  {task.status === 'waiting_for_review' && (
                    <div className="space-y-3">
                      {canReviewAtLeadStage ? (
                        <>
                          <textarea
                            rows={2}
                            value={workflowComment}
                            onChange={(e) => setWorkflowComment(e.target.value)}
                            placeholder="Add review feedback / comment..."
                            className="w-full bg-white border border-[#E5E7EB] rounded-md p-2 text-xs outline-none focus:border-[#2563EB]"
                          />
                          <div className="grid grid-cols-3 gap-2">
                            <button
                              onClick={() => handleWorkflowAction('approve')}
                              disabled={transitionMutation.isPending}
                              className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-xs font-bold transition-colors disabled:opacity-50"
                            >
                              Approve to Partner
                            </button>
                            <button
                              onClick={() => handleWorkflowAction('return')}
                              disabled={transitionMutation.isPending}
                              className="h-8 bg-amber-500 hover:bg-amber-600 text-white rounded-md text-xs font-bold transition-colors disabled:opacity-50"
                            >
                              Return with Comments
                            </button>
                          </div>
                        </>
                      ) : (
                        <p className="text-xs text-slate-500 italic">Waiting for Team Lead review. You do not have permissions to review at this stage.</p>
                      )}
                    </div>
                  )}

                  {task.status === 'approved' && (
                    <div className="space-y-3">
                      {canCloseApprovedWork ? (
                        <>
                          <textarea
                            rows={2}
                            value={workflowComment}
                            onChange={(e) => setWorkflowComment(e.target.value)}
                            placeholder="Add final approval comments..."
                            className="w-full bg-white border border-[#E5E7EB] rounded-md p-2 text-xs outline-none focus:border-[#2563EB]"
                          />
                          <div className="grid grid-cols-3 gap-2">
                            <button
                              onClick={() => handleWorkflowAction('close')}
                              disabled={transitionMutation.isPending}
                              className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-xs font-bold transition-colors disabled:opacity-50"
                            >
                              Close Task
                            </button>
                          </div>
                        </>
                      ) : (
                        <p className="text-xs text-slate-500 italic">Waiting for Partner approval. You do not have permissions to approve at this stage.</p>
                      )}
                    </div>
                  )}
                </div>
              )}

              {task.status === 'closed' && (
                <div className="bg-[#F0FDF4] border border-[#22C55E]/20 rounded-lg p-4 space-y-2 text-xs leading-relaxed text-[#64748B]">
                  <span className="font-bold text-[#0F172A] block">Completion Record</span>
                  <p>Completed by:{' '}
                    <span className="text-[#0F172A] font-medium">
                      {task.completed_user?.full_name || task.completed_user?.email || 'System'}
                    </span>
                  </p>
                  <p>Timestamp: <span className="text-[#0F172A] font-mono">{new Date(task.completed_at).toLocaleString('en-IN')}</span></p>
                </div>
              )}

              <div className="space-y-3">
                <span className="block text-xs font-bold text-[#64748B] uppercase tracking-wide">Discussion & Comments</span>
                
                {task.comments && task.comments.length > 0 ? (
                  <div className="space-y-2">
                    {task.comments.map((comment) => (
                      <div key={comment.id} className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-xs">
                        <div className="flex justify-between items-center mb-1">
                          <span className="font-bold text-[#0F172A]">{comment.user_name}</span>
                          <span className="text-[10px] text-[#94A3B8] font-mono">
                            {new Date(comment.created_at).toLocaleString('en-IN')}
                          </span>
                        </div>
                        <p className="text-slate-700 leading-relaxed break-words">{comment.content}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-[#64748B] italic text-center py-2 bg-slate-50 border border-dashed border-slate-200 rounded-lg">No comments yet. Start the discussion below!</p>
                )}

                <div className="flex gap-2 pt-1">
                  <input
                    type="text"
                    placeholder="Write a comment..."
                    value={newCommentText}
                    onChange={(e) => setNewCommentText(e.target.value)}
                    className="flex-grow h-8 bg-[#F8FAFC] border border-[#E5E7EB] rounded-md px-3 text-[#0F172A] placeholder-[#94A3B8] outline-none text-xs focus:border-[#2563EB]"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleAddComment();
                    }}
                  />
                  <button
                    onClick={handleAddComment}
                    disabled={addCommentMutation.isPending || !newCommentText.trim()}
                    className="h-8 bg-slate-800 hover:bg-slate-950 text-white px-3 rounded-md text-xs font-bold transition-colors disabled:opacity-50"
                  >
                    Post
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                <span className="block text-xs font-bold text-[#64748B] uppercase tracking-wide">Audit Trail</span>
                {task.audit_logs && task.audit_logs.length > 0 ? (
                  <div className="relative border-l border-[#E5E7EB] ml-2 pl-4 space-y-3 text-xs leading-relaxed">
                    {task.audit_logs.map((log) => (
                      <div key={log.id} className="relative group">
                        <div className="absolute -left-[20px] top-1 w-2.5 h-2.5 rounded-full bg-[#E5E7EB] border-2 border-white" />
                        <div>
                          <p className="text-[#0F172A] font-medium text-slate-800">
                            <span className="font-semibold">{log.user?.full_name || 'System'}</span>{' '}
                            {log.action.replace(/_/g, ' ')}
                          </p>
                          {log.action_metadata?.comment && (
                            <p className="text-[#475569] italic bg-slate-50 border border-slate-100 rounded px-2 py-1 mt-1 text-[11px]">
                              "{log.action_metadata.comment}"
                            </p>
                          )}
                          <span className="text-[10px] text-[#94A3B8] font-mono block mt-0.5">
                            {new Date(log.created_at).toLocaleString('en-IN')}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-[#64748B] italic">No audit trail recorded for this task.</p>
                )}
              </div>
            </>
          )}
        </div>

      </div>
    </>
  );
};

export default TaskDetail;
