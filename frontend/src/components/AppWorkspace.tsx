import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  LayoutDashboard,
  FileText,
  Kanban,
  Search,
  BarChart3,
  Users,
  Plug,
  Bell,
  Settings,
  Plus,
  Upload,
  Bot,
  Sparkles,
  ArrowLeft,
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  MessageSquare,
  Send,
  User,
  Shield,
  Key,
  CreditCard,
  ExternalLink,
  Check,
  ChevronRight,
  Filter,
  Maximize2,
  Lock,
  Volume2,
  VolumeX,
  Play,
  Pause,
  Trash2,
  Edit3,
  Tag,
  Share2,

  Download,
  LogOut,
  RefreshCw,
  Loader2,
  Mic,
  Square,
  FileDown,
  Printer,
  Radio,
  FileCode,
  Video,
} from 'lucide-react';

import { useUser, useClerk, useAuth } from '@clerk/clerk-react';
import {
  TaskPriority,
  TaskStatus,
  MeetingStatus,
  ApiWorkspace,
  ApiWorkspaceMember,
  ApiMeetingListItem,
  ApiMeetingDetail,
  ApiTask,
  ApiDecision,
  ApiTranscriptSegment,
  ApiChatMessage,
  ApiNotification,
  ApiSearchResult,
} from '../types';
import {
  apiFetch,
  getAudioStreamUrl,
  useAuthMe,
  useWorkspaces,
  useWorkspaceMembers,
  useMeetings,
  useMeetingDetail,
  useMeetingSummary,
  useMeetingTranscript,
  useMeetingDecisions,
  useMeetingTasks,
  useWorkspaceTasks,
  useMeetingChat,
  useWorkspaceIntegrations,
  useNotifications,
  useSearch,
  uploadMeetingAudio,
  createWorkspaceApi,
  inviteWorkspaceMemberApi,
  updateTaskApi,
  createTaskApi,
  deleteTaskApi,
  sendChatMessageApi,
  deleteMeetingApi,
  updateMeetingApi,
  retryMeetingApi,
  deleteWorkspaceApi,
  setupDiscordWebhookApi,
  disconnectIntegrationApi,
  getGoogleAuthUrlApi,
  getZoomAuthUrlApi,
  fetchZoomRecordingsApi,
  importZoomRecordingApi,
  stopLiveMeeting,
  ZoomCloudRecording,
  setClerkUserContext,
} from '../services/api';
import { LiveMeetingModal } from './LiveMeetingModal';
import { MeetingHeader } from './workspace/MeetingHeader';
import { MeetingAtAGlance } from './workspace/MeetingAtAGlance';
import { MeetingAudioPlayer } from './workspace/MeetingAudioPlayer';
import { DiarizedTranscript } from './workspace/DiarizedTranscript';
import { ExecutiveIntelligence } from './workspace/ExecutiveIntelligence';
import { ActionItemsView } from './workspace/ActionItemsView';
import { MeetingAssistantChat } from './workspace/MeetingAssistantChat';
import { ProcessingStateCard } from './workspace/ProcessingStateCard';
import { MeetingErrorCard } from './workspace/MeetingErrorCard';
import { getMeetingSpeakerStats, formatTimeSeconds } from '../utils/speakerUtils';




interface AppWorkspaceProps {
  onBackToLanding: () => void;
}

const getAvatar = (name: string, fallback?: string | null) =>
  fallback || `https://ui-avatars.com/api/?name=${encodeURIComponent(name || 'User')}&background=8B5CF6&color=fff&bold=true`;

const formatMeetingDate = (value?: string | null) => {
  if (!value) return 'Recently';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Recently';
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(date);
};

const formatDuration = (seconds?: number | null) => {
  if (!seconds || seconds <= 0) return '< 1 min';
  const minutes = Math.max(1, Math.round(seconds / 60));
  return `${minutes} mins`;
};

const formatTimestampSeconds = (seconds: number) => {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
};

export const AppWorkspace: React.FC<AppWorkspaceProps> = ({ onBackToLanding }) => {
  const { user } = useUser();
  const { getToken } = useAuth();
  const { signOut } = useClerk();

  // Tab State
  const [activeTab, setActiveTab] = useState<
    | 'dashboard'
    | 'meeting'
    | 'kanban'
    | 'search'
    | 'analytics'
    | 'team'
    | 'integrations'
    | 'notifications'
    | 'settings'
  >('dashboard');

  // Active Workspace Selection
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setClerkUserContext({
        email: user.primaryEmailAddress?.emailAddress,
        name: user.fullName || user.firstName || user.username || undefined,
        avatar: user.imageUrl,
      });
    }
  }, [user]);

  const [showWorkspaceSwitcher, setShowWorkspaceSwitcher] = useState(false);
  const [newWorkspaceModalOpen, setNewWorkspaceModalOpen] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);

  // Delete Workspace Modal & Confirmation States
  const [deleteWorkspaceModalOpen, setDeleteWorkspaceModalOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [deletingWorkspace, setDeletingWorkspace] = useState(false);
  const [deleteWorkspaceError, setDeleteWorkspaceError] = useState<string | null>(null);


  // Selected Meeting Selection
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
  const [meetingSubTab, setMeetingSubTab] = useState<'summary' | 'transcript' | 'tasks' | 'chat'>('summary');

  // Quick Upload Form State
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgressMsg, setUploadProgressMsg] = useState('');

  // Step C1 & C3: Live Google Meet Capture & Legal Consent State
  const [liveMeetModalOpen, setLiveMeetModalOpen] = useState(false);
  const [stoppingLiveMeeting, setStoppingLiveMeeting] = useState(false);

  // Step B1: In-Browser Live Microphone Recording State
  const [recordModalOpen, setRecordModalOpen] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [liveRecordTitle, setLiveRecordTitle] = useState('');
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [recordError, setRecordError] = useState<string | null>(null);
  const [submittingRecording, setSubmittingRecording] = useState(false);
  const recordingTimerRef = useRef<number | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const mediaStreamRef = useRef<MediaStream | null>(null);


  // Quick Add Task Form State
  const [quickTaskTitle, setQuickTaskTitle] = useState('');
  const [quickTaskAssignee, setQuickTaskAssignee] = useState('');
  const [quickTaskPriority, setQuickTaskPriority] = useState<TaskPriority>('medium');
  const [quickTaskDueDate, setQuickTaskDueDate] = useState('This Week');
  const [addingTask, setAddingTask] = useState(false);

  // Invite Member Form State
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'member'>('member');
  const [inviting, setInviting] = useState(false);

  // Global Search State with Debounce
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');

  // AI Chat Input State
  const [chatInput, setChatInput] = useState('');
  const [sendingChat, setSendingChat] = useState(false);
  const [localChatMessages, setLocalChatMessages] = useState<
    Array<{ id: string; role: 'user' | 'assistant'; content: string; cited_timestamp?: string | null; time?: string }>
  >([]);

  // Interactive Audio Player State
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  const [isMuted, setIsMuted] = useState(false);

  // Notification & Feedback Toasts
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const showToast = (text: string, type: 'success' | 'error' | 'info' = 'success') => {
    setToastMessage({ type, text });
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Meeting Rename State
  const [editingMeetingTitle, setEditingMeetingTitle] = useState(false);
  const [renameMeetingInput, setRenameMeetingInput] = useState('');
  const [savingMeetingTitle, setSavingMeetingTitle] = useState(false);

  // Settings subtab

  const [settingsTab, setSettingsTab] = useState<'profile' | 'workspace' | 'theme' | 'billing'>('profile');

  // Debounce search input (300ms)
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearchQuery(searchInput.trim());
    }, 300);
    return () => clearTimeout(handler);
  }, [searchInput]);

  // SWR Data Fetching Hooks
  const { data: authSession } = useAuthMe(getToken);
  const { data: workspaces, mutate: mutateWorkspaces } = useWorkspaces(getToken);

  // Auto-select or create first workspace
  useEffect(() => {
    if (workspaces && workspaces.length > 0) {
      if (!activeWorkspaceId || !workspaces.some((w) => w.id === activeWorkspaceId)) {
        setActiveWorkspaceId(workspaces[0].id);
      }
    } else if (workspaces && workspaces.length === 0 && user) {
      // Auto-provision initial workspace for new user
      const defaultName = user.firstName ? `${user.firstName}'s Workspace` : 'My Workspace';
      createWorkspaceApi(defaultName, getToken)
        .then((created) => {
          mutateWorkspaces();
          setActiveWorkspaceId(created.id);
        })
        .catch((err) => console.error('Failed to auto-create workspace:', err));
    }
  }, [workspaces, activeWorkspaceId, user, getToken, mutateWorkspaces]);

  const activeWorkspace = useMemo(
    () => workspaces?.find((w) => w.id === activeWorkspaceId) || workspaces?.[0],
    [workspaces, activeWorkspaceId]
  );

  // Fetch workspace members, meetings, workspace tasks, and notifications
  const { data: members, mutate: mutateMembers } = useWorkspaceMembers(activeWorkspace?.id, getToken);
  const { data: meetings, mutate: mutateMeetings } = useMeetings(activeWorkspace?.id, getToken);
  const { data: workspaceTasks, mutate: mutateTasks } = useWorkspaceTasks(activeWorkspace?.id, getToken);
  const { data: integrations, mutate: mutateIntegrations } = useWorkspaceIntegrations(activeWorkspace?.id, getToken);
  const { data: notifications } = useNotifications(getToken);
  const { data: searchResults, isValidating: searchLoading } = useSearch(debouncedSearchQuery, activeWorkspace?.id, getToken);

  // Step C: Third-Party Integrations Modals & Form States
  const [discordModalOpen, setDiscordModalOpen] = useState(false);
  const [discordWebhookInput, setDiscordWebhookInput] = useState('');
  const [savingDiscord, setSavingDiscord] = useState(false);

  const [zoomPickerOpen, setZoomPickerOpen] = useState(false);
  const [zoomRecordings, setZoomRecordings] = useState<ZoomCloudRecording[]>([]);
  const [loadingZoomRecordings, setLoadingZoomRecordings] = useState(false);
  const [importingZoomId, setImportingZoomId] = useState<string | null>(null);

  // Sync selected meeting ID

  useEffect(() => {
    if (meetings && meetings.length > 0) {
      if (!selectedMeetingId || !meetings.some((m) => m.id === selectedMeetingId)) {
        setSelectedMeetingId(meetings[0].id);
      }
    } else {
      setSelectedMeetingId(null);
    }
  }, [meetings, selectedMeetingId]);

  // Active meeting detail & associated data
  const { data: meetingDetail, mutate: mutateMeetingDetail } = useMeetingDetail(selectedMeetingId, getToken);
  const isMeetingProcessing = meetingDetail?.status === 'queued' || meetingDetail?.status === 'processing';

  const { data: meetingSummary, mutate: mutateMeetingSummary } = useMeetingSummary(selectedMeetingId, isMeetingProcessing, getToken);
  const { data: meetingTranscript, mutate: mutateMeetingTranscript } = useMeetingTranscript(selectedMeetingId, isMeetingProcessing, getToken);
  const { data: meetingDecisions, mutate: mutateMeetingDecisions } = useMeetingDecisions(selectedMeetingId, isMeetingProcessing, getToken);
  const { data: meetingTasks, mutate: mutateMeetingTasks } = useMeetingTasks(selectedMeetingId, isMeetingProcessing, getToken);
  const { data: serverChatHistory, mutate: mutateChat } = useMeetingChat(selectedMeetingId, getToken);

  const speakerStats = useMemo(
    () => getMeetingSpeakerStats(meetingDetail, meetingTranscript),
    [meetingDetail, meetingTranscript]
  );

  // Merge server chat history with active session messages
  useEffect(() => {
    if (serverChatHistory) {
      setLocalChatMessages(
        serverChatHistory.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          cited_timestamp: m.cited_timestamp,
          time: m.created_at ? formatMeetingDate(m.created_at) : 'Just now',
        }))
      );
    } else {
      setLocalChatMessages([]);
    }
  }, [serverChatHistory, selectedMeetingId]);

  // Audio Player Event Listeners & Time Update
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => setCurrentTime(audio.currentTime);
    const onLoadedMetadata = () => setAudioDuration(audio.duration || 0);
    const onEnded = () => setIsPlaying(false);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
    };
  }, [selectedMeetingId]);

  // Handle Seek Audio to Timestamp
  const handleSeekToTime = (seconds: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = seconds;
      audioRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const handleToggleAudio = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch(() => {});
    }
  };

  const handleToggleMute = () => {
    if (!audioRef.current) return;
    audioRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  // Handlers for Mutations

  // 1. Create Workspace
  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkspaceName.trim() || creatingWorkspace) return;

    setCreatingWorkspace(true);
    try {
      const created = await createWorkspaceApi(newWorkspaceName.trim(), getToken);
      await mutateWorkspaces();
      setActiveWorkspaceId(created.id);
      setNewWorkspaceName('');
      setNewWorkspaceModalOpen(false);
      showToast(`Created and switched to workspace "${created.name}"`);
    } catch (err: any) {
      showToast(err.message || 'Failed to create workspace', 'error');
    } finally {
      setCreatingWorkspace(false);
    }
  };

  // 2. Invite Workspace Member
  const handleInviteMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspaceId || !inviteEmail.trim() || inviting) return;

    setInviting(true);
    try {
      const newMember = await inviteWorkspaceMemberApi(activeWorkspaceId, inviteEmail.trim(), inviteRole, getToken);
      await mutateMembers();
      setInviteEmail('');
      setInviteModalOpen(false);
      showToast(`Invited ${newMember.name || newMember.email} as ${newMember.role}`);
    } catch (err: any) {
      showToast(err.message || 'Failed to invite member. User must register first.', 'error');
    } finally {
      setInviting(false);
    }
  };

  // 3. Upload Audio Meeting
  const handleUploadMeeting = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspaceId || !uploadFile || uploading) return;

    const title = uploadTitle.trim() || uploadFile.name.replace(/\.[^/.]+$/, '');
    setUploading(true);
    setUploadProgressMsg('Uploading audio file to MeetPilot AI backend...');

    try {
      const created = await uploadMeetingAudio(activeWorkspaceId, title, uploadFile, getToken);
      setUploadProgressMsg('Audio uploaded! Ingestion pipeline queued.');
      await mutateMeetings();
      setSelectedMeetingId(created.id);
      setUploadFile(null);
      setUploadTitle('');
      setUploadModalOpen(false);
      setActiveTab('meeting');
      setMeetingSubTab('summary');
      showToast(`"${title}" uploaded. Speech transcription & analysis queued in Celery!`);
    } catch (err: any) {
      showToast(err.message || 'Audio upload failed', 'error');
    } finally {
      setUploading(false);
      setUploadProgressMsg('');
    }
  };

  // Step B1: Start Live Microphone Recording

  const startLiveRecording = async () => {
    setRecordError(null);
    audioChunksRef.current = [];
    setRecordingSeconds(0);

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Microphone recording is not supported in this browser.');
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.start(1000);
      setMediaRecorder(recorder);
      setIsRecording(true);

      recordingTimerRef.current = window.setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err: any) {
      setRecordError(err.message || 'Microphone access denied or unavailable.');
    }
  };

  // Step B1: Stop and Submit Live Recording to Existing Backend Endpoint
  const stopAndSubmitRecording = async () => {
    if (!mediaRecorder || !activeWorkspaceId) return;

    setSubmittingRecording(true);
    setRecordError(null);

    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }

    mediaRecorder.onstop = async () => {
      try {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const defaultTitle = `Live Recording - ${new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        const title = liveRecordTitle.trim() || defaultTitle;
        const audioFile = new File([audioBlob], `${title.replace(/\s+/g, '_')}.webm`, { type: 'audio/webm' });

        const created = await uploadMeetingAudio(activeWorkspaceId, title, audioFile, getToken);
        await mutateMeetings();
        setSelectedMeetingId(created.id);
        setRecordModalOpen(false);
        setIsRecording(false);
        setLiveRecordTitle('');
        setRecordingSeconds(0);
        setActiveTab('meeting');
        setMeetingSubTab('summary');
        showToast(`"${title}" recorded & queued for Gemini transcription!`);
      } catch (err: any) {
        setRecordError(err.message || 'Failed to submit audio recording.');
        showToast(err.message || 'Failed to submit audio recording', 'error');
      } finally {
        setSubmittingRecording(false);
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }
      }
    };

    mediaRecorder.stop();
  };

  const cancelLiveRecording = () => {
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    setIsRecording(false);
    setRecordModalOpen(false);
    setRecordingSeconds(0);
    setRecordError(null);
  };

  // Step C4: End / Stop Live Meeting Bot and trigger Celery pipeline
  const handleStopLiveMeeting = async (meetingId: string) => {
    setStoppingLiveMeeting(true);
    try {
      await stopLiveMeeting(meetingId, getToken);
      await mutateMeetings();
      await mutateMeetingDetail();
      showToast('Live Google Meet capture concluded! Processing summary, tasks, decisions & embeddings...');
    } catch (err: any) {
      showToast(err.message || 'Failed to stop live meeting bot', 'error');
    } finally {
      setStoppingLiveMeeting(false);
    }
  };

  // Step B2: Export Meeting to Markdown (.md)
  const handleExportMarkdown = () => {
    if (!meetingDetail) return;

    let md = `# ${meetingDetail.title}\n\n`;
    md += `- **Date**: ${formatMeetingDate(meetingDetail.created_at)}\n`;
    md += `- **Duration**: ${formatDuration(meetingDetail.duration_seconds)}\n`;
    md += `- **Status**: ${meetingDetail.status.toUpperCase()}\n\n`;

    if (meetingDetail.participants && meetingDetail.participants.length > 0) {
      md += `**Participants**: ${meetingDetail.participants.map((p) => p.name).join(', ')}\n\n`;
    }

    if (meetingSummary) {
      md += `## Executive Overview\n\n${meetingSummary.overview || 'No overview available.'}\n\n`;

      if (meetingSummary.key_takeaways && meetingSummary.key_takeaways.length > 0) {
        md += `## Key Takeaways\n\n`;
        meetingSummary.key_takeaways.forEach((k) => {
          md += `- ${k}\n`;
        });
        md += `\n`;
      }

      if (meetingSummary.next_steps && meetingSummary.next_steps.length > 0) {
        md += `## Next Steps\n\n`;
        meetingSummary.next_steps.forEach((s) => {
          md += `- ${s}\n`;
        });
        md += `\n`;
      }
    }

    if (meetingDecisions && meetingDecisions.length > 0) {
      md += `## Consensus Decisions\n\n`;
      meetingDecisions.forEach((d) => {
        md += `- **${d.topic}**: ${d.outcome} *(Timestamp: @${d.transcript_timestamp || 'N/A'})*\n`;
      });
      md += `\n`;
    }

    if (meetingTasks && meetingTasks.length > 0) {
      md += `## Action Items & Tasks\n\n`;
      md += `| Action Item | Assignee | Priority | Due Date | Status |\n`;
      md += `| :--- | :--- | :--- | :--- | :--- |\n`;
      meetingTasks.forEach((t) => {
        md += `| ${t.title} | ${t.assignee_name || 'Unassigned'} | ${t.priority.toUpperCase()} | ${t.due_date || 'This Week'} | ${t.status.toUpperCase()} |\n`;
      });
      md += `\n`;
    }

    if (meetingTranscript && meetingTranscript.length > 0) {
      md += `## Diarized Transcript\n\n`;
      meetingTranscript.forEach((seg) => {
        const time = `${Math.floor(seg.start_time / 60).toString().padStart(2, '0')}:${Math.floor(seg.start_time % 60).toString().padStart(2, '0')}`;
        md += `**[${time}] ${seg.speaker}**: ${seg.text}\n\n`;
      });
    }

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${meetingDetail.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-summary.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    showToast('Meeting summary & transcript exported to Markdown (.md)!');
  };

  // Step B2: Export Meeting to PDF
  const handleExportPDF = () => {
    if (!meetingDetail) return;
    window.print();
  };

  // Export Meeting to JSON
  const handleExportJSON = () => {
    if (!meetingDetail) return;
    const exportData = {
      meeting: {
        id: meetingDetail.id,
        title: meetingDetail.title,
        status: meetingDetail.status,
        duration_seconds: meetingDetail.duration_seconds,
        created_at: meetingDetail.created_at,
        source: meetingDetail.source,
      },
      summary: meetingSummary,
      decisions: meetingDecisions,
      tasks: meetingTasks,
      transcript: meetingTranscript,
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${meetingDetail.title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-intelligence.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    showToast('Meeting intelligence exported to JSON (.json)!');
  };

  // Modular Meeting Action Handlers
  const handleRenameMeeting = async (newTitle: string) => {
    if (!selectedMeetingId || !newTitle.trim()) return;
    try {
      await updateMeetingApi(selectedMeetingId, { title: newTitle.trim() }, getToken);
      await mutateMeetingDetail();
      await mutateMeetings();
      showToast('Meeting title updated successfully!');
    } catch (err: any) {
      showToast(err.message || 'Failed to update meeting title', 'error');
      throw err;
    }
  };

  const handleRetryMeeting = async () => {
    if (!selectedMeetingId) return;
    try {
      await retryMeetingApi(selectedMeetingId, getToken);
      await mutateMeetingDetail();
      await mutateMeetings();
      showToast('Re-queued meeting in pipeline for analysis!');
    } catch (err: any) {
      showToast(err.message || 'Failed to retry processing', 'error');
      throw err;
    }
  };

  const handleAddMeetingTask = async (title: string, assignee: string, priority: TaskPriority, dueDate: string) => {
    if (!activeWorkspaceId || !selectedMeetingId || !title.trim()) return;
    try {
      await createTaskApi(
        activeWorkspaceId,
        {
          title: title.trim(),
          meeting_id: selectedMeetingId,
          assignee_name: assignee.trim() || undefined,
          priority,
          due_date: dueDate || 'This Week',
        },
        getToken
      );
      await mutateTasks();
      await mutateMeetingTasks();
      showToast('Action item created successfully!');
    } catch (err: any) {
      showToast(err.message || 'Failed to add action item', 'error');
      throw err;
    }
  };

  const handleUpdateTaskStatus = async (taskId: string, newStatus: TaskStatus) => {
    try {
      await updateTaskApi(taskId, { status: newStatus }, getToken);
      await mutateTasks();
      if (selectedMeetingId) {
        await mutateMeetingTasks();
      }
      showToast(`Task status updated to ${newStatus.toUpperCase()}`);
    } catch (err: any) {
      showToast(err.message || 'Failed to update task status', 'error');
    }
  };

  // Step C1: Discord Webhook Handler
  const handleSaveDiscordWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspaceId || !discordWebhookInput.trim()) return;
    setSavingDiscord(true);
    try {
      await setupDiscordWebhookApi(activeWorkspaceId, discordWebhookInput.trim(), getToken);
      await mutateIntegrations();
      setDiscordModalOpen(false);
      setDiscordWebhookInput('');
      showToast('Discord Webhook connected! Meeting digests will now post automatically.');
    } catch (err: any) {
      showToast(err.message || 'Failed to save Discord Webhook', 'error');
    } finally {
      setSavingDiscord(false);
    }
  };

  // Step C: Disconnect Integration
  const handleDisconnectIntegration = async (provider: string, label: string) => {
    if (!activeWorkspaceId) return;
    if (!window.confirm(`Disconnect ${label}? Stored credentials and tokens will be permanently removed.`)) {
      return;
    }
    try {
      await disconnectIntegrationApi(activeWorkspaceId, provider, getToken);
      await mutateIntegrations();
      showToast(`${label} disconnected successfully.`);
    } catch (err: any) {
      showToast(err.message || `Failed to disconnect ${label}`, 'error');
    }
  };

  // Step C2: Google Calendar Connect
  const handleConnectGoogleCalendar = async () => {
    if (!activeWorkspaceId) return;
    try {
      const { url } = await getGoogleAuthUrlApi(activeWorkspaceId, getToken);
      window.open(url, '_blank', 'width=600,height=700');
      showToast('Opening Google Calendar authorization window...');
    } catch (err: any) {
      showToast(err.message || 'Failed to initialize Google OAuth', 'error');
    }
  };

  // Step C3: Zoom Connect
  const handleConnectZoom = async () => {
    if (!activeWorkspaceId) return;
    try {
      const { url } = await getZoomAuthUrlApi(activeWorkspaceId, getToken);
      window.open(url, '_blank', 'width=600,height=700');
      showToast('Opening Zoom authorization window...');
    } catch (err: any) {
      showToast(err.message || 'Failed to initialize Zoom OAuth', 'error');
    }
  };

  // Step C3: Open Zoom Cloud Recordings Picker
  const handleOpenZoomPicker = async () => {
    if (!activeWorkspaceId) return;
    setZoomPickerOpen(true);
    setLoadingZoomRecordings(true);
    try {
      const list = await fetchZoomRecordingsApi(activeWorkspaceId, getToken);
      setZoomRecordings(list || []);
    } catch (err: any) {
      showToast(err.message || 'Failed to fetch Zoom recordings', 'error');
    } finally {
      setLoadingZoomRecordings(false);
    }
  };

  // Step C3: Import Zoom Cloud Recording
  const handleImportZoomRecording = async (rec: ZoomCloudRecording) => {
    if (!activeWorkspaceId) return;
    setImportingZoomId(rec.id);
    try {
      const res = await importZoomRecordingApi(
        activeWorkspaceId,
        rec.topic || 'Zoom Cloud Meeting',
        rec.download_url,
        rec.file_type || 'M4A',
        getToken
      );
      await mutateMeetings();
      setSelectedMeetingId(res.id);
      setZoomPickerOpen(false);
      setActiveTab('meeting');
      setMeetingSubTab('summary');
      showToast(`Zoom recording "${rec.topic}" queued for Gemini transcription!`);
    } catch (err: any) {
      showToast(err.message || 'Failed to import Zoom recording', 'error');
    } finally {
      setImportingZoomId(null);
    }
  };

  // 4. Delete Meeting


  const handleDeleteMeeting = async (meetingId: string, title: string) => {
    if (!window.confirm(`Are you sure you want to delete "${title}"? This cannot be undone.`)) {
      return;
    }
    try {
      await deleteMeetingApi(meetingId, getToken);
      await mutateMeetings();
      showToast(`Deleted meeting "${title}"`);
      if (selectedMeetingId === meetingId) {
        setSelectedMeetingId(null);
      }
    } catch (err: any) {
      showToast(err.message || 'Failed to delete meeting', 'error');
    }
  };

  // Handle Rename Meeting
  const handleUpdateMeetingTitle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMeetingId || !renameMeetingInput.trim()) return;
    setSavingMeetingTitle(true);
    try {
      await updateMeetingApi(selectedMeetingId, { title: renameMeetingInput.trim() }, getToken);
      await mutateMeetingDetail();
      await mutateMeetings();
      setEditingMeetingTitle(false);
      showToast('Meeting title updated successfully!');
    } catch (err: any) {
      showToast(err.message || 'Failed to update meeting title', 'error');
    } finally {
      setSavingMeetingTitle(false);
    }
  };

  // Handle Delete Task
  const handleDeleteTask = async (taskId: string, title: string) => {
    if (!window.confirm(`Delete task "${title}"?`)) return;
    try {
      await deleteTaskApi(taskId, getToken);
      await mutateTasks();
      showToast(`Deleted task "${title}"`);
    } catch (err: any) {
      showToast(err.message || 'Failed to delete task', 'error');
    }
  };

  // 5. Delete Workspace with Human Confirmation Step
  const handleDeleteWorkspace = async (e: React.FormEvent) => {

    e.preventDefault();
    if (!activeWorkspace) return;

    if (deleteConfirmText.trim().toLowerCase() !== activeWorkspace.name.trim().toLowerCase()) {
      setDeleteWorkspaceError(`Please type "${activeWorkspace.name}" exactly to confirm.`);
      return;
    }

    setDeletingWorkspace(true);
    setDeleteWorkspaceError(null);

    try {
      await deleteWorkspaceApi(activeWorkspace.id, getToken);
      setDeleteWorkspaceModalOpen(false);
      setDeleteConfirmText('');
      showToast(`Deleted workspace "${activeWorkspace.name}"`);
      await mutateWorkspaces();

      const remaining = workspaces?.filter((w) => w.id !== activeWorkspace.id) || [];
      if (remaining.length > 0) {
        setActiveWorkspaceId(remaining[0].id);
      } else {
        setActiveWorkspaceId(null);
      }
    } catch (err: any) {
      setDeleteWorkspaceError(err.message || 'Failed to delete workspace.');
      showToast(err.message || 'Failed to delete workspace', 'error');
    } finally {
      setDeletingWorkspace(false);
    }
  };


  // 5. Kanban Task Status Update with Optimistic UI and Rollback
  const handleTaskStatusChange = async (task: ApiTask, newStatus: TaskStatus) => {
    const originalStatus = task.status;
    if (originalStatus === newStatus) return;

    // Optimistic cache update
    mutateTasks(
      (current) =>
        current?.map((t) => (t.id === task.id ? { ...t, status: newStatus } : t)),
      false
    );

    try {
      await updateTaskApi(task.id, { status: newStatus }, getToken);
      await mutateTasks();
      showToast(`Moved task to ${newStatus.toUpperCase()}`);
    } catch (err: any) {
      // Rollback on network failure
      mutateTasks(
        (current) =>
          current?.map((t) => (t.id === task.id ? { ...t, status: originalStatus } : t)),
        false
      );
      showToast('Network error updating task status. Rolled back.', 'error');
    }
  };

  // 6. Quick Add Task with Optimistic UI
  const handleQuickAddTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspaceId || !quickTaskTitle.trim() || addingTask) return;

    const title = quickTaskTitle.trim();
    setAddingTask(true);

    const tempId = `temp-${Date.now()}`;
    const optimisticTask: ApiTask = {
      id: tempId,
      meeting_id: selectedMeetingId || '',
      title,
      assignee_name: quickTaskAssignee || user?.fullName || 'Unassigned',
      due_date: quickTaskDueDate || 'This Week',
      priority: quickTaskPriority,
      status: 'todo',
    };

    // Optimistically prepend to board
    mutateTasks((current) => [optimisticTask, ...(current || [])], false);
    setQuickTaskTitle('');

    try {
      const created = await createTaskApi(
        {
          title,
          workspace_id: activeWorkspaceId,
          meeting_id: selectedMeetingId || undefined,
          assignee_name: quickTaskAssignee || user?.fullName || undefined,
          due_date: quickTaskDueDate,
          priority: quickTaskPriority,
          status: 'todo',
        },
        getToken
      );
      await mutateTasks();
      showToast(`Action item assigned to ${created.assignee_name || 'workspace'}`);
    } catch (err: any) {
      // Rollback
      mutateTasks((current) => current?.filter((t) => t.id !== tempId), false);
      showToast(err.message || 'Failed to create task. Rolled back.', 'error');
    } finally {
      setAddingTask(false);
    }
  };

  // 7. Send Grounded AI Chat Message
  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMeetingId || !chatInput.trim() || sendingChat) return;

    const question = chatInput.trim();
    const tempUserMsg = {
      id: `chat-${Date.now()}`,
      role: 'user' as const,
      content: question,
      time: 'Just now',
    };

    setLocalChatMessages((prev) => [...prev, tempUserMsg]);
    setChatInput('');
    setSendingChat(true);

    try {
      const response = await sendChatMessageApi(selectedMeetingId, question, getToken);
      setLocalChatMessages((prev) => [
        ...prev,
        {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: response.answer,
          cited_timestamp: response.cited_timestamp,
          time: 'Just now',
        },
      ]);
      await mutateChat();
    } catch (err: any) {
      setLocalChatMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `Error: ${err.message || 'Failed to query meeting memory.'}`,
          time: 'Just now',
        },
      ]);
    } finally {
      setSendingChat(false);
    }
  };

  const handleSendChatDirect = async (question: string) => {
    if (!selectedMeetingId || !question.trim() || sendingChat) return;

    const tempUserMsg = {
      id: `chat-${Date.now()}`,
      role: 'user' as const,
      content: question.trim(),
      time: 'Just now',
    };

    setLocalChatMessages((prev) => [...prev, tempUserMsg]);
    setSendingChat(true);

    try {
      const response = await sendChatMessageApi(selectedMeetingId, question.trim(), getToken);
      setLocalChatMessages((prev) => [
        ...prev,
        {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: response.answer,
          cited_timestamp: response.cited_timestamp,
          time: 'Just now',
        },
      ]);
      await mutateChat();
    } catch (err: any) {
      setLocalChatMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: `Error: ${err.message || 'Failed to query meeting memory.'}`,
          time: 'Just now',
        },
      ]);
    } finally {
      setSendingChat(false);
    }
  };

  // Computed Real Analytics
  const totalMeetingsCount = meetings?.length || 0;
  const completedMeetingsCount = meetings?.filter((m) => m.status === 'completed').length || 0;
  const totalSpeakingSeconds = meetings?.reduce((acc, m) => acc + (m.duration_seconds || 0), 0) || 0;
  const totalSpeakingHours = (totalSpeakingSeconds / 3600).toFixed(1);

  const pendingTasksList = useMemo(() => {
    return workspaceTasks?.filter((t) => t.status !== 'done') || [];
  }, [workspaceTasks]);

  const tasksByStatus = useMemo(() => {
    return {
      todo: workspaceTasks?.filter((t) => t.status === 'todo') || [],
      doing: workspaceTasks?.filter((t) => t.status === 'doing') || [],
      done: workspaceTasks?.filter((t) => t.status === 'done') || [],
    };
  }, [workspaceTasks]);

  // Speaking time breakdown by speaker from current meeting transcript for Analytics
  const analyticsSpeakerStats = useMemo(() => {
    if (!meetingTranscript || meetingTranscript.length === 0) return [];
    const speakerMap: Record<string, number> = {};
    let totalSecs = 0;
    meetingTranscript.forEach((seg) => {
      const dur = Math.max(1, seg.end_time - seg.start_time);
      speakerMap[seg.speaker] = (speakerMap[seg.speaker] || 0) + dur;
      totalSecs += dur;
    });
    return Object.entries(speakerMap).map(([speaker, dur]) => ({
      speaker,
      seconds: dur,
      percentage: totalSecs > 0 ? Math.round((dur / totalSecs) * 100) : 0,
      hours: (dur / 3600).toFixed(1),
    }));
  }, [meetingTranscript]);

  return (
    <div className="min-h-screen bg-[#09090B] text-slate-100 flex flex-col font-sans selection:bg-[#8B5CF6]/30 selection:text-white antialiased">
      {/* Top Header Bar */}
      <header className="h-16 border-b border-[#27272A] bg-[#111113] px-4 sm:px-6 flex items-center justify-between sticky top-0 z-40">
        {/* Left Brand & Workspace Switcher */}
        <div className="flex items-center gap-3 sm:gap-4">
          <button
            onClick={onBackToLanding}
            className="group relative flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-tr from-[#8B5CF6] to-[#A78BFA] p-[1px] shadow-lg shadow-[#8B5CF6]/20 hover:shadow-[#8B5CF6]/40 transition-all duration-300 cursor-pointer active:scale-95"
            title="Return to Home / Landing Page"
          >
            <div className="w-full h-full bg-[#111113] rounded-[11px] flex items-center justify-center group-hover:bg-[#181822] transition-colors">
              <Bot className="w-5 h-5 text-[#8B5CF6] group-hover:scale-110 transition-transform duration-300" />
            </div>
            <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-400 rounded-full border-2 border-[#09090B] animate-pulse" />
          </button>

          <div className="h-4 w-px bg-gradient-to-b from-transparent via-[#3F3F50] to-transparent hidden sm:block mx-0.5" />

          {/* Workspace Switcher */}
          <div className="relative">
            <button
              onClick={() => setShowWorkspaceSwitcher(!showWorkspaceSwitcher)}
              className="group flex items-center gap-2 px-3.5 py-1.5 rounded-xl border border-[#2D2D3B] hover:border-[#8B5CF6]/60 bg-gradient-to-r from-[#181822] to-[#1E1E2A] hover:from-[#20202E] hover:to-[#262638] text-white text-xs font-bold transition-all duration-200 cursor-pointer shadow-sm active:scale-[0.98]"
            >
              <span className="max-w-[140px] sm:max-w-[200px] truncate tracking-tight text-white font-bold">
                {activeWorkspace?.name || 'Loading Workspace...'}
              </span>
              <ChevronRight
                className={`w-3.5 h-3.5 text-slate-400 group-hover:text-slate-200 transition-transform duration-200 ${
                  showWorkspaceSwitcher ? 'rotate-90 text-[#8B5CF6]' : ''
                }`}
              />
            </button>

            {/* Workspace Dropdown Popover */}
            {showWorkspaceSwitcher && (
              <div className="absolute left-0 mt-2 w-72 rounded-2xl bg-[#121217]/95 backdrop-blur-xl border border-[#2D2D3B] p-2.5 shadow-2xl shadow-black/80 z-50 space-y-1 animate-fadeIn">
                <div className="flex items-center justify-between px-3 py-1.5 border-b border-[#27272A] text-[10px] font-mono uppercase text-slate-400">
                  <span>Your Workspaces</span>
                  <span>{workspaces?.length || 0}</span>
                </div>

                <div className="max-h-48 overflow-y-auto space-y-1 py-1">
                  {workspaces?.map((ws) => (
                    <button
                      key={ws.id}
                      onClick={() => {
                        setActiveWorkspaceId(ws.id);
                        setShowWorkspaceSwitcher(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-xl text-xs flex items-center justify-between transition-colors cursor-pointer ${
                        ws.id === activeWorkspaceId
                          ? 'bg-[#8B5CF6] text-white font-bold'
                          : 'text-slate-300 hover:bg-[#18181b] hover:text-white'
                      }`}
                    >
                      <span className="truncate">{ws.name}</span>
                      {ws.id === activeWorkspaceId && <Check className="w-3.5 h-3.5" />}
                    </button>
                  ))}
                </div>

                <div className="pt-2 border-t border-[#27272A] space-y-1">
                  <button
                    onClick={() => {
                      setShowWorkspaceSwitcher(false);
                      setNewWorkspaceModalOpen(true);
                    }}
                    className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-[#18181b] hover:bg-[#27272A] text-xs font-bold text-[#8B5CF6] transition-colors cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Create Workspace</span>
                  </button>

                  {activeWorkspace && (
                    <button
                      onClick={() => {
                        setShowWorkspaceSwitcher(false);
                        setDeleteConfirmText('');
                        setDeleteWorkspaceError(null);
                        setDeleteWorkspaceModalOpen(true);
                      }}
                      className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-bold text-red-400 hover:text-red-300 hover:bg-red-950/20 transition-colors cursor-pointer"
                    >
                      <Trash2 className="w-3 h-3" />
                      <span>Delete Active Workspace</span>
                    </button>
                  )}
                </div>
              </div>
            )}

          </div>
        </div>

        {/* Right Header Navigation & Actions */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Step C1: Join Live Google Meet Button */}
          <button
            onClick={() => setLiveMeetModalOpen(true)}
            className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-lg shadow-emerald-500/20 transition-all active:scale-95 border border-emerald-400/30"
          >
            <Video className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Join Google Meet</span>
            <span className="inline-flex items-center px-1.5 py-0.2 text-[9px] font-bold uppercase tracking-wider bg-emerald-950/80 border border-emerald-400/40 rounded-md text-emerald-300">
              Live
            </span>
          </button>

          {/* Live Mic Recording Button */}
          <button
            onClick={() => {
              setRecordError(null);
              setRecordModalOpen(true);
            }}
            className="px-3.5 py-1.5 rounded-xl bg-[#18181b] hover:bg-rose-950/30 border border-rose-500/30 hover:border-rose-500/60 text-rose-300 text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-sm transition-all active:scale-95"
          >
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
            <Mic className="w-3.5 h-3.5 text-rose-400" />
            <span className="hidden sm:inline">Record Mic</span>
          </button>

          {/* Quick Upload Button */}
          <button
            onClick={() => setUploadModalOpen(true)}
            className="px-3.5 py-1.5 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-lg shadow-[#8B5CF6]/20 transition-all active:scale-95"
          >
            <Upload className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Upload Audio</span>
          </button>


          {/* User Profile Badge */}
          <div className="flex items-center gap-2 pl-2 border-l border-[#27272A]">
            <img
              src={getAvatar(user?.fullName || user?.firstName || 'User', user?.imageUrl)}
              alt="User"
              className="w-8 h-8 rounded-full object-cover ring-2 ring-[#8B5CF6]/30"
            />
            <div className="hidden md:block text-left">
              <div className="text-xs font-bold text-white leading-none">{user?.fullName || user?.firstName || 'User'}</div>
              <div className="text-[10px] text-slate-400 font-mono mt-0.5 truncate max-w-[120px]">
                {user?.primaryEmailAddress?.emailAddress}
              </div>
            </div>

            <button
              onClick={() => signOut()}
              title="Sign Out"
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors ml-1"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar Navigation */}
        <aside className="w-16 sm:w-56 border-r border-[#27272A] bg-[#111113] p-3 flex flex-col justify-between shrink-0">
          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
                activeTab === 'dashboard'
                  ? 'bg-[#8B5CF6] text-white shadow-md shadow-[#8B5CF6]/20'
                  : 'text-slate-400 hover:text-white hover:bg-[#18181b]'
              }`}
            >
              <LayoutDashboard className="w-4 h-4 shrink-0" />
              <span className="hidden sm:inline">Dashboard</span>
            </button>

            <button
              onClick={() => setActiveTab('meeting')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
                activeTab === 'meeting'
                  ? 'bg-[#8B5CF6] text-white shadow-md shadow-[#8B5CF6]/20'
                  : 'text-slate-400 hover:text-white hover:bg-[#18181b]'
              }`}
            >
              <FileText className="w-4 h-4 shrink-0" />
              <span className="hidden sm:inline">Meeting Detail</span>
            </button>

            <button
              onClick={() => setActiveTab('kanban')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
                activeTab === 'kanban'
                  ? 'bg-[#8B5CF6] text-white shadow-md shadow-[#8B5CF6]/20'
                  : 'text-slate-400 hover:text-white hover:bg-[#18181b]'
              }`}
            >
              <Kanban className="w-4 h-4 shrink-0" />
              <span className="hidden sm:inline">Action Items</span>
            </button>

            <button
              onClick={() => setActiveTab('search')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
                activeTab === 'search'
                  ? 'bg-[#8B5CF6] text-white shadow-md shadow-[#8B5CF6]/20'
                  : 'text-slate-400 hover:text-white hover:bg-[#18181b]'
              }`}
            >
              <Search className="w-4 h-4 shrink-0" />
              <span className="hidden sm:inline">Global Search</span>
            </button>

            <button
              onClick={() => setActiveTab('analytics')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
                activeTab === 'analytics'
                  ? 'bg-[#8B5CF6] text-white shadow-md shadow-[#8B5CF6]/20'
                  : 'text-slate-400 hover:text-white hover:bg-[#18181b]'
              }`}
            >
              <BarChart3 className="w-4 h-4 shrink-0" />
              <span className="hidden sm:inline">Analytics</span>
            </button>

            <div className="pt-4 pb-1 text-[10px] font-mono uppercase text-slate-500 px-3 hidden sm:block">Team & Tools</div>

            <button
              onClick={() => setActiveTab('team')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
                activeTab === 'team'
                  ? 'bg-[#8B5CF6] text-white shadow-md shadow-[#8B5CF6]/20'
                  : 'text-slate-400 hover:text-white hover:bg-[#18181b]'
              }`}
            >
              <Users className="w-4 h-4 shrink-0" />
              <span className="hidden sm:inline">Team Members</span>
            </button>

            <button
              onClick={() => setActiveTab('integrations')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
                activeTab === 'integrations'
                  ? 'bg-[#8B5CF6] text-white shadow-md shadow-[#8B5CF6]/20'
                  : 'text-slate-400 hover:text-white hover:bg-[#18181b]'
              }`}
            >
              <Plug className="w-4 h-4 shrink-0" />
              <span className="hidden sm:inline">Integrations</span>
            </button>

            <button
              onClick={() => setActiveTab('notifications')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
                activeTab === 'notifications'
                  ? 'bg-[#8B5CF6] text-white shadow-md shadow-[#8B5CF6]/20'
                  : 'text-slate-400 hover:text-white hover:bg-[#18181b]'
              }`}
            >
              <Bell className="w-4 h-4 shrink-0" />
              <span className="hidden sm:inline">Notifications</span>
              {notifications && notifications.length > 0 && (
                <span className="hidden sm:inline-block ml-auto px-1.5 py-0.2 bg-[#8B5CF6] text-white rounded-full text-[10px] font-bold font-mono">
                  {notifications.length}
                </span>
              )}
            </button>
          </nav>

          <div className="pt-4 border-t border-[#27272A]">
            <button
              onClick={() => setActiveTab('settings')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
                activeTab === 'settings'
                  ? 'bg-[#8B5CF6] text-white shadow-md shadow-[#8B5CF6]/20'
                  : 'text-slate-400 hover:text-white hover:bg-[#18181b]'
              }`}
            >
              <Settings className="w-4 h-4 shrink-0" />
              <span className="hidden sm:inline">Settings</span>
            </button>
          </div>
        </aside>

        {/* Central Workspace Canvas */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6 bg-[#09090B]">
          {/* TAB 1: DASHBOARD OVERVIEW */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6 animate-fadeIn">
              {/* Dashboard Banner */}
              <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <img
                    src={getAvatar(user?.fullName || user?.firstName || 'User', user?.imageUrl)}
                    alt="User"
                    className="w-12 h-12 rounded-2xl object-cover ring-2 ring-[#8B5CF6]/40"
                  />
                  <div>
                    <h2 className="text-2xl font-extrabold text-white">
                      Welcome back, {user?.firstName || 'Pilot'} 👋
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">
                      {activeWorkspace?.name} · {completedMeetingsCount} completed meetings · {pendingTasksList.length} pending action items.
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => setUploadModalOpen(true)}
                  className="px-4 py-2 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] text-white font-bold text-xs flex items-center gap-2 cursor-pointer shadow-lg shadow-[#8B5CF6]/20"
                >
                  <Upload className="w-4 h-4" />
                  <span>Upload Meeting Audio</span>
                </button>
              </div>

              {/* Stats Overview Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-[#111113] border border-[#27272A] space-y-1">
                  <div className="text-[11px] font-mono uppercase text-slate-500">Total Meetings</div>
                  <div className="text-2xl font-extrabold text-white">{totalMeetingsCount}</div>
                  <div className="text-[10px] text-emerald-400 font-semibold">{completedMeetingsCount} processed live</div>
                </div>

                <div className="p-4 rounded-xl bg-[#111113] border border-[#27272A] space-y-1">
                  <div className="text-[11px] font-mono uppercase text-slate-500">Pending Tasks</div>
                  <div className="text-2xl font-extrabold text-white">{pendingTasksList.length}</div>
                  <div className="text-[10px] text-[#8B5CF6] font-semibold">
                    {tasksByStatus.doing.length} currently in progress
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[#111113] border border-[#27272A] space-y-1">
                  <div className="text-[11px] font-mono uppercase text-slate-500">Speaking Time</div>
                  <div className="text-2xl font-extrabold text-white">{totalSpeakingHours} hrs</div>
                  <div className="text-[10px] text-slate-400 font-semibold">
                    Across {members?.length || 1} team members
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-[#111113] border border-[#27272A] space-y-1">
                  <div className="text-[11px] font-mono uppercase text-slate-500">Completed Tasks</div>
                  <div className="text-2xl font-extrabold text-white">{tasksByStatus.done.length}</div>
                  <div className="text-[10px] text-emerald-400 font-semibold">100% indexed in memory</div>
                </div>
              </div>

              {/* Recent Meetings & Pending Tasks Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Recent Meetings (7 cols) */}
                <div className="lg:col-span-7 p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider">Recent Meetings</h3>
                    <span className="text-xs text-slate-500 font-mono">{totalMeetingsCount} Total</span>
                  </div>

                  {(!meetings || meetings.length === 0) ? (
                    <div className="p-8 text-center border border-dashed border-[#27272A] rounded-xl space-y-3">
                      <FileText className="w-8 h-8 text-slate-500 mx-auto" />
                      <p className="text-xs text-slate-400">No meetings recorded in this workspace yet.</p>
                      <button
                        onClick={() => setUploadModalOpen(true)}
                        className="px-3 py-1.5 rounded-lg bg-[#8B5CF6] text-white text-xs font-bold"
                      >
                        Upload Audio
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {meetings.slice(0, 5).map((m) => (
                        <div
                          key={m.id}
                          onClick={() => {
                            setSelectedMeetingId(m.id);
                            setActiveTab('meeting');
                          }}
                          className={`p-4 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${
                            selectedMeetingId === m.id
                              ? 'bg-[#18181b] border-[#8B5CF6]'
                              : 'bg-[#18181b] border-[#27272A] hover:border-[#8B5CF6]/50'
                          }`}
                        >
                          <div className="space-y-1">
                            <div className="text-sm font-bold text-white flex items-center gap-2">
                              <span>{m.title}</span>
                              <span
                                className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                                  m.status === 'completed'
                                    ? 'bg-emerald-500/20 text-emerald-300'
                                    : m.status === 'processing'
                                    ? 'bg-[#8B5CF6]/20 text-[#8B5CF6] animate-pulse'
                                    : m.status === 'queued'
                                    ? 'bg-amber-500/20 text-amber-300'
                                    : 'bg-rose-500/20 text-rose-300'
                                }`}
                              >
                                {m.status}
                              </span>
                            </div>
                            <div className="text-xs text-slate-400 flex items-center gap-3">
                              <span>{formatMeetingDate(m.created_at)}</span>
                              <span>•</span>
                              <span>{formatDuration(m.duration_seconds)}</span>
                              <span>•</span>
                              <span>{m.participants.length || 1} participants</span>
                            </div>
                          </div>

                          <div className="flex items-center gap-3">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteMeeting(m.id, m.title);
                              }}
                              title={`Delete ${m.title}`}
                              className="p-2 rounded-xl text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                            <ChevronRight className="w-4 h-4 text-slate-500" />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>


                {/* Pending Tasks & Upcoming Deadlines (5 cols) */}
                <div className="lg:col-span-5 p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider">Pending Action Items</h3>
                    <button onClick={() => setActiveTab('kanban')} className="text-xs text-[#8B5CF6] hover:underline">
                      View Board
                    </button>
                  </div>

                  {pendingTasksList.length === 0 ? (
                    <div className="p-8 text-center border border-dashed border-[#27272A] rounded-xl space-y-2">
                      <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                      <p className="text-xs text-slate-400">All tasks completed! Upload audio to extract new items.</p>
                    </div>
                  ) : (
                    <div className="space-y-2.5">
                      {pendingTasksList.slice(0, 5).map((t) => (
                        <div key={t.id} className="p-3 rounded-xl bg-[#18181b] border border-[#27272A] space-y-2">
                          <div className="flex items-start justify-between gap-2">
                            <span className="text-xs font-semibold text-white leading-snug">{t.title}</span>
                            <span
                              className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded font-bold ${
                                t.priority === 'high'
                                  ? 'bg-rose-500/20 text-rose-300'
                                  : t.priority === 'medium'
                                  ? 'bg-amber-500/20 text-amber-300'
                                  : 'bg-blue-500/20 text-blue-300'
                              }`}
                            >
                              {t.priority}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-[11px] text-slate-400">
                            <span>Assignee: {t.assignee_name || 'Team Member'}</span>
                            <span className="font-mono text-slate-500">Due: {t.due_date || 'This Week'}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: MEETING INTELLIGENCE DETAIL */}
          {activeTab === 'meeting' && (
            <div className="space-y-6 animate-fadeIn">
              {/* Empty state if no meetings exist */}
              {(!meetings || meetings.length === 0) && (
                <div className="p-12 rounded-2xl bg-[#111113] border border-dashed border-[#27272A] text-center space-y-4 shadow-xl">
                  <FileText className="w-12 h-12 text-[#8B5CF6] mx-auto animate-bounce" />
                  <h3 className="text-lg font-bold text-white">No Meetings in this Workspace</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Upload an MP3, WAV, or M4A recording or join a live Google Meet to trigger speech diarization, automated summarization, and action item detection.
                  </p>
                  <div className="flex items-center justify-center gap-3">
                    <button
                      onClick={() => setLiveMeetModalOpen(true)}
                      className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-lg shadow-emerald-500/20 inline-flex items-center gap-2 cursor-pointer"
                    >
                      <Video className="w-4 h-4" />
                      <span>Join Live Google Meet</span>
                    </button>
                    <button
                      onClick={() => setUploadModalOpen(true)}
                      className="px-5 py-2.5 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] text-white text-xs font-bold shadow-lg shadow-[#8B5CF6]/20 inline-flex items-center gap-2 cursor-pointer"
                    >
                      <Upload className="w-4 h-4" />
                      <span>Upload Audio</span>
                    </button>
                  </div>
                </div>
              )}

              {meetingDetail && (
                <>
                  {/* Meeting Header */}
                  <MeetingHeader
                    meeting={meetingDetail}
                    allMeetings={meetings || []}
                    speakerStats={speakerStats}
                    onSelectMeeting={(id) => setSelectedMeetingId(id)}
                    onRenameMeeting={handleRenameMeeting}
                    onDeleteMeeting={handleDeleteMeeting}
                    onExportMarkdown={handleExportMarkdown}
                    onExportJSON={handleExportJSON}
                    onExportPDF={handleExportPDF}
                  />

                  {/* Meeting At A Glance Strip */}
                  {meetingDetail.status === 'completed' && (
                    <MeetingAtAGlance
                      durationSeconds={meetingDetail.duration_seconds}
                      speakerStats={speakerStats}
                      decisionsCount={meetingDecisions?.length || 0}
                      tasksCount={meetingTasks?.length || 0}
                      completedTasksCount={meetingTasks?.filter((t) => t.status === 'done').length || 0}
                    />
                  )}

                  {/* Live Active Meeting View */}
                  {meetingDetail.status === 'in_progress' && (
                    <div className="p-6 rounded-2xl bg-[#111113] border border-rose-500/40 space-y-6 shadow-2xl shadow-rose-950/20">
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl bg-gradient-to-r from-rose-950/40 via-[#18181b] to-slate-900 border border-rose-500/30">
                        <div className="flex items-center gap-3">
                          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400">
                            <Radio className="w-5 h-5 animate-pulse" />
                            <span className="absolute -top-1 -right-1 w-3 h-3 bg-rose-500 rounded-full border-2 border-[#111113] animate-ping" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="text-base font-bold text-white">Live Google Meet Capture Active</h3>
                              <span className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider text-rose-300 bg-rose-950/80 border border-rose-500/40 rounded-md animate-pulse">
                                Live Ingestion
                              </span>
                            </div>
                            <p className="text-xs text-slate-400 mt-0.5">
                              Bot is connected to Google Meet ({meetingDetail.native_meeting_id || 'call'}). Real-time speech turns stream directly into memory.
                            </p>
                          </div>
                        </div>

                        <button
                          onClick={() => handleStopLiveMeeting(meetingDetail.id)}
                          disabled={stoppingLiveMeeting}
                          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-rose-600 via-rose-500 to-pink-600 hover:from-rose-500 hover:to-pink-500 text-white text-xs font-bold shadow-lg shadow-rose-500/25 flex items-center gap-2 cursor-pointer transition-all active:scale-95 shrink-0"
                        >
                          {stoppingLiveMeeting ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              <span>Stopping & Triggering AI...</span>
                            </>
                          ) : (
                            <>
                              <Square className="w-4 h-4 fill-current" />
                              <span>Leave / Process Meeting</span>
                            </>
                          )}
                        </button>
                      </div>

                      {/* Live Diarized Turns Feed */}
                      <DiarizedTranscript
                        segments={meetingTranscript || []}
                        speakerStats={speakerStats}
                        currentTime={currentTime}
                        onSeek={handleSeekToTime}
                        isLongRecording={false}
                      />
                    </div>
                  )}

                  {/* Queued / Processing State Card */}
                  {(meetingDetail.status === 'queued' || meetingDetail.status === 'processing') && (
                    <ProcessingStateCard
                      status={meetingDetail.status}
                      meetingTitle={meetingDetail.title}
                    />
                  )}

                  {/* Failed Meeting Error Card */}
                  {meetingDetail.status === 'failed' && (
                    <MeetingErrorCard
                      meetingId={meetingDetail.id}
                      meetingTitle={meetingDetail.title}
                      failureReason={meetingDetail.failure_reason}
                      onRetry={handleRetryMeeting}
                      onOpenUpload={() => setUploadModalOpen(true)}
                      onDelete={() => handleDeleteMeeting(meetingDetail.id, meetingDetail.title)}
                    />
                  )}

                  {/* Completed Meeting Intelligence Hub */}
                  {meetingDetail.status === 'completed' && (
                    <div className="space-y-6">
                      {/* Interactive Audio Player */}
                      {selectedMeetingId && meetingDetail.audio_url && (
                        <MeetingAudioPlayer
                          audioUrl={getAudioStreamUrl(selectedMeetingId)}
                          fallbackDuration={meetingDetail.duration_seconds}
                          currentTime={currentTime}
                          onTimeUpdate={(t) => setCurrentTime(t)}
                          onSeek={handleSeekToTime}
                          audioRef={audioRef}
                        />
                      )}

                      {/* Sub-Tab Navigation Strip */}
                      <div className="flex items-center gap-2 p-1.5 rounded-2xl bg-[#111113] border border-[#27272A] overflow-x-auto">
                        <button
                          onClick={() => setMeetingSubTab('summary')}
                          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
                            meetingSubTab === 'summary'
                              ? 'bg-[#8B5CF6] text-white shadow-lg shadow-[#8B5CF6]/25'
                              : 'text-slate-400 hover:text-white hover:bg-[#18181b]'
                          }`}
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>Executive Summary & Decisions</span>
                        </button>

                        <button
                          onClick={() => setMeetingSubTab('transcript')}
                          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
                            meetingSubTab === 'transcript'
                              ? 'bg-[#8B5CF6] text-white shadow-lg shadow-[#8B5CF6]/25'
                              : 'text-slate-400 hover:text-white hover:bg-[#18181b]'
                          }`}
                        >
                          <FileText className="w-3.5 h-3.5" />
                          <span>Diarized Transcript ({meetingTranscript?.length || 0})</span>
                        </button>

                        <button
                          onClick={() => setMeetingSubTab('tasks')}
                          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
                            meetingSubTab === 'tasks'
                              ? 'bg-[#8B5CF6] text-white shadow-lg shadow-[#8B5CF6]/25'
                              : 'text-slate-400 hover:text-white hover:bg-[#18181b]'
                          }`}
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Action Items ({meetingTasks?.length || 0})</span>
                        </button>

                        <button
                          onClick={() => setMeetingSubTab('chat')}
                          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
                            meetingSubTab === 'chat'
                              ? 'bg-[#8B5CF6] text-white shadow-lg shadow-[#8B5CF6]/25'
                              : 'text-slate-400 hover:text-white hover:bg-[#18181b]'
                          }`}
                        >
                          <Bot className="w-3.5 h-3.5 text-indigo-300" />
                          <span>AI Assistant Chat</span>
                        </button>
                      </div>

                      {/* Sub-Tab 1: Executive Intelligence & Decisions */}
                      {meetingSubTab === 'summary' && (
                        <ExecutiveIntelligence
                          summary={meetingSummary}
                          decisions={meetingDecisions || []}
                          onSeek={handleSeekToTime}
                        />
                      )}

                      {/* Sub-Tab 2: Diarized Synchronized Transcript */}
                      {meetingSubTab === 'transcript' && (
                        <DiarizedTranscript
                          segments={meetingTranscript || []}
                          speakerStats={speakerStats}
                          currentTime={currentTime}
                          onSeek={handleSeekToTime}
                          isLongRecording={Boolean(meetingDetail.duration_seconds && meetingDetail.duration_seconds > 900)}
                        />
                      )}

                      {/* Sub-Tab 3: Action Items */}
                      {meetingSubTab === 'tasks' && (
                        <ActionItemsView
                          tasks={meetingTasks || []}
                          onUpdateTaskStatus={handleUpdateTaskStatus}
                          onDeleteTask={handleDeleteTask}
                          onAddTask={handleAddMeetingTask}
                          onSeek={handleSeekToTime}
                          onOpenKanban={() => setActiveTab('kanban')}
                        />
                      )}

                      {/* Sub-Tab 4: AI Assistant Chat */}
                      {meetingSubTab === 'chat' && (
                        <MeetingAssistantChat
                          meetingTitle={meetingDetail.title}
                          messages={localChatMessages}
                          isSending={sendingChat}
                          onSendMessage={handleSendChatDirect}
                          onSeek={handleSeekToTime}
                        />
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* TAB 3: KANBAN BOARD */}
          {activeTab === 'kanban' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-extrabold text-white">Action Items Kanban Board</h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Tasks aggregated across workspace meetings with live status updates.
                  </p>
                </div>
              </div>

              {/* 3 Kanban Columns */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Column 1: TODO */}
                <div className="p-4 rounded-2xl bg-[#111113] border border-[#27272A] space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-[#27272A]">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-amber-400" /> Todo
                    </span>
                    <span className="text-xs font-mono text-slate-500">{tasksByStatus.todo.length}</span>
                  </div>

                  <div className="space-y-3 min-h-[200px]">
                    {tasksByStatus.todo.map((t) => (
                      <div key={t.id} className="p-4 rounded-xl bg-[#18181b] border border-[#27272A] space-y-3 shadow-lg">
                        <div className="flex items-start justify-between gap-2">
                          <div className="text-xs font-bold text-white">{t.title}</div>
                          <button
                            onClick={() => handleDeleteTask(t.id, t.title)}
                            title="Delete Task"
                            className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-[#27272A]">
                          <span>{t.assignee_name || 'Unassigned'}</span>
                          <button
                            onClick={() => handleTaskStatusChange(t, 'doing')}
                            className="text-[10px] text-[#8B5CF6] hover:underline font-mono cursor-pointer"
                          >
                            Move to Doing →
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Column 2: DOING */}
                <div className="p-4 rounded-2xl bg-[#111113] border border-[#27272A] space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-[#27272A]">
                    <span className="text-xs font-bold text-[#8B5CF6] uppercase tracking-wider flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[#8B5CF6] animate-pulse" /> Doing
                    </span>
                    <span className="text-xs font-mono text-slate-500">{tasksByStatus.doing.length}</span>
                  </div>

                  <div className="space-y-3 min-h-[200px]">
                    {tasksByStatus.doing.map((t) => (
                      <div key={t.id} className="p-4 rounded-xl bg-[#18181b] border border-[#8B5CF6]/50 space-y-3 shadow-lg">
                        <div className="flex items-start justify-between gap-2">
                          <div className="text-xs font-bold text-white">{t.title}</div>
                          <button
                            onClick={() => handleDeleteTask(t.id, t.title)}
                            title="Delete Task"
                            className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-[#27272A]">
                          <span>{t.assignee_name || 'Unassigned'}</span>
                          <button
                            onClick={() => handleTaskStatusChange(t, 'done')}
                            className="text-[10px] text-emerald-400 hover:underline font-mono cursor-pointer"
                          >
                            Mark Done ✓
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Column 3: DONE */}
                <div className="p-4 rounded-2xl bg-[#111113] border border-[#27272A] space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-[#27272A]">
                    <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-400" /> Done
                    </span>
                    <span className="text-xs font-mono text-slate-500">{tasksByStatus.done.length}</span>
                  </div>

                  <div className="space-y-3 min-h-[200px]">
                    {tasksByStatus.done.map((t) => (
                      <div key={t.id} className="p-4 rounded-xl bg-[#18181b]/50 border border-[#27272A] space-y-2 opacity-80">
                        <div className="flex items-start justify-between gap-2">
                          <div className="text-xs font-bold text-slate-300 line-through">{t.title}</div>
                          <button
                            onClick={() => handleDeleteTask(t.id, t.title)}
                            title="Delete Task"
                            className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-[#27272A]">
                          <span>{t.assignee_name || 'Unassigned'}</span>
                          <span className="text-emerald-400 font-mono text-[10px]">Completed</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* TAB 4: GLOBAL SEARCH */}
          {activeTab === 'search' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4">
                <h2 className="text-2xl font-extrabold text-white">Global Semantic Search</h2>
                <p className="text-xs text-slate-400">Search across meeting titles, transcript turns, tasks, and consensus decisions.</p>

                <div className="relative">
                  <Search className="w-5 h-5 text-slate-500 absolute left-4 top-3.5" />
                  <input
                    type="text"
                    placeholder="Search terms (e.g. 'authentication', 'rate limiting', 'pricing', 'architecture')..."
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    className="w-full bg-[#18181b] border border-[#27272A] rounded-xl pl-12 pr-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#8B5CF6]"
                  />
                  {searchLoading && (
                    <Loader2 className="w-4 h-4 text-[#8B5CF6] animate-spin absolute right-4 top-4" />
                  )}
                </div>
              </div>

              {/* Search Results */}
              <div className="space-y-3">
                <div className="text-xs font-mono uppercase text-slate-500">
                  {searchResults?.results ? `${searchResults.results.length} matches found` : 'Search across workspace meetings'}
                </div>

                {searchResults?.results && searchResults.results.length > 0 ? (
                  searchResults.results.map((item, idx) => (
                    <div
                      key={idx}
                      onClick={() => {
                        setSelectedMeetingId(item.meeting_id);
                        setActiveTab('meeting');
                        if (item.type === 'transcript') setMeetingSubTab('transcript');
                        if (item.type === 'task') setMeetingSubTab('tasks');
                        if (item.type === 'decision') setMeetingSubTab('summary');
                      }}
                      className="p-4 rounded-xl bg-[#111113] border border-[#27272A] space-y-2 hover:border-[#8B5CF6] transition-colors cursor-pointer"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-[#8B5CF6]">{item.meeting_title}</span>
                          <span className="px-1.5 py-0.5 rounded bg-[#27272A] text-[10px] font-mono uppercase text-slate-300">
                            {item.type}
                          </span>
                        </div>
                        {item.timestamp && (
                          <span className="text-[10px] font-mono text-slate-500">@{item.timestamp}</span>
                        )}
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed font-sans">
                        "{item.snippet}"
                      </p>
                    </div>
                  ))
                ) : debouncedSearchQuery ? (
                  <div className="p-8 text-center border border-dashed border-[#27272A] rounded-xl text-xs text-slate-500">
                    No matching results found for "{debouncedSearchQuery}".
                  </div>
                ) : null}
              </div>
            </div>
          )}

          {/* TAB 5: ANALYTICS */}
          {activeTab === 'analytics' && (
            <div className="space-y-6 animate-fadeIn">
              <div>
                <h2 className="text-2xl font-extrabold text-white">Workspace Analytics</h2>
                <p className="text-xs text-slate-400 mt-0.5">Real-time metrics computed from live meetings and transcript turns.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Speaking Time Distribution */}
                <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4">
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Speaker Turn Distribution {meetingDetail?.title ? `(${meetingDetail.title})` : ''}
                  </h3>

                  {analyticsSpeakerStats.length > 0 ? (
                    <div className="space-y-3 pt-2">
                      {analyticsSpeakerStats.map((stat, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-300 font-semibold">{stat.speaker}</span>
                            <span className="text-[#8B5CF6] font-mono font-bold">
                              {stat.percentage}% ({stat.hours} hrs)
                            </span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-[#18181b] overflow-hidden">
                            <div className="h-full bg-[#8B5CF6]" style={{ width: `${stat.percentage}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 italic">Select a completed meeting to view speaker distribution.</p>
                  )}
                </div>

                {/* Action Item Breakdown */}
                <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4">
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">Task Completion Breakdown</h3>
                  <div className="space-y-4 pt-2">
                    <div className="flex items-center justify-between text-xs p-3 rounded-xl bg-[#18181b] border border-[#27272A]">
                      <span className="text-slate-300">Total Action Items</span>
                      <span className="font-mono font-bold text-white">{workspaceTasks?.length || 0}</span>
                    </div>

                    <div className="flex items-center justify-between text-xs p-3 rounded-xl bg-[#18181b] border border-[#27272A]">
                      <span className="text-slate-300">Completed Tasks</span>
                      <span className="font-mono font-bold text-emerald-400">{tasksByStatus.done.length}</span>
                    </div>

                    <div className="flex items-center justify-between text-xs p-3 rounded-xl bg-[#18181b] border border-[#27272A]">
                      <span className="text-slate-300">In Progress (Doing)</span>
                      <span className="font-mono font-bold text-[#8B5CF6]">{tasksByStatus.doing.length}</span>
                    </div>

                    <div className="flex items-center justify-between text-xs p-3 rounded-xl bg-[#18181b] border border-[#27272A]">
                      <span className="text-slate-300">To Do</span>
                      <span className="font-mono font-bold text-amber-400">{tasksByStatus.todo.length}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: TEAM MEMBERS */}
          {activeTab === 'team' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-extrabold text-white">{activeWorkspace?.name || 'Workspace'} Members</h2>
                  <p className="text-xs text-slate-400 mt-0.5">Manage team access and permissions.</p>
                </div>
                <button
                  onClick={() => setInviteModalOpen(true)}
                  className="px-4 py-2 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] text-white text-xs font-bold cursor-pointer shadow-lg shadow-[#8B5CF6]/20"
                >
                  + Invite Teammate
                </button>
              </div>

              <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Active Workspace Members ({members?.length || 1})
                </h3>

                <div className="space-y-3">
                  {members?.map((m) => (
                    <div
                      key={m.user_id}
                      className="p-4 rounded-xl bg-[#18181b] border border-[#27272A] flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3">
                        <img
                          src={getAvatar(m.name, m.avatar_url)}
                          alt={m.name}
                          className="w-9 h-9 rounded-full object-cover"
                        />
                        <div>
                          <div className="text-xs font-bold text-white">{m.name}</div>
                          <div className="text-[11px] text-slate-400">{m.email}</div>
                        </div>
                      </div>
                      <span className="text-[10px] font-mono px-2.5 py-1 rounded bg-[#8B5CF6]/20 text-[#8B5CF6] font-bold uppercase">
                        {m.role}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: INTEGRATIONS */}
          {activeTab === 'integrations' && (
            <div className="space-y-6 animate-fadeIn">
              <div>
                <h2 className="text-2xl font-extrabold text-white">Workspace Integrations</h2>
                <p className="text-xs text-slate-400 mt-0.5">Connect MeetPilot AI to issue trackers, Discord channels, Google Calendar, and Zoom cloud recordings.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* 1. Discord Integration Card */}
                {(() => {
                  const discord = integrations?.find((i) => i.provider === 'discord');
                  const isConn = discord?.is_connected;
                  return (
                    <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4 flex flex-col justify-between">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-xl bg-[#5865F2]/20 border border-[#5865F2]/40 flex items-center justify-center text-[#5865F2] font-bold">
                              #
                            </div>
                            <div>
                              <div className="text-sm font-extrabold text-white">Discord Webhook</div>
                              <div className="text-[11px] font-mono text-slate-400">Digest Bot</div>
                            </div>
                          </div>

                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold flex items-center gap-1.5 ${
                              isConn
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : 'bg-[#18181b] text-slate-400 border border-[#27272A]'
                            }`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${isConn ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                            {isConn ? 'Connected' : 'Not Connected'}
                          </span>
                        </div>

                        <p className="text-xs text-slate-300 leading-relaxed">
                          Automatically broadcasts an executive digest (meeting overview, key takeaways, and top action items) to your team's Discord channel when a meeting completes.
                        </p>

                        {isConn && discord?.masked_identifier && (
                          <div className="p-2.5 rounded-xl bg-[#18181b] border border-[#27272A] text-[11px] font-mono text-slate-400 truncate">
                            Webhook: <span className="text-emerald-300">{discord.masked_identifier}</span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2 pt-2 border-t border-[#27272A]">
                        <button
                          onClick={() => {
                            setDiscordWebhookInput('');
                            setDiscordModalOpen(true);
                          }}
                          className="px-4 py-2 rounded-xl text-xs font-bold bg-[#8B5CF6] hover:bg-[#7c3aed] text-white transition-colors cursor-pointer shadow-lg shadow-[#8B5CF6]/20"
                        >
                          {isConn ? 'Update Webhook' : 'Configure Discord'}
                        </button>

                        {isConn && (
                          <button
                            onClick={() => handleDisconnectIntegration('discord', 'Discord Webhook')}
                            className="px-3.5 py-2 rounded-xl text-xs font-bold text-rose-400 hover:text-rose-300 hover:bg-rose-950/20 border border-rose-500/30 transition-colors cursor-pointer"
                          >
                            Disconnect
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })()}

                {/* 2. Google Calendar Card */}
                {(() => {
                  const gcal = integrations?.find((i) => i.provider === 'google_calendar');
                  const isConn = gcal?.is_connected;
                  return (
                    <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4 flex flex-col justify-between">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-xl bg-blue-500/20 border border-blue-500/40 flex items-center justify-center text-blue-400 font-bold">
                              <Calendar className="w-4 h-4" />
                            </div>
                            <div>
                              <div className="text-sm font-extrabold text-white">Google Calendar</div>
                              <div className="text-[11px] font-mono text-slate-400">Event Sync</div>
                            </div>
                          </div>

                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold flex items-center gap-1.5 ${
                              isConn
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : 'bg-[#18181b] text-slate-400 border border-[#27272A]'
                            }`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${isConn ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                            {isConn ? 'Connected' : 'Not Connected'}
                          </span>
                        </div>

                        <p className="text-xs text-slate-300 leading-relaxed">
                          Automatically synchronizes detected action items with assigned due dates into Google Calendar events with direct links to the meeting audio timestamp.
                        </p>

                        {isConn && gcal?.masked_identifier && (
                          <div className="p-2.5 rounded-xl bg-[#18181b] border border-[#27272A] text-[11px] font-mono text-slate-400 truncate">
                            Account: <span className="text-blue-300">{gcal.masked_identifier}</span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2 pt-2 border-t border-[#27272A]">
                        <button
                          onClick={handleConnectGoogleCalendar}
                          className="px-4 py-2 rounded-xl text-xs font-bold bg-[#8B5CF6] hover:bg-[#7c3aed] text-white transition-colors cursor-pointer shadow-lg shadow-[#8B5CF6]/20"
                        >
                          {isConn ? 'Reconnect Calendar' : 'Connect Google Calendar'}
                        </button>

                        {isConn && (
                          <button
                            onClick={() => handleDisconnectIntegration('google_calendar', 'Google Calendar')}
                            className="px-3.5 py-2 rounded-xl text-xs font-bold text-rose-400 hover:text-rose-300 hover:bg-rose-950/20 border border-rose-500/30 transition-colors cursor-pointer"
                          >
                            Disconnect
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })()}

                {/* 3. Zoom Cloud Recordings Card */}
                {(() => {
                  const zoom = integrations?.find((i) => i.provider === 'zoom');
                  const isConn = zoom?.is_connected;
                  return (
                    <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4 flex flex-col justify-between">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-xl bg-sky-500/20 border border-sky-500/40 flex items-center justify-center text-sky-400 font-bold">
                              <Radio className="w-4 h-4" />
                            </div>
                            <div>
                              <div className="text-sm font-extrabold text-white">Zoom Cloud Recordings</div>
                              <div className="text-[11px] font-mono text-slate-400">1-Click Importer</div>
                            </div>
                          </div>

                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold flex items-center gap-1.5 ${
                              isConn
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : 'bg-[#18181b] text-slate-400 border border-[#27272A]'
                            }`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${isConn ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                            {isConn ? 'Connected' : 'Not Connected'}
                          </span>
                        </div>

                        <p className="text-xs text-slate-300 leading-relaxed">
                          Fetch and browse Zoom cloud audio/video recordings. Import any recording directly into MeetPilot AI for speech diarization and summary extraction.
                        </p>

                        {isConn && zoom?.masked_identifier && (
                          <div className="p-2.5 rounded-xl bg-[#18181b] border border-[#27272A] text-[11px] font-mono text-slate-400 truncate">
                            Status: <span className="text-sky-300">{zoom.masked_identifier}</span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2 pt-2 border-t border-[#27272A]">
                        {isConn ? (
                          <>
                            <button
                              onClick={handleOpenZoomPicker}
                              className="px-4 py-2 rounded-xl text-xs font-bold bg-[#8B5CF6] hover:bg-[#7c3aed] text-white transition-colors cursor-pointer shadow-lg shadow-[#8B5CF6]/20"
                            >
                              Browse Recordings
                            </button>
                            <button
                              onClick={() => handleDisconnectIntegration('zoom', 'Zoom Account')}
                              className="px-3.5 py-2 rounded-xl text-xs font-bold text-rose-400 hover:text-rose-300 hover:bg-rose-950/20 border border-rose-500/30 transition-colors cursor-pointer"
                            >
                              Disconnect
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={handleConnectZoom}
                            className="px-4 py-2 rounded-xl text-xs font-bold bg-[#8B5CF6] hover:bg-[#7c3aed] text-white transition-colors cursor-pointer shadow-lg shadow-[#8B5CF6]/20"
                          >
                            Connect Zoom Account
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })()}

                {/* 4. Linear Issue Tracker Card */}
                <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-4 flex flex-col justify-between">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-xl bg-purple-500/20 border border-purple-500/40 flex items-center justify-center text-purple-400 font-bold">
                          <Kanban className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="text-sm font-extrabold text-white">Linear & Jira</div>
                          <div className="text-[11px] font-mono text-slate-400">Sprint Sync</div>
                        </div>
                      </div>

                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#18181b] text-slate-400 border border-[#27272A]">
                        Active
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">
                      Sync meeting action items and assignees directly to your product engineering backlog with priority and deadline metadata.
                    </p>
                  </div>

                  <div className="flex items-center gap-2 pt-2 border-t border-[#27272A]">
                    <button
                      onClick={() => showToast('Linear issue sync is active on your workspace Kanban board.')}
                      className="px-4 py-2 rounded-xl text-xs font-bold bg-[#18181b] hover:bg-[#27272A] text-slate-300 border border-[#27272A] transition-colors cursor-pointer"
                    >
                      View Board Sync
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}


          {/* TAB 8: NOTIFICATIONS */}
          {activeTab === 'notifications' && (
            <div className="space-y-6 animate-fadeIn">
              <div>
                <h2 className="text-2xl font-extrabold text-white">Notifications & Activity</h2>
                <p className="text-xs text-slate-400 mt-0.5">Live events generated during meeting processing.</p>
              </div>

              <div className="p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-3">
                {notifications && notifications.length > 0 ? (
                  notifications.map((n) => (
                    <div key={n.id} className="p-4 rounded-xl bg-[#18181b] border border-[#27272A] flex items-center justify-between">
                      <div>
                        <div className="text-xs font-bold text-white flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-[#8B5CF6]" />
                          <span>{n.message}</span>
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono mt-0.5 ml-4">
                          Type: {n.type}
                        </div>
                      </div>
                      <span className="text-[10px] font-mono text-slate-500">{formatMeetingDate(n.created_at)}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-500 italic text-center py-6">No recent notifications.</p>
                )}
              </div>
            </div>
          )}

          {/* TAB 9: SETTINGS */}
          {activeTab === 'settings' && (
            <div className="space-y-6 animate-fadeIn">
              <div>
                <h2 className="text-2xl font-extrabold text-white">Workspace Settings</h2>
                <p className="text-xs text-slate-400 mt-0.5">Manage your authenticated profile and workspace configuration.</p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-4 p-4 rounded-2xl bg-[#111113] border border-[#27272A] space-y-1">
                  <button
                    onClick={() => setSettingsTab('profile')}
                    className={`w-full text-left px-3.5 py-2.5 rounded-xl text-xs font-bold transition-colors cursor-pointer ${
                      settingsTab === 'profile' ? 'bg-[#8B5CF6] text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    User Profile
                  </button>

                  <button
                    onClick={() => setSettingsTab('workspace')}
                    className={`w-full text-left px-3.5 py-2.5 rounded-xl text-xs font-bold transition-colors cursor-pointer ${
                      settingsTab === 'workspace' ? 'bg-[#8B5CF6] text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Workspace Details
                  </button>

                  <button
                    onClick={() => setSettingsTab('theme')}
                    className={`w-full text-left px-3.5 py-2.5 rounded-xl text-xs font-bold transition-colors cursor-pointer ${
                      settingsTab === 'theme' ? 'bg-[#8B5CF6] text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Appearance & Theme
                  </button>
                </div>

                <div className="lg:col-span-8 p-6 rounded-2xl bg-[#111113] border border-[#27272A] space-y-6">
                  {settingsTab === 'profile' && (
                    <div className="space-y-4">
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">Profile Information</h3>
                      <div className="space-y-3 text-xs">
                        <div>
                          <span className="text-slate-500 font-mono">Full Name:</span>
                          <div className="text-white font-bold mt-1">{user?.fullName || user?.firstName || 'User'}</div>
                        </div>
                        <div>
                          <span className="text-slate-500 font-mono">Primary Email:</span>
                          <div className="text-white font-bold mt-1">{user?.primaryEmailAddress?.emailAddress}</div>
                        </div>
                        <div>
                          <span className="text-slate-500 font-mono">Clerk User ID:</span>
                          <div className="text-slate-400 font-mono text-[11px] mt-1">{user?.id}</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {settingsTab === 'workspace' && (
                    <div className="space-y-6">
                      <div className="space-y-4">
                        <h3 className="text-sm font-bold text-white uppercase tracking-wider">Workspace Information</h3>
                        <div className="space-y-3 text-xs">
                          <div>
                            <span className="text-slate-500 font-mono">Workspace ID:</span>
                            <div className="text-slate-400 font-mono text-[11px] mt-1">{activeWorkspace?.id}</div>
                          </div>
                          <div>
                            <span className="text-slate-500 font-mono">Workspace Name:</span>
                            <div className="text-white font-bold mt-1">{activeWorkspace?.name}</div>
                          </div>
                          <div>
                            <span className="text-slate-500 font-mono">Total Meetings:</span>
                            <div className="text-white font-bold mt-1">{meetings?.length || 0} recording(s)</div>
                          </div>
                          <div>
                            <span className="text-slate-500 font-mono">Team Members:</span>
                            <div className="text-white font-bold mt-1">{members?.length || 0} member(s)</div>
                          </div>
                        </div>
                      </div>

                      {/* Danger Zone: Delete Workspace */}
                      {activeWorkspace && (
                        <div className="pt-6 border-t border-[#27272A] space-y-3">
                          <div className="p-4 rounded-xl border border-red-500/30 bg-red-950/10 space-y-3">
                            <div className="flex items-center gap-2 text-red-400">
                              <AlertCircle className="w-4 h-4" />
                              <h4 className="text-xs font-bold uppercase tracking-wider">Danger Zone</h4>
                            </div>
                            <p className="text-xs text-slate-300">
                              Permanently delete <span className="font-bold text-white">"{activeWorkspace.name}"</span> and all associated recordings, audio files, diarized transcripts, and action items. This destructive action cannot be undone.
                            </p>
                            <div className="pt-1">
                              <button
                                onClick={() => {
                                  setDeleteConfirmText('');
                                  setDeleteWorkspaceError(null);
                                  setDeleteWorkspaceModalOpen(true);
                                }}
                                className="px-4 py-2 rounded-xl bg-red-600/90 hover:bg-red-600 text-white text-xs font-bold flex items-center gap-2 cursor-pointer transition-colors shadow-lg shadow-red-900/20"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                                <span>Delete this Workspace</span>
                              </button>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}


                  {settingsTab === 'theme' && (
                    <div className="space-y-4">
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">Theme Preferences</h3>
                      <p className="text-xs text-slate-400">
                        Dark Luxury (#09090B zinc neutral with #8B5CF6 violet accent) is active.
                      </p>
                      <div className="p-4 rounded-xl bg-[#09090B] border border-[#8B5CF6] text-xs font-bold text-white inline-block">
                        Dark Luxury (Active)
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* MODALS */}

      {/* 1. Quick Upload Modal */}
      {uploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="relative w-full max-w-md rounded-2xl bg-[#111113] border border-[#27272A] p-6 text-slate-200 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Upload Meeting Audio</h3>
            <p className="text-xs text-slate-400">
              Upload MP3, WAV, AAC, or M4A audio for Gemini speech diarization and action item extraction.
            </p>

            <form onSubmit={handleUploadMeeting} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[11px] font-mono text-slate-400">Meeting Title</label>
                <input
                  type="text"
                  placeholder="e.g. Q3 Architecture & Security Review"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  className="w-full bg-[#18181b] border border-[#27272A] rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#8B5CF6]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-mono text-slate-400">Select Audio File</label>
                <input
                  type="file"
                  accept="audio/*,video/*"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setUploadFile(e.target.files[0]);
                      if (!uploadTitle) {
                        setUploadTitle(e.target.files[0].name.replace(/\.[^/.]+$/, ''));
                      }
                    }
                  }}
                  className="w-full text-xs text-slate-400 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-[#8B5CF6] file:text-white hover:file:bg-[#7c3aed] cursor-pointer"
                />
              </div>

              {uploadProgressMsg && (
                <div className="flex items-center gap-2 text-xs text-[#8B5CF6] font-mono">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>{uploadProgressMsg}</span>
                </div>
              )}

              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setUploadModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-[#18181b] hover:bg-[#27272A] text-xs font-bold text-slate-400 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!uploadFile || uploading}
                  className="px-5 py-2 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] disabled:opacity-40 text-xs font-bold text-white transition-colors cursor-pointer shadow-lg shadow-[#8B5CF6]/20"
                >
                  {uploading ? 'Uploading...' : 'Upload & Process'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Live In-Browser Microphone Recording Modal */}
      {recordModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-md rounded-2xl bg-[#111113] border border-[#27272A] p-6 text-slate-200 space-y-5 shadow-2xl shadow-black/80">
            <div className="flex items-center justify-between border-b border-[#27272A] pb-3">
              <div className="flex items-center gap-2.5 text-rose-400 font-bold text-sm">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
                <Mic className="w-4 h-4 text-rose-400" />
                <h3 className="text-white font-extrabold text-base">In-Browser Live Mic Recording</h3>
              </div>
              <span className="text-[10px] font-mono uppercase text-slate-400 px-2 py-0.5 rounded bg-[#18181b]">
                MediaRecorder
              </span>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[11px] font-mono text-slate-400">Meeting / Session Title</label>
                <input
                  type="text"
                  placeholder="e.g. Daily Standup / Customer Discovery"
                  value={liveRecordTitle}
                  onChange={(e) => setLiveRecordTitle(e.target.value)}
                  disabled={isRecording}
                  className="w-full bg-[#18181b] border border-[#27272A] rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#8B5CF6]"
                />
              </div>

              {/* Live Waveform & Timer Banner */}
              <div className="p-6 rounded-2xl bg-[#18181b] border border-[#27272A] text-center space-y-3">
                <div className="text-3xl font-extrabold font-mono tracking-wider text-white">
                  {formatTimestampSeconds(recordingSeconds)}
                </div>

                {isRecording ? (
                  <div className="flex items-center justify-center gap-1.5 py-2">
                    <div className="w-1.5 h-6 bg-rose-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-1.5 h-10 bg-rose-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-1.5 h-7 bg-rose-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    <div className="w-1.5 h-12 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '450ms' }} />
                    <div className="w-1.5 h-8 bg-rose-400 rounded-full animate-bounce" style={{ animationDelay: '200ms' }} />
                    <div className="w-1.5 h-5 bg-rose-500 rounded-full animate-bounce" style={{ animationDelay: '100ms' }} />
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">
                    Click "Start Recording" to capture audio directly through your microphone.
                  </p>
                )}

                {isRecording && (
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/10 text-rose-300 text-[11px] font-mono">
                    <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                    <span>Capturing live microphone audio stream...</span>
                  </div>
                )}
              </div>

              {recordError && (
                <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/40 text-xs text-rose-300 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>{recordError}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={cancelLiveRecording}
                  className="px-4 py-2 rounded-xl bg-[#18181b] hover:bg-[#27272A] text-xs font-bold text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  Cancel
                </button>

                {!isRecording ? (
                  <button
                    type="button"
                    onClick={startLiveRecording}
                    className="px-5 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-xs font-bold text-white transition-colors cursor-pointer shadow-lg shadow-rose-900/30 flex items-center gap-2"
                  >
                    <Radio className="w-3.5 h-3.5" />
                    <span>Start Recording</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={stopAndSubmitRecording}
                    disabled={submittingRecording}
                    className="px-5 py-2 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] disabled:opacity-50 text-xs font-bold text-white transition-colors cursor-pointer shadow-lg shadow-[#8B5CF6]/30 flex items-center gap-2"
                  >
                    {submittingRecording ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Uploading Recording...</span>
                      </>
                    ) : (
                      <>
                        <Square className="w-3.5 h-3.5 fill-current" />
                        <span>Stop & Transcribe</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}


      {/* 2. Create Workspace Modal */}
      {newWorkspaceModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="relative w-full max-w-md rounded-2xl bg-[#111113] border border-[#27272A] p-6 text-slate-200 space-y-4 shadow-2xl">
            <h3 className="text-lg font-extrabold text-white">Create New Workspace</h3>
            <p className="text-xs text-slate-400">Isolate meetings, transcripts, and action items for a team.</p>

            <form onSubmit={handleCreateWorkspace} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[11px] font-mono text-slate-400">Workspace Name</label>
                <input
                  type="text"
                  placeholder="e.g. Platform Architecture"
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  autoFocus
                  className="w-full bg-[#18181b] border border-[#27272A] rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#8B5CF6]"
                />
              </div>

              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setNewWorkspaceModalOpen(false)}
                  className="px-4 py-2 rounded-xl border border-[#27272A] text-xs font-semibold text-slate-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newWorkspaceName.trim() || creatingWorkspace}
                  className="px-4 py-2 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] disabled:opacity-50 text-xs font-bold text-white transition-colors cursor-pointer shadow-lg shadow-[#8B5CF6]/20"
                >
                  {creatingWorkspace ? 'Creating...' : 'Create Workspace'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Discord Webhook Configuration Modal */}
      {discordModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-md rounded-2xl bg-[#111113] border border-[#27272A] p-6 text-slate-200 space-y-4 shadow-2xl">
            <div className="flex items-center gap-2.5 text-[#5865F2]">
              <div className="w-8 h-8 rounded-xl bg-[#5865F2]/20 border border-[#5865F2]/40 flex items-center justify-center text-[#5865F2] font-bold">
                #
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Configure Discord Webhook</h3>
                <p className="text-xs text-slate-400">Post automated meeting digests to your Discord channel.</p>
              </div>
            </div>

            <form onSubmit={handleSaveDiscordWebhook} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[11px] font-mono text-slate-400">Discord Webhook URL</label>
                <input
                  type="url"
                  placeholder="https://discord.com/api/webhooks/..."
                  value={discordWebhookInput}
                  onChange={(e) => setDiscordWebhookInput(e.target.value)}
                  required
                  autoFocus
                  className="w-full bg-[#18181b] border border-[#27272A] rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#8B5CF6]"
                />
              </div>

              <div className="p-3 rounded-xl bg-[#18181b] border border-[#27272A] text-[11px] text-slate-400 space-y-1">
                <div className="font-bold text-white flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Encrypted at Rest</span>
                </div>
                <p>
                  Webhook credentials are encrypted via Fernet AES before saving and scoped strictly to this workspace.
                </p>
              </div>

              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setDiscordModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-[#18181b] hover:bg-[#27272A] text-xs font-bold text-slate-400 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingDiscord || !discordWebhookInput.trim()}
                  className="px-5 py-2 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] disabled:opacity-50 text-xs font-bold text-white transition-colors cursor-pointer shadow-lg shadow-[#8B5CF6]/20 flex items-center gap-2"
                >
                  {savingDiscord ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <span>Save & Connect</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Zoom Cloud Recordings Picker Modal */}
      {zoomPickerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-2xl rounded-2xl bg-[#111113] border border-[#27272A] p-6 text-slate-200 space-y-5 shadow-2xl shadow-black/80 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-[#27272A] pb-3">
              <div className="flex items-center gap-2.5 text-sky-400">
                <div className="w-8 h-8 rounded-xl bg-sky-500/20 border border-sky-500/40 flex items-center justify-center text-sky-400 font-bold">
                  <Radio className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-white">Import Zoom Cloud Recordings</h3>
                  <p className="text-xs text-slate-400">Select a cloud recording to pull and process with Gemini 2.0 Flash.</p>
                </div>
              </div>

              <button
                onClick={() => setZoomPickerOpen(false)}
                className="p-1.5 rounded-xl bg-[#18181b] hover:bg-[#27272A] text-slate-400 hover:text-white cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {loadingZoomRecordings ? (
                <div className="p-12 text-center space-y-3">
                  <Loader2 className="w-8 h-8 text-sky-400 animate-spin mx-auto" />
                  <p className="text-xs text-slate-400">Fetching cloud recordings from Zoom API...</p>
                </div>
              ) : zoomRecordings.length === 0 ? (
                <div className="p-12 text-center border border-dashed border-[#27272A] rounded-2xl space-y-2">
                  <Radio className="w-8 h-8 text-slate-500 mx-auto" />
                  <p className="text-xs text-slate-400">No cloud recordings found in the last 30 days.</p>
                </div>
              ) : (
                zoomRecordings.map((rec) => (
                  <div
                    key={rec.id}
                    className="p-4 rounded-xl bg-[#18181b] border border-[#27272A] flex items-center justify-between gap-4 hover:border-sky-500/40 transition-colors"
                  >
                    <div className="space-y-1">
                      <div className="text-xs font-bold text-white flex items-center gap-2">
                        <span>{rec.topic}</span>
                        <span className="px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 font-mono text-[10px] uppercase font-bold">
                          {rec.file_type}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-400 flex items-center gap-3">
                        <span>{formatMeetingDate(rec.start_time)}</span>
                        <span>•</span>
                        <span>{rec.duration} mins</span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleImportZoomRecording(rec)}
                      disabled={importingZoomId === rec.id}
                      className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-bold transition-all shadow-md shadow-sky-900/30 shrink-0 flex items-center gap-2 cursor-pointer"
                    >
                      {importingZoomId === rec.id ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Importing...</span>
                        </>
                      ) : (
                        <>
                          <Upload className="w-3.5 h-3.5" />
                          <span>Import & Process</span>
                        </>
                      )}
                    </button>
                  </div>
                ))
              )}
            </div>

            <div className="flex justify-end pt-2 border-t border-[#27272A]">
              <button
                type="button"
                onClick={() => setZoomPickerOpen(false)}
                className="px-4 py-2 rounded-xl bg-[#18181b] hover:bg-[#27272A] text-xs font-bold text-slate-400 transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Invite Member Modal */}
      {inviteModalOpen && (

        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="relative w-full max-w-md rounded-2xl bg-[#111113] border border-[#27272A] p-6 text-slate-200 space-y-4 shadow-2xl">
            <h3 className="text-lg font-extrabold text-white">Invite Teammate</h3>
            <p className="text-xs text-slate-400">Add a registered user by email to {activeWorkspace?.name}.</p>

            <form onSubmit={handleInviteMember} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[11px] font-mono text-slate-400">Teammate Email</label>
                <input
                  type="email"
                  placeholder="e.g. sarah@acme.dev"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  autoFocus
                  className="w-full bg-[#18181b] border border-[#27272A] rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#8B5CF6]"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[11px] font-mono text-slate-400">Workspace Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as 'admin' | 'member')}
                  className="w-full bg-[#18181b] border border-[#27272A] rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-[#8B5CF6]"
                >
                  <option value="member">Member (Read & Upload)</option>
                  <option value="admin">Admin (Full Control)</option>
                </select>
              </div>

              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setInviteModalOpen(false)}
                  className="px-4 py-2 rounded-xl border border-[#27272A] text-xs font-semibold text-slate-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!inviteEmail.trim() || inviting}
                  className="px-4 py-2 rounded-xl bg-[#8B5CF6] hover:bg-[#7c3aed] disabled:opacity-50 text-xs font-bold text-white transition-colors cursor-pointer shadow-lg shadow-[#8B5CF6]/20"
                >
                  {inviting ? 'Inviting...' : 'Send Invite'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 4. Delete Workspace Confirmation Modal */}
      {deleteWorkspaceModalOpen && activeWorkspace && (

        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-md rounded-2xl bg-[#111113] border border-red-500/40 p-6 text-slate-200 space-y-5 shadow-2xl shadow-red-950/50">
            <div className="flex items-center gap-3 text-red-400">
              <div className="p-2 rounded-xl bg-red-950/50 border border-red-500/30">
                <AlertCircle className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-white">Delete Workspace</h3>
                <p className="text-[11px] text-red-400 font-mono">Destructive Action Confirmation</p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-[#18181b] border border-[#27272A] text-xs text-slate-300 space-y-2">
              <p>
                Are you sure you want to permanently delete <strong className="text-white font-bold">{activeWorkspace.name}</strong>?
              </p>
              <ul className="list-disc pl-4 space-y-1 text-slate-400 text-[11px]">
                <li>All meetings and uploaded audio recordings will be deleted from disk.</li>
                <li>All transcripts, summaries, and action items will be removed.</li>
                <li>Team memberships for this workspace will be revoked.</li>
              </ul>
            </div>

            <form onSubmit={handleDeleteWorkspace} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[11px] font-mono text-slate-400">
                  Type <span className="text-red-400 font-bold underline select-all">{activeWorkspace.name}</span> to confirm:
                </label>
                <input
                  type="text"
                  placeholder={activeWorkspace.name}
                  value={deleteConfirmText}
                  onChange={(e) => {
                    setDeleteConfirmText(e.target.value);
                    if (deleteWorkspaceError) setDeleteWorkspaceError(null);
                  }}
                  autoFocus
                  className="w-full bg-[#18181b] border border-red-500/30 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-red-500 font-mono"
                />
              </div>

              {deleteWorkspaceError && (
                <div className="text-xs text-red-400 font-mono flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5" />
                  <span>{deleteWorkspaceError}</span>
                </div>
              )}

              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setDeleteWorkspaceModalOpen(false);
                    setDeleteConfirmText('');
                    setDeleteWorkspaceError(null);
                  }}
                  className="px-4 py-2 rounded-xl bg-[#18181b] hover:bg-[#27272A] text-xs font-bold text-slate-300 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={
                    deleteConfirmText.trim().toLowerCase() !== activeWorkspace.name.trim().toLowerCase() ||
                    deletingWorkspace
                  }
                  className="px-5 py-2 rounded-xl bg-red-600 hover:bg-red-700 disabled:opacity-40 text-xs font-bold text-white transition-colors cursor-pointer shadow-lg shadow-red-900/30 flex items-center gap-2"
                >
                  {deletingWorkspace ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Deleting Workspace...</span>
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Permanently Delete</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Step C1 & C3: Live Google Meet Capture & Mandatory Legal Consent Modal */}
      <LiveMeetingModal
        isOpen={liveMeetModalOpen}
        onClose={() => setLiveMeetModalOpen(false)}
        workspaceId={activeWorkspaceId || ''}
        getToken={getToken}
        onSuccess={(created) => {
          mutateMeetings();
          setSelectedMeetingId(created.id);
          setActiveTab('meeting');
          showToast(`Joined Google Meet call! Bot is actively transcribing.`);
        }}
      />

      {/* Floating Feedback Toast */}
      {toastMessage && (
        <div
          className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-2xl border shadow-2xl text-xs font-semibold animate-fadeIn ${
            toastMessage.type === 'error'
              ? 'bg-rose-950/90 border-rose-500/50 text-rose-200'
              : 'bg-[#111113]/95 border-[#8B5CF6]/50 text-white shadow-[#8B5CF6]/20'
          }`}
        >
          {toastMessage.type === 'error' ? (
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-[#8B5CF6] shrink-0" />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}
    </div>
  );
};
