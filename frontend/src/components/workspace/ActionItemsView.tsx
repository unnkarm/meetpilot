import React, { useState } from 'react';
import {
  CheckSquare,
  Plus,
  Trash2,
  Play,
  Clock,
  User,
  Calendar,
  ExternalLink,
  Loader2,
  CheckCircle2,
  Edit3,
  Save,
  X,
} from 'lucide-react';
import { ApiTask, ApiWorkspaceMember, TaskPriority, TaskStatus } from '../../types';
import { useMeetingText } from './MeetingLanguageDisplay';
import { useWorkspaceManager } from '../../utils/workspacePermissions';

interface ActionItemsViewProps {
  tasks: ApiTask[];
  onUpdateTaskStatus: (taskId: string, status: TaskStatus) => Promise<void>;
  onDeleteTask: (taskId: string, title: string) => void;
  onAddTask: (title: string, assignee: string, priority: TaskPriority, dueDate: string) => Promise<void>;
  onSeek: (seconds: number) => void;
  onOpenKanban: () => void;
  members: ApiWorkspaceMember[];
  onUpdateTask: (taskId: string, updates: { title: string; assignee_name: string | null; priority: TaskPriority; due_date: string | null }) => Promise<void>;
}

export const ActionItemsView: React.FC<ActionItemsViewProps> = ({
  tasks,
  onUpdateTaskStatus,
  onDeleteTask,
  onAddTask,
  onSeek,
  onOpenKanban,
  members,
  onUpdateTask,
}) => {
  const canManage = useWorkspaceManager();
  const displayText = useMeetingText();
  const [newTitle, setNewTitle] = useState('');
  const [newAssignee, setNewAssignee] = useState('');
  const [newPriority, setNewPriority] = useState<TaskPriority>('medium');
  const [newDueDate, setNewDueDate] = useState('');
  const [isAdding, setIsAdding] = useState(false);
  const [updatingTaskId, setUpdatingTaskId] = useState<string | null>(null);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editAssignee, setEditAssignee] = useState('');
  const [editPriority, setEditPriority] = useState<TaskPriority>('medium');
  const [editDueDate, setEditDueDate] = useState('');

  const beginEdit = (task: ApiTask) => {
    setEditingTaskId(task.id);
    setEditTitle(task.title);
    setEditAssignee(task.assignee_id || task.assignee_name || '');
    setEditPriority(task.priority);
    setEditDueDate(task.due_date || '');
  };

  const saveEdit = async () => {
    if (!editingTaskId || !editTitle.trim()) return;
    setUpdatingTaskId(editingTaskId);
    try {
      await onUpdateTask(editingTaskId, { title: editTitle.trim(), assignee_name: editAssignee || null,
        priority: editPriority, due_date: editDueDate || null });
      setEditingTaskId(null);
    } finally { setUpdatingTaskId(null); }
  };

  const parseTimestampSeconds = (ts?: string | null): number | null => {
    if (!ts) return null;
    const parts = ts.replace('@', '').split(':').map(Number);
    if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
      return parts[0] * 60 + parts[1];
    }
    const single = Number(ts);
    return !isNaN(single) ? single : null;
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || isAdding) return;
    setIsAdding(true);
    try {
      await onAddTask(newTitle.trim(), newAssignee.trim(), newPriority, newDueDate);
      setNewTitle('');
      setNewAssignee('');
      setNewDueDate('');
    } finally {
      setIsAdding(false);
    }
  };

  const handleStatusChange = async (taskId: string, newStatus: TaskStatus) => {
    setUpdatingTaskId(taskId);
    try {
      await onUpdateTaskStatus(taskId, newStatus);
    } finally {
      setUpdatingTaskId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Title & Kanban Link */}
      <div className="p-6 rounded-xl bg-surface border border-line space-y-4 shadow-sm">
        <div className="flex items-center justify-between pb-3 border-b border-line">
          <div className="flex items-center gap-2">
            <CheckSquare className="w-4 h-4 text-brand" />
            <h3 className="text-sm font-bold text-ink uppercase tracking-wider">
              Action Items ({tasks.length})
            </h3>
          </div>

          <button
            onClick={onOpenKanban}
            className="text-sm text-brand hover:text-brand flex items-center gap-1 font-bold cursor-pointer transition-colors"
          >
            <span>Open Workspace Kanban</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Tasks List / Grid */}
        {tasks.length === 0 ? (
          <div className="p-10 text-center border border-dashed border-line rounded-xl space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-700 mx-auto" />
            <p className="text-sm text-muted">
              {canManage ? 'No action items were identified in this meeting.' : 'No tasks are assigned to you in this meeting.'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {tasks.map((task) => {
              const seekSecs = parseTimestampSeconds(task.transcript_timestamp);
              const isDone = task.status === 'done';

              return (
                <div
                  key={task.id}
                  className={`p-4 rounded-xl border transition-all duration-150 space-y-3 shadow-sm ${
                    isDone
                      ? 'bg-surface/50 border-emerald-500/20 opacity-80'
                      : 'bg-surface border-line hover:border-brand/40'
                  }`}
                >
                  {/* Top: Title + Priority Tag + Delete */}
                  <div className="flex items-start justify-between gap-2.5">
                    <div className="flex items-start gap-2.5 flex-1 min-w-0">
                      {/* Checkbox Status Toggle */}
                      <button
                        onClick={() => handleStatusChange(task.id, isDone ? 'todo' : 'done')}
                        disabled={updatingTaskId === task.id}
                        className={`w-4 h-4 rounded mt-0.5 border flex items-center justify-center transition-colors cursor-pointer shrink-0 ${
                          isDone
                            ? 'bg-emerald-500 border-emerald-500 text-ink'
                            : 'border-slate-500 hover:border-brand'
                        }`}
                      >
                        {isDone && <CheckCircle2 className="w-3 h-3" />}
                      </button>

                      <span
                        className={`text-sm font-bold leading-snug ${
                          isDone ? 'line-through text-muted' : 'text-ink'
                        }`}
                      >
                        {displayText(task.title)}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <button disabled={!canManage} type="button" onClick={() => beginEdit(task)} className="p-1 text-muted hover:text-ink"
                        aria-label={`Edit task ${task.title}`}><Edit3 className="w-3.5 h-3.5" /></button>
                      {/* Priority Badge */}
                      <span
                        className={`text-sm font-mono uppercase px-2 py-0.5 rounded font-bold ${
                          task.priority === 'high'
                            ? 'bg-rose-500/20 text-rose-700 border border-rose-500/30'
                            : task.priority === 'medium'
                            ? 'bg-amber-500/20 text-amber-700 border border-amber-500/30'
                            : 'bg-blue-500/20 text-blue-700 border border-blue-500/30'
                        }`}
                      >
                        {task.priority}
                      </span>

                      {/* Delete Task */}
                      <button
                        disabled={!canManage}
                        onClick={() => onDeleteTask(task.id, task.title)}
                        title="Delete Action Item"
                        className="p-1 rounded text-muted hover:text-rose-700 hover:bg-rose-500/10 transition-colors cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Bottom: Assignee + Due Date + Source Timestamp + Status Dropdown */}
                  <div className="flex items-center justify-between pt-2 border-t border-line text-sm text-muted flex-wrap gap-2">
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3 text-muted" />
                        <span className="text-ink font-medium">
                          {task.assignee_id ? displayText(task.assignee_name) : task.assignee_name ? `Unconfirmed: ${displayText(task.assignee_name)}` : 'Unassigned'}
                        </span>
                      </span>

                      <span className="flex items-center gap-1 text-sm font-mono text-muted">
                        <Calendar className="w-3 h-3" />
                        <span>{task.due_date || 'No due date'}</span>
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Source Timestamp */}
                      {task.transcript_timestamp && seekSecs !== null && (
                        <button
                          onClick={() => onSeek(seekSecs)}
                          title="Seek audio to when this task was assigned"
                          className="text-sm font-mono text-brand hover:text-ink bg-brand/10 px-1.5 py-0.5 rounded cursor-pointer transition-colors flex items-center gap-0.5 font-semibold"
                        >
                          <Play className="w-2.5 h-2.5 fill-current" />
                          <span>@{task.transcript_timestamp.replace('@', '')}</span>
                        </button>
                      )}

                      {/* Status Dropdown */}
                      <select
                        value={task.status}
                        onChange={(e) => handleStatusChange(task.id, e.target.value as TaskStatus)}
                        className="bg-surface border border-line text-sm font-mono font-bold text-ink rounded px-1.5 py-0.5 focus:outline-none focus:border-brand cursor-pointer"
                      >
                        <option value="todo">TO DO</option>
                        <option value="doing">IN PROGRESS</option>
                        <option value="done">DONE</option>
                      </select>
                    </div>
                  </div>
                  {editingTaskId === task.id && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-line">
                      <input value={editTitle} onChange={(event) => setEditTitle(event.target.value)} aria-label="Task title"
                        className="bg-surface border border-brand/40 rounded px-2 py-1 text-sm text-ink sm:col-span-2" />
                      <select value={editAssignee} onChange={(event) => setEditAssignee(event.target.value)} aria-label="Task assignee"
                        className="bg-surface border border-line rounded px-2 py-1 text-sm text-ink">
                        <option value="">Unassigned</option>
                        {members.map((member) => <option key={member.user_id} value={member.user_id}>{member.name} · {member.email}</option>)}
                      </select>
                      <select value={editPriority} onChange={(event) => setEditPriority(event.target.value as TaskPriority)} aria-label="Task priority"
                        className="bg-surface border border-line rounded px-2 py-1 text-sm text-ink">
                        <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
                      </select>
                      <input type="date" value={editDueDate} onChange={(event) => setEditDueDate(event.target.value)} aria-label="Task due date"
                        className="bg-surface border border-line rounded px-2 py-1 text-sm text-ink" />
                      <div className="flex gap-3 justify-end">
                        <button type="button" onClick={() => setEditingTaskId(null)} aria-label="Cancel task edit"><X className="w-4 h-4 text-muted" /></button>
                        <button type="button" onClick={saveEdit} disabled={updatingTaskId === task.id || !editTitle.trim()} aria-label="Save task"><Save className="w-4 h-4 text-emerald-700" /></button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Quick Add Action Item Bar */}
      {canManage && <div className="p-5 rounded-xl bg-surface border border-line space-y-3 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-bold text-ink uppercase tracking-wider">
            <Plus className="w-4 h-4 text-brand" />
            <span>Quick Add Action Item</span>
          </div>
          <span className="text-sm text-muted font-mono">Live PostgreSQL sync</span>
        </div>

        <form onSubmit={handleCreateTask} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
          <input
            type="text"
            placeholder="Action item title..."
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            className="flex-1 bg-surface border border-line rounded-xl px-3.5 py-2 text-sm text-ink placeholder-slate-500 focus:outline-none focus:border-brand"
          />

          <select value={newAssignee} onChange={(e) => setNewAssignee(e.target.value)} aria-label="New task assignee"
            className="w-full sm:w-40 bg-surface border border-line rounded-xl px-3.5 py-2 text-sm text-ink">
            <option value="">Unassigned</option>
            {members.map((member) => <option key={member.user_id} value={member.user_id}>{member.name} · {member.email}</option>)}
          </select>

          <input type="date" value={newDueDate} onChange={(e) => setNewDueDate(e.target.value)} aria-label="New task due date"
            className="w-full sm:w-40 bg-surface border border-line rounded-xl px-3.5 py-2 text-sm text-ink" />

          <select
            value={newPriority}
            onChange={(e) => setNewPriority(e.target.value as TaskPriority)}
            className="bg-surface border border-line rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:border-brand"
          >
            <option value="low">Low Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="high">High Priority</option>
          </select>

          <button
            type="submit"
            disabled={!newTitle.trim() || isAdding}
            className="px-4 py-2 rounded-xl bg-brand hover:bg-brand disabled:opacity-40 text-on-brand text-sm font-bold flex items-center justify-center gap-1.5 cursor-pointer shadow-sm  transition-all shrink-0"
          >
            {isAdding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
            <span>Add Item</span>
          </button>
        </form>
      </div>}
    </div>
  );
};
