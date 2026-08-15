import React, { useEffect, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { BookOpen, CheckCircle2, Copy, Mail, PenLine, RefreshCw, Search, ShieldCheck } from 'lucide-react';
import toast from 'react-hot-toast';
import ChatBox from '../components/ChatBox';
import { checkChatHealth, draftClientEmail } from '../services/chat';
import { useWorkspace } from '../context/WorkspaceContext';
import { useClients } from '../hooks/useClients';

const EmailDraftPanel = ({ workspaceMode, isCS }) => {
  const { data: clients = [], isLoading: clientsLoading } = useClients({ client_type: workspaceMode, is_active: true });
  const [clientId, setClientId] = useState('');
  const [recipientName, setRecipientName] = useState('');
  const [tone, setTone] = useState('professional');
  const [prompt, setPrompt] = useState('');
  
  // Editable draft states
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [hasDraft, setHasDraft] = useState(false);

  const generateDraft = useMutation({
    mutationFn: draftClientEmail,
    onSuccess: (result) => {
      setSubject(result.subject);
      setBody(result.body);
      setHasDraft(true);
    },
    onError: (error) => toast.error(error.message),
  });

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!clientId) return toast.error('Select a client');
    if (prompt.trim().length < 10) return toast.error('Describe the email in a little more detail');
    generateDraft.mutate({
      client_id: clientId,
      recipient_name: recipientName.trim() || null,
      tone,
      prompt: prompt.trim(),
    });
  };

  const copyDraft = async () => {
    await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
    toast.success('Email draft copied to clipboard');
  };

  const inputClass = 'w-full rounded-xl border border-slate-200 bg-slate-50/70 px-3.5 py-3 text-xs text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:bg-white focus:ring-4 focus:ring-blue-50';

  return (
    <section className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
      <form onSubmit={handleSubmit} className="premium-card p-5 sm:p-6">
        <div className="flex items-center gap-2">
          <PenLine className={`h-4 w-4 ${isCS ? 'text-blue-600' : 'text-emerald-600'}`} />
          <h2 className="text-sm font-semibold text-slate-950">Email brief</h2>
        </div>
        <div className="mt-5 space-y-4">
          <div>
            <label htmlFor="email-client" className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-slate-500">Client</label>
            <select id="email-client" value={clientId} onChange={(event) => setClientId(event.target.value)} className={inputClass} disabled={clientsLoading} required>
              <option value="">{clientsLoading ? 'Loading clients...' : 'Select client'}</option>
              {clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
            </select>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="recipient-name" className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-slate-500">Recipient name <span className="normal-case text-slate-400">(optional)</span></label>
              <input id="recipient-name" value={recipientName} onChange={(event) => setRecipientName(event.target.value)} placeholder="e.g. Mr. Mehta" className={inputClass} maxLength={100} />
            </div>
            <div>
              <label htmlFor="email-tone" className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-slate-500">Tone</label>
              <select id="email-tone" value={tone} onChange={(event) => setTone(event.target.value)} className={inputClass}>
                <option value="professional">Professional</option>
                <option value="friendly">Friendly</option>
                <option value="urgent">Urgent</option>
                <option value="concise">Concise</option>
              </select>
            </div>
          </div>
          <div>
            <label htmlFor="email-prompt" className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-slate-500">What should the email say?</label>
            <textarea id="email-prompt" value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={8} maxLength={2000} className={`${inputClass} resize-none`} placeholder="Example: Ask the client to share signed financial statements and bank statements by Friday for the annual filing. Mention that we will review them before submission." required />
            <p className="mt-1.5 text-right text-[9px] text-slate-400">{prompt.length}/2000</p>
          </div>
          <button type="submit" disabled={generateDraft.isPending || clientsLoading} className="premium-button-primary h-11 w-full justify-center disabled:bg-slate-300">
            {generateDraft.isPending ? <><RefreshCw className="h-3.5 w-3.5 animate-spin" /> Drafting...</> : <><Mail className="h-3.5 w-3.5" /> Generate email draft</>}
          </button>
        </div>
      </form>

      <div className="premium-card flex min-h-[520px] flex-col overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6">
          <div>
            <p className="text-sm font-semibold text-slate-950">Draft preview</p>
            <p className="mt-0.5 text-[10px] text-slate-500">Review and edit directly before sending to the client.</p>
          </div>
          {hasDraft && (
            <div className="flex items-center gap-2">
              <button type="button" onClick={handleSubmit} disabled={generateDraft.isPending} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-[10px] font-semibold text-slate-600 transition hover:bg-slate-50">
                <RefreshCw className={`h-3.5 w-3.5 ${generateDraft.isPending ? 'animate-spin' : ''}`} /> Regenerate
              </button>
              <button type="button" onClick={copyDraft} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-[10px] font-semibold text-slate-600 transition hover:bg-slate-50">
                <Copy className="h-3.5 w-3.5" /> Copy
              </button>
            </div>
          )}
        </div>
        {hasDraft ? (
          <div className="flex-1 bg-slate-50/50 p-5 sm:p-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
              <div>
                <label className="text-[9px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">Subject</label>
                <input value={subject} onChange={(e) => setSubject(e.target.value)} className="w-full text-sm font-semibold text-slate-950 border-b border-slate-200 pb-2 outline-none focus:border-blue-500" />
              </div>
              <div>
                <label className="text-[9px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">Body</label>
                <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={12} className="w-full text-xs leading-6 text-slate-700 outline-none resize-y border border-slate-100 rounded-lg p-3 focus:border-blue-500" />
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-1 items-center justify-center p-8 text-center">
            <div className="max-w-xs">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600"><Mail className="h-5 w-5" /></div>
              <p className="mt-4 text-sm font-semibold text-slate-900">Your draft will appear here</p>
              <p className="mt-2 text-xs leading-5 text-slate-500">Choose a client and describe the message. Missing details will be marked with placeholders instead of being invented.</p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

const Chat = () => {
  const [status, setStatus] = useState('checking');
  const [recordCount, setRecordCount] = useState(0);
  const [assistantMode, setAssistantMode] = useState('research');
  const { mode, isCS } = useWorkspace();

  const check = async () => {
    setStatus('checking');
    try {
      const result = await checkChatHealth();
      setRecordCount(result.records_indexed || 0);
      setStatus('ready');
    } catch {
      setStatus('unavailable');
    }
  };

  useEffect(() => { check(); }, []);

  if (status === 'checking') {
    return (
      <div className="premium-card flex min-h-[520px] items-center justify-center">
        <div className="text-center">
          <RefreshCw className={`mx-auto h-5 w-5 animate-spin ${isCS ? 'text-blue-600' : 'text-emerald-600'}`} />
          <p className="mt-3 text-xs text-slate-500">Preparing assistant…</p>
        </div>
      </div>
    );
  }

  if (status === 'unavailable') {
    return (
      <div className="premium-card flex min-h-[520px] items-center justify-center p-8">
        <div className="max-w-sm text-center">
          <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-50 text-amber-600">
            <RefreshCw className="h-5 w-5" />
          </div>
          <h2 className="mt-4 text-base font-semibold text-slate-950">Assistant is reconnecting</h2>
          <p className="mt-2 text-xs leading-5 text-slate-500">The regulatory library could not be reached. The rest of the dashboard remains available.</p>
          <button onClick={check} className="premium-button-primary mt-5 h-10 px-4">
            <RefreshCw className="h-3.5 w-3.5" /> Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-transition space-y-5">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="max-w-2xl">
          <div className={`mb-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] ${isCS ? 'text-blue-600' : 'text-emerald-600'}`}>
            {assistantMode === 'research' ? <ShieldCheck className="h-3.5 w-3.5" /> : <Mail className="h-3.5 w-3.5" />}
            {assistantMode === 'research' ? 'Regulatory Library Assistant' : 'Client Email Assistant'}
          </div>
          <h1 className="text-2xl font-semibold tracking-[-0.035em] text-slate-950">
            {assistantMode === 'research' ? 'Ask the regulatory library.' : 'Draft a client email.'}
          </h1>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            {assistantMode === 'research'
              ? 'Find answers across the indexed regulatory sources. Responses are synthesized from retrieved material and include links to the original publications.'
              : 'Turn a short brief into a professional, client-specific email. Every draft remains reviewable and is never sent automatically.'}
          </p>
        </div>
        {assistantMode === 'research' ? (
          <div className="inline-flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-[10px] font-medium text-emerald-700">
            <CheckCircle2 className="h-3.5 w-3.5" /> {recordCount.toLocaleString()} sources ready
          </div>
        ) : (
          <div className="inline-flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[10px] font-medium text-amber-700">
            <ShieldCheck className="h-3.5 w-3.5" /> Review required before sending
          </div>
        )}
      </section>

      <div className="inline-flex rounded-xl border border-slate-200 bg-white p-1 shadow-sm" role="tablist" aria-label="Assistant mode">
        <button type="button" role="tab" aria-selected={assistantMode === 'research'} onClick={() => setAssistantMode('research')} className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-[11px] font-semibold transition ${assistantMode === 'research' ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-500 hover:bg-slate-50'}`}><Search className="h-3.5 w-3.5" /> Research</button>
        <button type="button" role="tab" aria-selected={assistantMode === 'email'} onClick={() => setAssistantMode('email')} className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-[11px] font-semibold transition ${assistantMode === 'email' ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-500 hover:bg-slate-50'}`}><Mail className="h-3.5 w-3.5" /> Draft email</button>
      </div>

      {assistantMode === 'email' ? <EmailDraftPanel workspaceMode={mode} isCS={isCS} /> : <section className="grid gap-5 xl:grid-cols-[1fr_280px]">
        <div className="h-[620px]">
          <ChatBox />
        </div>
        <aside className="space-y-4">
          <div className="premium-card p-5">
            <Search className={`h-4 w-4 ${isCS ? 'text-blue-600' : 'text-emerald-600'}`} />
            <p className="mt-4 text-xs font-semibold text-slate-900">Ask focused questions</p>
            <ul className="mt-3 space-y-2 text-[10px] leading-4 text-slate-500">
              {isCS ? (
                <>
                  <li>Include a form or circular number</li>
                  <li>Name the relevant regulator</li>
                  <li>Mention the filing or obligation</li>
                  <li>Use one question at a time</li>
                </>
              ) : (
                <>
                  <li>Include a GST section or form number</li>
                  <li>Ask about Advance Tax computation</li>
                  <li>Describe a TDS slab deduction rate</li>
                  <li>Provide invoice reconciliation questions</li>
                </>
              )}
            </ul>
          </div>
          <div className="premium-card p-5">
            <BookOpen className={`h-4 w-4 ${isCS ? 'text-violet-600' : 'text-teal-600'}`} />
            <p className="mt-4 text-xs font-semibold text-slate-900">Example searches</p>
            <ul className="mt-3 space-y-2 text-[10px] leading-4 text-slate-500">
              {isCS ? (
                <>
                  <li>“MCA annual filing requirements”</li>
                  <li>“SEBI disclosure circular”</li>
                  <li>“IBBI insolvency regulations”</li>
                  <li>“Udyam registration guidance”</li>
                </>
              ) : (
                <>
                  <li>“GSTR-1 filing dates and penalties”</li>
                  <li>“Income Tax Advance Tax installment rules”</li>
                  <li>“TDS return requirements for corporations”</li>
                  <li>“GST Input Tax Credit (ITC) reconciliation”</li>
                </>
              )}
            </ul>
          </div>
        </aside>
      </section>}
    </div>
  );
};

export default Chat;