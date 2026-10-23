import React, { useEffect, useMemo, useRef, useState } from 'react';
import useSWR, { useSWRConfig } from 'swr';
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
  Brain,
} from 'lucide-react';

import { useUser, useClerk, useAuth } from '@clerk/clerk-react';
import { MeetPilotLogo } from './Logo';
import {
  TaskPriority,
  TaskStatus,
  MeetingStatus,
  isProcessingStatus,
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
  ApiKnowledgeDocument,
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
  useWorkspaceAnalytics,
  useWorkspaceDocuments,
  useNotifications,
  useSearch,
  uploadMeetingAudio,
  createWorkspaceApi,
  createDemoWorkspaceApi,
  updateWorkspaceApi,
  inviteWorkspaceMemberApi,
  removeWorkspaceMemberApi,
  updateTaskApi,
  createTaskApi,
  deleteTaskApi,
  sendChatMessageApi,
  deleteMeetingApi,
  updateMeetingApi,
  updateMeetingSummaryApi,
  updateDecisionApi,
  deleteDecisionApi,
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
  updateMeetingDisplayScript,
} from '../services/api';
import { beginIntegrationOAuth } from '../utils/integrationOAuth';
import { MeetingPrintReport } from './workspace/MeetingPrintReport';
import { WorkspaceTaskBoard } from './workspace/WorkspaceTaskBoard';
import { WorkspaceShell, type WorkspaceTab } from './workspace/WorkspaceShell';
import { WorkspaceOverview } from './workspace/WorkspaceOverview';
import { MeetingLibrary } from './workspace/MeetingLibrary';
import { Modal } from './Modal';
import { LiveMeetingModal } from './LiveMeetingModal';
import { MeetingHeader } from './workspace/MeetingHeader';
import { PilotVoicePanel } from './workspace/PilotVoicePanel';
import { PilotVoiceSettings } from './workspace/PilotVoiceSettings';
import { AppearanceSettings } from './workspace/AppearanceSettings';
import { LegalSettings } from './workspace/LegalSettings';
import { ensurePolicyAcceptance, PolicyActionCancelled } from '../services/legalConsent';
import { MeetingLanguageSelect, MeetingScriptContext } from './workspace/MeetingLanguageDisplay';
import { MEETING_LANGUAGES } from '../utils/meetingLanguage';
import { LiveInsights } from './workspace/LiveInsights';
import { WorkspaceManagerContext, isWorkspaceManager } from '../utils/workspacePermissions';
import { JoinWorkspaceModal, WorkspaceAccessPanel, WorkspaceOnboarding } from './workspace/WorkspaceAccessPanel';
import type { JoinRequest } from './workspace/WorkspaceAccessPanel';
import { MeetingIdentities } from './workspace/MeetingIdentities';
import { MeetingAtAGlance } from './workspace/MeetingAtAGlance';
import { MeetingAudioPlayer } from './workspace/MeetingAudioPlayer';
import { MeetingReviewTools } from './workspace/MeetingReviewTools';
import { MeetingBookmarks } from './workspace/MeetingBookmarks';
import { DiarizedTranscript } from './workspace/DiarizedTranscript';
import { ExecutiveIntelligence } from './workspace/ExecutiveIntelligence';
import { ActionItemsView } from './workspace/ActionItemsView';
import { MeetingAssistantChat } from './workspace/MeetingAssistantChat';
import { ProcessingStateCard } from './workspace/ProcessingStateCard';
import { MeetingErrorCard } from './workspace/MeetingErrorCard';
import { AIKnowledgeView } from './workspace/AIKnowledgeView';
import { WorkspaceSemanticSearch } from './workspace/WorkspaceSemanticSearch';
import { getMeetingSpeakerStats, formatTimeSeconds } from '../utils/speakerUtils';




interface AppWorkspaceProps {
  onBackToLanding: () => void;
}

const getAvatar = (name: string, fallback?: string | null) => {
  if (fallback) return fallback;
  const initials = (name || 'User').trim().split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase()
    .replace(/[&<>"']/g, '');
  return `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" rx="32" fill="#e6eeea"/><text x="32" y="38" text-anchor="middle" fill="#497061" font-family="Arial,sans-serif" font-size="22">${initials}</text></svg>`)}`;
};

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
  const { mutate: mutateCache } = useSWRConfig();
  const integrationPopup = useRef<Window | null>(null);
  const previousRole = useRef<string | undefined>(undefined);

  // Tab State
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('dashboard');

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
  const [joinWorkspaceOpen, setJoinWorkspaceOpen] = useState(false);
  const [newWorkspaceModalOpen, setNewWorkspaceModalOpen] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [exploringDemo, setExploringDemo] = useState(false);

  // Delete Workspace Modal & Confirmation States
  const [deleteWorkspaceModalOpen, setDeleteWorkspaceModalOpen] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [deletingWorkspace, setDeletingWorkspace] = useState(false);
  const [deleteWorkspaceError, setDeleteWorkspaceError] = useState<string | null>(null);


  // Selected Meeting Selection
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
  const [meetingSubTab, setMeetingSubTab] = useState<'summary' | 'transcript' | 'tasks' | 'chat' | 'review'>('summary');

  // Quick Upload Form State
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadLanguage, setUploadLanguage] = useState('en');
  const [savingDisplayScript, setSavingDisplayScript] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgressMsg, setUploadProgressMsg] = useState('');

  // Live Google Meet capture state; policy acknowledgment is handled once per account.
  const [liveMeetModalOpen, setLiveMeetModalOpen] = useState(false);
  const [retryLiveMeetingUrl, setRetryLiveMeetingUrl] = useState('');
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
  const beginAction = (action: () => void) => {
    void ensurePolicyAcceptance().then(action).catch(error => {
      if (!(error instanceof PolicyActionCancelled)) showToast(error instanceof Error ? error.message : 'Could not continue.', 'error');
    });
  };

  // Meeting Rename State
  const [editingMeetingTitle, setEditingMeetingTitle] = useState(false);
  const [renameMeetingInput, setRenameMeetingInput] = useState('');
  const [savingMeetingTitle, setSavingMeetingTitle] = useState(false);

  // Workspace Rename State
  const [editingWorkspaceName, setEditingWorkspaceName] = useState(false);
  const [workspaceRenameInput, setWorkspaceRenameInput] = useState('');
  const [savingWorkspaceName, setSavingWorkspaceName] = useState(false);

  // Settings subtab
  const [settingsTab, setSettingsTab] = useState<'profile' | 'workspace' | 'voice' | 'appearance'>('profile');

  // Debounce search input (300ms)
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearchQuery(searchInput.trim());
    }, 300);
    return () => clearTimeout(handler);
  }, [searchInput]);

  // SWR Data Fetching Hooks
  const { data: authSession } = useAuthMe(getToken);
  const { data: workspaces, error: workspacesError, isLoading: workspacesLoading, mutate: mutateWorkspaces } = useWorkspaces(getToken);

  // Select only an approved membership; organization creation is an explicit choice.
  useEffect(() => {
    if (workspaces && workspaces.length > 0) {
      if (!activeWorkspaceId || !workspaces.some((w) => w.id === activeWorkspaceId)) {
        setActiveWorkspaceId(workspaces[0].id);
      }
    } else if (workspaces?.length === 0) {
      setActiveWorkspaceId(null);
      setSelectedMeetingId(null);
    }
  }, [workspaces, activeWorkspaceId, user, getToken, mutateWorkspaces]);

  const enterApprovedWorkspace = async (workspaceId: string) => {
    const available = await mutateWorkspaces();
    if (!available?.some(w => w.id === workspaceId)) throw new Error('Workspace access is not available. Ask your manager to confirm your membership.');
    setActiveWorkspaceId(workspaceId);
    setSelectedMeetingId(null);
    setActiveTab('dashboard');
    setJoinWorkspaceOpen(false);
  };

  const activeWorkspace = useMemo(
    () => workspaces?.find((w) => w.id === activeWorkspaceId) || workspaces?.[0],
    [workspaces, activeWorkspaceId]
  );
  const canManageWorkspace = isWorkspaceManager(activeWorkspace?.current_role);
  const isWorkspaceOwner = activeWorkspace?.current_role === 'owner';
  useEffect(() => {
    if (previousRole.current && previousRole.current !== activeWorkspace?.current_role) {
      // Remove results fetched with the old role before asking the API again.
      void mutateCache(key => typeof key === 'string' && (key.includes('/tasks') || key.includes('/chat') || key.includes('/search') || key.includes('/analytics')),
        undefined, { revalidate: true });
      setLocalChatMessages([]);
    }
    previousRole.current = activeWorkspace?.current_role;
  }, [activeWorkspace?.current_role, mutateCache]);
  const { data: pendingJoinRequests } = useSWR<JoinRequest[]>(
    canManageWorkspace && activeWorkspace ? `/api/v1/workspaces/${activeWorkspace.id}/join-requests` : null,
    path => apiFetch<JoinRequest[]>(path, {}, getToken), { refreshInterval: 15000 });

  const handleExploreDemo = async () => {
    setExploringDemo(true);
    try {
      const demo = await createDemoWorkspaceApi(getToken);
      await mutateWorkspaces();
      setActiveWorkspaceId(demo.id);
      setSelectedMeetingId(null);
      setActiveTab('dashboard');
      showToast('Sample workspace ready. Explore meetings, evidence and Ask MeetPilot.');
    } catch (err: any) {
      showToast(err.message || 'Could not open demo workspace', 'error');
    } finally { setExploringDemo(false); }
  };

  // Fetch workspace members, meetings, workspace tasks, and notifications
  const { data: members, mutate: mutateMembers } = useWorkspaceMembers(activeWorkspace?.id, getToken);
  const { data: meetings, error: meetingsError, isLoading: meetingsLoading, mutate: mutateMeetings } = useMeetings(activeWorkspace?.id, getToken);
  const { data: workspaceTaskRows, error: tasksError, isLoading: tasksLoading, mutate: mutateTasks } = useWorkspaceTasks(activeWorkspace?.id, getToken);
  const workspaceTasks = canManageWorkspace ? workspaceTaskRows : workspaceTaskRows?.filter(task => task.assignee_id === authSession?.user.id);
  const { data: integrations, mutate: mutateIntegrations } = useWorkspaceIntegrations(activeWorkspace?.id, getToken);
  const { data: workspaceAnalytics, mutate: mutateAnalytics } = useWorkspaceAnalytics(activeWorkspace?.id, getToken);
  const { data: workspaceDocs } = useWorkspaceDocuments(activeWorkspace?.id, getToken);
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
  const { data: meetingDetail, error: meetingError, isLoading: meetingLoading, mutate: mutateMeetingDetail } = useMeetingDetail(selectedMeetingId, getToken);
  const canManageMeeting = canManageWorkspace || Boolean(authSession?.user.id && meetingDetail?.created_by === authSession.user.id);
  const isMeetingProcessing = isProcessingStatus(meetingDetail?.status);
  const deferMeetingResults = isMeetingProcessing && meetingDetail?.source !== 'live';

  const { data: meetingSummary, mutate: mutateMeetingSummary } = useMeetingSummary(selectedMeetingId, deferMeetingResults, getToken);
  const { data: meetingTranscript, mutate: mutateMeetingTranscript } = useMeetingTranscript(selectedMeetingId, deferMeetingResults, getToken);
  const { data: meetingDecisions, mutate: mutateMeetingDecisions } = useMeetingDecisions(selectedMeetingId, deferMeetingResults, getToken);
  const { data: meetingTaskRows, mutate: mutateMeetingTasks } = useMeetingTasks(selectedMeetingId, deferMeetingResults, getToken);
  const meetingTasks = canManageWorkspace ? meetingTaskRows : meetingTaskRows?.filter(task => task.assignee_id === authSession?.user.id);
  const { data: serverChatHistory, mutate: mutateChat } = useMeetingChat(selectedMeetingId, getToken);

  const hasSavedMeetingData = Boolean(meetingTranscript?.length || meetingSummary || meetingDecisions?.length || meetingTasks?.length || meetingDetail?.audio_url);
  const showMeetingResults = meetingDetail?.status === 'completed' ||
    (meetingDetail?.source === 'live' && meetingDetail.status !== 'in_progress' && hasSavedMeetingData);

  useEffect(() => {
    if (meetingDetail?.status === 'completed') {
      void Promise.allSettled([mutateMeetingSummary(), mutateMeetingTranscript(), mutateMeetingDecisions(), mutateMeetingTasks()]);
    }
  }, [meetingDetail?.id, meetingDetail?.status, mutateMeetingSummary, mutateMeetingTranscript, mutateMeetingDecisions, mutateMeetingTasks]);

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
    setCurrentTime(seconds);
    setMeetingSubTab('transcript');
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
      const created = await uploadMeetingAudio(activeWorkspaceId, title, uploadFile, getToken, uploadLanguage);
      setUploadProgressMsg('Audio uploaded! Ingestion pipeline queued.');
      await mutateMeetings();
      setSelectedMeetingId(created.id);
      setUploadFile(null);
      setUploadTitle('');
      setUploadModalOpen(false);
      setActiveTab('meeting');
      setMeetingSubTab('summary');
      showToast(`"${title}" uploaded. Processing has started.`);
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
      await ensurePolicyAcceptance();
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

        const created = await uploadMeetingAudio(activeWorkspaceId, title, audioFile, getToken, uploadLanguage);
        await mutateMeetings();
        setSelectedMeetingId(created.id);
        setRecordModalOpen(false);
        setIsRecording(false);
        setLiveRecordTitle('');
        setRecordingSeconds(0);
        setActiveTab('meeting');
        setMeetingSubTab('summary');
        showToast(`"${title}" recorded and queued for transcription.`);
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
        md += `| ${t.title} | ${t.assignee_name || 'Unassigned'} | ${t.priority.toUpperCase()} | ${t.due_date || 'No deadline'} | ${t.status.toUpperCase()} |\n`;
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

  const handleEditSummary = async (overview: string) => {
    if (!selectedMeetingId) return;
    try {
      await updateMeetingSummaryApi(selectedMeetingId, { overview }, getToken);
      await mutateMeetingSummary();
      showToast('Summary updated');
    } catch (err: any) {
      showToast(err.message || 'Could not update summary', 'error');
      throw err;
    }
  };

  const handleEditDecision = async (decisionId: string, topic: string, outcome: string) => {
    if (!selectedMeetingId) return;
    try {
      await updateDecisionApi(selectedMeetingId, decisionId, { topic, outcome }, getToken);
      await mutateMeetingDecisions();
      showToast('Decision updated');
    } catch (err: any) {
      showToast(err.message || 'Could not update decision', 'error');
      throw err;
    }
  };

  const handleDeleteDecision = async (decisionId: string) => {
    if (!selectedMeetingId || !window.confirm('Remove this decision? The source transcript will remain.')) return;
    try {
      await deleteDecisionApi(selectedMeetingId, decisionId, getToken);
      await mutateMeetingDecisions();
      showToast('Decision removed');
    } catch (err: any) {
      showToast(err.message || 'Could not remove decision', 'error');
    }
  };

  const handleAddMeetingTask = async (title: string, assignee: string, priority: TaskPriority, dueDate: string) => {
    if (!activeWorkspaceId || !selectedMeetingId || !title.trim()) return;
    try {
      await createTaskApi(
        {
          title: title.trim(),
          workspace_id: activeWorkspaceId,
          meeting_id: selectedMeetingId,
          assignee_name: assignee.trim() || undefined,
          priority,
          due_date: dueDate || undefined,
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

  const handleEditTask = async (taskId: string, updates: { title: string; assignee_name: string | null; priority: TaskPriority; due_date: string | null }) => {
    try {
      await updateTaskApi(taskId, updates, getToken);
      await mutateTasks();
      await mutateMeetingTasks();
      showToast('Task updated');
    } catch (err: any) {
      showToast(err.message || 'Could not update task', 'error');
      throw err;
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

  const handleConnectIntegration = async (provider: 'google' | 'zoom') => {
    if (!activeWorkspaceId || !canManageWorkspace || !user?.id) return;
    try {
      await ensurePolicyAcceptance();
      const attempt = beginIntegrationOAuth(provider, activeWorkspaceId, user.id, getToken);
      integrationPopup.current = attempt.popup;
      await attempt.ready;
      showToast('Complete authorization in the connection window.', 'info');
    } catch (err) { showToast(err instanceof Error ? err.message : 'Could not start authorization.', 'error'); }
  };
  const handleConnectGoogleCalendar = () => handleConnectIntegration('google');
  const handleConnectZoom = () => handleConnectIntegration('zoom');
  useEffect(() => {
    const connected = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.source !== integrationPopup.current || event.data?.type !== 'meetpilot:integration-connected' || event.data.workspaceId !== activeWorkspaceId || !['google', 'zoom'].includes(event.data.provider)) return;
      void mutateIntegrations();
      showToast('Workspace integration connected.');
    };
    window.addEventListener('message', connected);
    return () => window.removeEventListener('message', connected);
  }, [activeWorkspaceId, mutateIntegrations]);

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
      showToast(`Zoom recording "${rec.topic}" queued for transcription.`);
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

  // 5b. Rename Workspace
  const handleRenameWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !workspaceRenameInput.trim()) return;

    setSavingWorkspaceName(true);
    try {
      const updated = await updateWorkspaceApi(activeWorkspace.id, { name: workspaceRenameInput.trim() }, getToken);
      showToast(`Workspace renamed to "${updated.name}"`);
      setEditingWorkspaceName(false);
      await mutateWorkspaces();
    } catch (err: any) {
      showToast(err.message || 'Failed to rename workspace', 'error');
    } finally {
      setSavingWorkspaceName(false);
    }
  };

  // 5c. Remove Member from Workspace
  const handleRemoveMember = async (userId: string, memberName: string) => {
    if (!activeWorkspace) return;
    if (!confirm(`Are you sure you want to remove ${memberName} from this workspace?`)) return;

    try {
      await removeWorkspaceMemberApi(activeWorkspace.id, userId, getToken);
      showToast(`Removed ${memberName} from workspace`);
      await mutateMembers();
    } catch (err: any) {
      showToast(err.message || 'Failed to remove member', 'error');
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
      due_date: quickTaskDueDate || null,
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

  if (!activeWorkspace) {
    return <WorkspaceOnboarding getToken={getToken} onEnter={enterApprovedWorkspace}
      loading={workspacesLoading || (!workspaces && !workspacesError)}
      loadError={workspacesError ? (workspacesError instanceof Error ? workspacesError.message : 'Could not load your workspaces') : undefined}
      onRetry={() => void mutateWorkspaces()} onBack={onBackToLanding} onSignOut={() => void signOut()} />;
  }

  return (
    <WorkspaceManagerContext.Provider value={canManageWorkspace}>
    <div className="mp-root">
      {activeTab === 'meeting' && meetingDetail && <MeetingPrintReport meeting={meetingDetail} summary={meetingSummary} decisions={meetingDecisions || []} tasks={meetingTasks || []} transcript={meetingTranscript || []} />}
      <WorkspaceShell activeTab={activeTab} onNavigate={setActiveTab} workspace={activeWorkspace}
        workspaces={workspaces || []} manager={canManageWorkspace}
        onSwitchWorkspace={id => { setSelectedMeetingId(null); setLocalChatMessages([]); setCurrentTime(0); setActiveWorkspaceId(id); setActiveTab('dashboard'); }}
        onCreateWorkspace={() => setNewWorkspaceModalOpen(true)} onJoinWorkspace={() => setJoinWorkspaceOpen(true)}
        onHome={onBackToLanding} onSignOut={() => void signOut()}
        onUpload={() => beginAction(() => setUploadModalOpen(true))} onRecord={() => { setRecordError(null); beginAction(() => setRecordModalOpen(true)); }}
        onJoinMeeting={() => beginAction(() => setLiveMeetModalOpen(true))} userName={user?.fullName || user?.firstName || 'Your account'}
        userEmail={user?.primaryEmailAddress?.emailAddress} avatarUrl={user?.imageUrl}
        pendingRequests={pendingJoinRequests?.length || 0} notificationCount={notifications?.length || 0}>
        {/* Central Workspace Canvas */}
        <main id="workspace-content" className="mp-workspace-content space-y-6">
          {canManageWorkspace && !!pendingJoinRequests?.length && activeTab !== 'team' && <div role="status" className="flex items-center justify-between rounded-xl border border-amber-500/30 bg-amber-50 p-4 text-sm text-amber-700"><span>{pendingJoinRequests.length} teammate request(s) waiting for your approval.</span><button onClick={() => setActiveTab('team')} className="rounded-lg bg-amber-700 px-3 py-2 text-on-brand">Review requests</button></div>}
          {activeTab === 'dashboard' && <WorkspaceOverview name={user?.firstName || 'there'}
            meetings={meetings || []} tasks={workspaceTasks || []} loading={meetingsLoading}
            error={meetingsError?.message} onRetry={() => void mutateMeetings()} manager={canManageWorkspace}
            isDemo={activeWorkspace.is_demo} onOpen={id => { setSelectedMeetingId(id); setActiveTab('meeting'); setMeetingSubTab('summary'); }}
            onNavigate={setActiveTab} onJoin={() => beginAction(() => setLiveMeetModalOpen(true))} onUpload={() => beginAction(() => setUploadModalOpen(true))}
            onDemo={handleExploreDemo} exploringDemo={exploringDemo} documentCount={workspaceDocs?.length || 0} memberCount={members?.length || 0} />}
          {activeTab === 'meetings' && <MeetingLibrary key={activeWorkspace.id} meetings={meetings || []}
            loading={meetingsLoading} error={meetingsError?.message} onRetry={() => void mutateMeetings()}
            manager={canManageWorkspace} actorId={authSession?.user.id} onDelete={handleDeleteMeeting}
            onOpen={id => { setSelectedMeetingId(id); setActiveTab('meeting'); setMeetingSubTab('summary'); setCurrentTime(0); }}
            onUpload={() => beginAction(() => setUploadModalOpen(true))} onJoin={() => beginAction(() => setLiveMeetModalOpen(true))} />}

          {/* TAB 2: MEETING INTELLIGENCE DETAIL */}
          {activeTab === 'meeting' && (
            <div className="space-y-6 animate-fadeIn">
              <button className="mp-text-button" onClick={() => setActiveTab('meetings')}><ArrowLeft size={15} />All meetings</button>
              {meetingLoading && <div className="mp-empty" role="status">Loading meeting...</div>}
              {meetingError && <div className="mp-error-state" role="alert"><p>{meetingError.message || 'Could not load meeting.'}</p><button className="mp-button mp-button-secondary" onClick={() => void mutateMeetingDetail()}>Try again</button></div>}
              {/* Empty state if no meetings exist */}
              {(!meetings || meetings.length === 0) && (
                <div className="p-12 rounded-xl bg-surface border border-dashed border-line text-center space-y-4 shadow-sm">
                  <FileText className="w-12 h-12 text-brand mx-auto " />
                  <h3 className="text-lg font-bold text-ink">No Meetings in this Workspace</h3>
                  <p className="text-sm text-muted max-w-md mx-auto">
                    Upload an MP3, WAV, or M4A recording to create a timestamped transcript, summary, tasks, and decisions. Review the results when processing finishes.
                  </p>
                  <div className="flex items-center justify-center gap-3">
                    <button
                      onClick={() => beginAction(() => setUploadModalOpen(true))}
                      className="px-5 py-2.5 rounded-xl bg-brand hover:bg-brand text-on-brand text-sm font-bold shadow-sm  inline-flex items-center gap-2 cursor-pointer"
                    >
                      <Upload className="w-4 h-4" />
                      <span>Upload Audio</span>
                    </button>
                    <button
                      onClick={() => beginAction(() => setLiveMeetModalOpen(true))}
                      className="px-5 py-2.5 rounded-xl bg-surface hover:bg-line text-ink text-sm font-bold border border-line inline-flex items-center gap-2 cursor-pointer"
                    >
                      <Video className="w-4 h-4" />
                      <span>Live meeting options</span>
                    </button>
                  </div>
                </div>
              )}

              {meetingDetail && (
                <MeetingScriptContext.Provider value={meetingDetail.display_script || 'original'}>
                  {/* Meeting Header */}
                  <MeetingHeader key={meetingDetail.id}
                    canManage={canManageMeeting}
                    meeting={meetingDetail}
                    allMeetings={meetings || []}
                    speakerStats={speakerStats}
                    onSelectMeeting={id => { setSelectedMeetingId(id); setCurrentTime(0); }}
                    onRenameMeeting={handleRenameMeeting}
                    onDeleteMeeting={handleDeleteMeeting}
                    onExportMarkdown={() => beginAction(handleExportMarkdown)}
                    onExportJSON={() => beginAction(handleExportJSON)}
                    onExportPDF={() => beginAction(handleExportPDF)}
                  />

                  <div className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-surface p-3 text-sm text-ink">
                    <span>Meeting language: {MEETING_LANGUAGES.find(([code]) => code === (meetingDetail.transcription_language || meetingDetail.language_code))?.[1] || meetingDetail.language_name || 'Auto-detect'}</span>
                    {['hi', 'bn', 'auto'].includes(meetingDetail.transcription_language || meetingDetail.language_code || '') && (
                      <label className="flex items-center gap-2">Display
                        <select aria-label="Meeting text display" value={meetingDetail.display_script || 'original'} disabled={savingDisplayScript || !canManageMeeting}
                          onChange={async event => {
                            const script = event.target.value as 'original' | 'romanized';
                            setSavingDisplayScript(true);
                            try {
                              await updateMeetingDisplayScript(meetingDetail.id, script, getToken);
                              await mutateMeetingDetail();
                            } catch (err) { showToast(err instanceof Error ? err.message : 'Could not change display', 'error'); }
                            finally { setSavingDisplayScript(false); }
                          }} className="rounded-lg border border-line bg-surface p-2 text-ink">
                          <option value="original">Original script</option>
                          <option value="romanized">{(meetingDetail.transcription_language || meetingDetail.language_code) === 'hi' ? 'Hinglish' : (meetingDetail.transcription_language || meetingDetail.language_code) === 'bn' ? 'Benglish' : 'Roman letters (Hindi / Bengali)'}</option>
                        </select>
                      </label>
                    )}
                    {meetingDetail.display_script === 'romanized' && <span className="text-muted">Roman spellings are approximate. Original quotes are preserved.</span>}
                  </div>

                  {meetingDetail.status === 'in_progress' && (
                    <>
                      <PilotVoicePanel key={meetingDetail.id} meetingId={meetingDetail.id} getToken={getToken} isLive={meetingDetail.source === 'live' && meetingDetail.status === 'in_progress'} />
                      <LiveInsights meetingId={meetingDetail.id} getToken={getToken} />
                    </>
                  )}

                  {canManageWorkspace && <MeetingIdentities key={meetingDetail.id} meetingId={meetingDetail.id} members={members || []} getToken={getToken} />}

                  {/* Meeting At A Glance Strip */}
                  {showMeetingResults && (
                    <MeetingAtAGlance
                      durationSeconds={meetingDetail.duration_seconds}
                      speakerStats={speakerStats}
                      decisionsCount={meetingDecisions?.length || 0}
                      tasksCount={meetingTasks?.length || 0}
                      completedTasksCount={meetingTasks?.filter((t) => t.status === 'done').length || 0}
                    />
                  )}

                  {/* Live Active Meeting View */}
                  {meetingDetail.status === 'in_progress' && authSession?.user.id && <MeetingBookmarks
                    key={`bookmarks-${meetingDetail.id}`} meetingId={meetingDetail.id} actorId={authSession.user.id}
                    getToken={getToken} position={Math.max(0, ...(meetingTranscript || []).map(s => s.end_time))}
                    hasTranscript={!!meetingTranscript?.length} isLive onSeek={handleSeekToTime} />}
                  {meetingDetail.status === 'in_progress' && (
                    <div className="p-6 rounded-xl bg-surface border border-rose-500/40 space-y-6 shadow-sm ">
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl bg-brand-soft border border-rose-500/30">
                        <div className="flex items-center gap-3">
                          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-700">
                            <Radio className="w-5 h-5 animate-pulse" />
                            <span className="absolute -top-1 -right-1 w-3 h-3 bg-rose-500 rounded-full border-2 border-[#111113] " />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="text-base font-bold text-ink">Live meeting</h3>
                              <span className="px-2 py-0.5 text-sm font-mono font-bold uppercase tracking-wider text-rose-700 bg-rose-50 border border-rose-500/40 rounded-md animate-pulse">
                                Live transcript
                              </span>
                            </div>
                            <p className="text-sm text-muted mt-0.5">
                              Meeting assistant is joining or connected ({meetingDetail.native_meeting_id || 'call'}). Speech turns stream into MeetPilot memory after capture begins.
                            </p>
                          </div>
                        </div>

                        <button
                          onClick={() => handleStopLiveMeeting(meetingDetail.id)}
                          disabled={stoppingLiveMeeting || !canManageMeeting}
                          className="px-5 py-2.5 rounded-xl bg-brand-soft text-ink text-sm font-bold shadow-sm  flex items-center gap-2 cursor-pointer transition-all active:scale-95 shrink-0"
                        >
                          {stoppingLiveMeeting ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              <span>Finishing meeting...</span>
                            </>
                          ) : (
                            <>
                              <Square className="w-4 h-4 fill-current" />
                              <span>End capture</span>
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
                  {isProcessingStatus(meetingDetail.status) && (
                    <ProcessingStateCard
                      status={meetingDetail.status}
                      meetingTitle={meetingDetail.title}
                      retryAvailable={meetingDetail.retry_available}
                      onRetry={handleRetryMeeting}
                    />
                  )}

                  {/* Failed Meeting Error Card */}
                  {meetingDetail.status === 'failed' && (
                    <MeetingErrorCard canManage={canManageMeeting}
                      meetingId={meetingDetail.id}
                      meetingTitle={meetingDetail.title}
                      failureReason={meetingDetail.failure_reason}
                      isLive={meetingDetail.source === 'live' && !hasSavedMeetingData && Boolean(meetingDetail.capture_failure_reason)}
                      onNewLiveMeeting={() => {
                        const code = meetingDetail.native_meeting_id;
                        setRetryLiveMeetingUrl(code && /^[a-z]{3}-[a-z]{4}-[a-z]{3}$/i.test(code)
                          ? `https://meet.google.com/${code}` : '');
                        beginAction(() => setLiveMeetModalOpen(true));
                      }}
                      onRetry={handleRetryMeeting}
                      onOpenUpload={() => beginAction(() => setUploadModalOpen(true))}
                      onDelete={() => handleDeleteMeeting(meetingDetail.id, meetingDetail.title)}
                    />
                  )}

                  {meetingDetail.capture_failure_reason && meetingDetail.status !== 'failed' && (
                    <div role="alert" className="rounded-xl border border-rose-500/30 bg-rose-50 p-4 text-sm text-rose-700">
                      <p className="font-semibold">Meeting capture was interrupted</p>
                      <p className="mt-1">The saved transcript and available analysis are shown below. Speech after the disconnection may be missing.</p>
                      <details className="mt-2 text-sm"><summary className="cursor-pointer">Connection details</summary>{meetingDetail.capture_failure_reason}</details>
                    </div>
                  )}

                  {/* Completed Meeting Intelligence Hub */}
                  {showMeetingResults && (
                    <div className="space-y-6">
                      {/* Interactive Audio Player */}
                      {selectedMeetingId && meetingDetail.audio_url && (
                        <MeetingAudioPlayer key={selectedMeetingId}
                          audioUrl={getAudioStreamUrl(selectedMeetingId)}
                          segments={meetingTranscript || []}
                          getToken={getToken}
                          fallbackDuration={meetingDetail.duration_seconds}
                          currentTime={currentTime}
                          onTimeUpdate={(t) => setCurrentTime(t)}
                          onSeek={handleSeekToTime}
                          audioRef={audioRef}
                        />
                      )}

                      {/* Sub-Tab Navigation Strip */}
                      <div className="flex items-center gap-2 p-1.5 rounded-xl bg-surface border border-line overflow-x-auto">
                        <button
                          onClick={() => setMeetingSubTab('summary')}
                          className={`px-4 py-2 rounded-xl text-sm font-bold transition-all cursor-pointer flex items-center gap-2 ${
                            meetingSubTab === 'summary'
                              ? 'bg-brand text-on-brand shadow-sm '
                              : 'text-muted hover:text-ink hover:bg-surface'
                          }`}
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>Summary & decisions</span>
                        </button>

                        <button
                          onClick={() => setMeetingSubTab('transcript')}
                          className={`px-4 py-2 rounded-xl text-sm font-bold transition-all cursor-pointer flex items-center gap-2 ${
                            meetingSubTab === 'transcript'
                              ? 'bg-brand text-on-brand shadow-sm '
                              : 'text-muted hover:text-ink hover:bg-surface'
                          }`}
                        >
                          <FileText className="w-3.5 h-3.5" />
                          <span>Transcript ({meetingTranscript?.length || 0})</span>
                        </button>

                        <button
                          onClick={() => setMeetingSubTab('tasks')}
                          className={`px-4 py-2 rounded-xl text-sm font-bold transition-all cursor-pointer flex items-center gap-2 ${
                            meetingSubTab === 'tasks'
                              ? 'bg-brand text-on-brand shadow-sm '
                              : 'text-muted hover:text-ink hover:bg-surface'
                          }`}
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Action Items ({meetingTasks?.length || 0})</span>
                        </button>

                        <button
                          onClick={() => setMeetingSubTab('chat')}
                          className={`px-4 py-2 rounded-xl text-sm font-bold transition-all cursor-pointer flex items-center gap-2 ${
                            meetingSubTab === 'chat'
                              ? 'bg-brand text-on-brand shadow-sm '
                              : 'text-muted hover:text-ink hover:bg-surface'
                          }`}
                        >
                          <Bot className="w-3.5 h-3.5 text-brand" />
                          <span>Ask this meeting</span>
                        </button>
                        {authSession?.user.id && <button onClick={() => setMeetingSubTab('review')}
                          className={`px-4 py-2 rounded-xl text-sm font-bold ${meetingSubTab === 'review' ? 'bg-brand text-on-brand' : 'text-muted hover:text-ink'}`}>Review tools</button>}
                      </div>

                      {meetingSubTab === 'review' && authSession?.user.id && <MeetingReviewTools key={`${meetingDetail.id}:${authSession.user.id}`}
                        meetingId={meetingDetail.id} workspaceId={meetingDetail.workspace_id}
                        actorId={authSession.user.id} getToken={getToken} currentTime={currentTime}
                        segments={meetingTranscript || []} onSeek={handleSeekToTime} />}

                      {/* Sub-Tab 1: Executive Intelligence & Decisions */}
                      {meetingSubTab === 'summary' && (
                        <ExecutiveIntelligence
                          summary={meetingSummary}
                          decisions={meetingDecisions || []}
                          onSeek={handleSeekToTime}
                          onEditSummary={handleEditSummary}
                          onEditDecision={handleEditDecision}
                          onDeleteDecision={handleDeleteDecision}
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
                          members={members || []}
                          onUpdateTask={handleEditTask}
                        />
                      )}

                      {/* Sub-Tab 4: Ask this meeting */}
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
                </MeetingScriptContext.Provider>
              )}
            </div>
          )}

          {activeTab === 'kanban' && <WorkspaceTaskBoard key={activeWorkspace.id} tasks={workspaceTasks || []}
            meetings={meetings || []} members={members || []} manager={canManageWorkspace} loading={tasksLoading}
            error={tasksError?.message} onRetry={() => void mutateTasks()} onDelete={handleDeleteTask}
            onStatus={handleTaskStatusChange} onOpenMeeting={id => { setSelectedMeetingId(id); setActiveTab('meeting'); setMeetingSubTab('tasks'); }}
            onCreate={async draft => { if (!canManageWorkspace) return; await createTaskApi({ ...draft, workspace_id: activeWorkspace.id, status: 'todo' }, getToken); await Promise.all([mutateTasks(), mutateMeetings()]); showToast('Action item created.'); }} />}

          {/* TAB: AI KNOWLEDGE / RAG */}
          {activeTab === 'knowledge' && (
            <div className="h-full flex-1 flex flex-col min-h-0 animate-fadeIn">
              <AIKnowledgeView
                key={activeWorkspace?.id}
                activeWorkspace={activeWorkspace}
                getToken={getToken}
                onNavigateToMeeting={(meetingId, ts) => {
                  setSelectedMeetingId(meetingId);
                  setActiveTab('meeting');
                  setCurrentTime(ts || 0);
                  setMeetingSubTab(ts !== undefined ? 'transcript' : 'summary');
                }}
                showToast={showToast}
              />
            </div>
          )}

          {/* TAB: WORKSPACE SEMANTIC SEARCH */}
          {activeTab === 'search' && (
            <div className="h-full flex-1 flex flex-col min-h-0 animate-fadeIn">
              <WorkspaceSemanticSearch
                activeWorkspace={activeWorkspace}
                getToken={getToken}
                onNavigateToMeeting={(meetingId, ts) => {
                  setSelectedMeetingId(meetingId);
                  setActiveTab('meeting');
                  setCurrentTime(ts || 0);
                  setMeetingSubTab(ts !== undefined ? 'transcript' : 'summary');
                }}
                onNavigateToTab={tab => { if (tab === 'kanban') setActiveTab('kanban'); }}
                showToast={showToast}
              />
            </div>
          )}

          {/* TAB 5: ANALYTICS */}
          {activeTab === 'analytics' && (
            <div className="space-y-6 animate-fadeIn">
              <div>
                <h2 className="text-2xl font-semibold text-ink">Workspace Analytics</h2>
                <p className="text-sm text-muted mt-0.5">A workspace view of meeting duration, decisions and action-item progress.</p>
              </div>

              {/* 4-Card Executive Metric Strip */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-surface border border-line space-y-1">
                  <div className="text-sm font-mono uppercase text-muted">Total Meetings</div>
                  <div className="text-2xl font-semibold text-ink font-mono">
                    {workspaceAnalytics?.total_meetings ?? meetings?.length ?? 0}
                  </div>
                  <div className="text-sm text-emerald-700 font-mono">
                    {workspaceAnalytics?.completed_meetings ?? 0} completed &bull; {workspaceAnalytics?.processing_meetings ?? 0} in pipeline
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-surface border border-line space-y-1">
                  <div className="text-sm font-mono uppercase text-muted">Meeting duration</div>
                  <div className="text-2xl font-semibold text-brand font-mono">
                    {workspaceAnalytics?.total_speaking_hours ?? 0} hrs
                  </div>
                  <div className="text-sm text-muted font-mono">
                    Avg {workspaceAnalytics?.avg_meeting_duration_minutes ?? 0}m per meeting
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-surface border border-line space-y-1">
                  <div className="text-sm font-mono uppercase text-muted">Decisions Reached</div>
                  <div className="text-2xl font-semibold text-sky-700 font-mono">
                    {workspaceAnalytics?.total_decisions ?? 0}
                  </div>
                  <div className="text-sm text-muted font-mono">
                    Consensus points recorded
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-surface border border-line space-y-1">
                  <div className="text-sm font-mono uppercase text-muted">Task Completion</div>
                  <div className="text-2xl font-semibold text-emerald-700 font-mono">
                    {workspaceAnalytics?.task_completion_rate ?? 0}%
                  </div>
                  <div className="text-sm text-muted font-mono">
                    {workspaceAnalytics?.completed_tasks ?? tasksByStatus.done.length} of {workspaceAnalytics?.total_tasks ?? workspaceTasks?.length ?? 0} items resolved
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Speaking Time Distribution */}
                <div className="p-6 rounded-xl bg-surface border border-line space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-ink uppercase tracking-wider">
                      Speaker Airtime Distribution
                    </h3>
                    <span className="text-sm font-mono text-muted">Workspace Aggregate</span>
                  </div>

                  {workspaceAnalytics?.speakers_distribution && workspaceAnalytics.speakers_distribution.length > 0 ? (
                    <div className="space-y-3 pt-2">
                      {workspaceAnalytics.speakers_distribution.map((stat, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span className="text-ink font-semibold">{stat.speaker}</span>
                            <span className="text-brand font-mono font-bold">
                              {stat.percentage}% ({Math.round(stat.duration_seconds / 60)} min &bull; {stat.turn_count} turns)
                            </span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-surface overflow-hidden">
                            <div className="h-full bg-brand" style={{ width: `${stat.percentage}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : analyticsSpeakerStats.length > 0 ? (
                    <div className="space-y-3 pt-2">
                      {analyticsSpeakerStats.map((stat, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between text-sm">
                            <span className="text-ink font-semibold">{stat.speaker}</span>
                            <span className="text-brand font-mono font-bold">
                              {stat.percentage}% ({stat.hours} hrs)
                            </span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-surface overflow-hidden">
                            <div className="h-full bg-brand" style={{ width: `${stat.percentage}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted italic">No diarized audio segments recorded in this workspace yet.</p>
                  )}
                </div>

                {/* Action Item Breakdown */}
                <div className="p-6 rounded-xl bg-surface border border-line space-y-4">
                  <h3 className="text-sm font-bold text-ink uppercase tracking-wider">Action Items & Kanban State</h3>
                  <div className="space-y-3 pt-2">
                    <div className="flex items-center justify-between text-sm p-3 rounded-xl bg-surface border border-line">
                      <span className="text-ink">Total Action Items</span>
                      <span className="font-mono font-bold text-ink">{workspaceAnalytics?.total_tasks ?? workspaceTasks?.length ?? 0}</span>
                    </div>

                    <div className="flex items-center justify-between text-sm p-3 rounded-xl bg-surface border border-line">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-400" />
                        <span className="text-ink">Completed (Done)</span>
                      </div>
                      <span className="font-mono font-bold text-emerald-700">{workspaceAnalytics?.completed_tasks ?? tasksByStatus.done.length}</span>
                    </div>

                    <div className="flex items-center justify-between text-sm p-3 rounded-xl bg-surface border border-line">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-brand" />
                        <span className="text-ink">In Progress (Doing)</span>
                      </div>
                      <span className="font-mono font-bold text-brand">{workspaceAnalytics?.in_progress_tasks ?? tasksByStatus.doing.length}</span>
                    </div>

                    <div className="flex items-center justify-between text-sm p-3 rounded-xl bg-surface border border-line">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-amber-400" />
                        <span className="text-ink">To Do</span>
                      </div>
                      <span className="font-mono font-bold text-amber-700">{workspaceAnalytics?.todo_tasks ?? tasksByStatus.todo.length}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: TEAM MEMBERS */}
          {activeTab === 'team' && (
            <div className="space-y-6 animate-fadeIn">
              {activeWorkspace && <WorkspaceAccessPanel key={activeWorkspace.id} workspace={activeWorkspace} members={members || []} getToken={getToken} onChange={async () => { await Promise.all([mutateMembers(), mutateWorkspaces()]); }} />}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-semibold text-ink">{activeWorkspace?.name || 'Workspace'} Members</h2>
                  <p className="text-sm text-muted mt-0.5">Manage team access and permissions.</p>
                </div>
                <button
                  disabled={!canManageWorkspace}
                  onClick={() => setInviteModalOpen(true)}
                  className="px-4 py-2 rounded-xl bg-brand hover:bg-brand text-on-brand text-sm font-bold cursor-pointer shadow-sm "
                >
                  + Invite Teammate
                </button>
              </div>

              <div className="p-6 rounded-xl bg-surface border border-line space-y-4">
                <h3 className="text-sm font-bold text-ink uppercase tracking-wider">
                  Active Workspace Members ({members?.length || 1})
                </h3>

                <div className="space-y-3">
                  {members?.map((m) => (
                    <div
                      key={m.user_id}
                      className="p-4 rounded-xl bg-surface border border-line flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3">
                        <img
                          src={getAvatar(m.name, m.avatar_url)}
                          alt={m.name}
                          className="w-9 h-9 rounded-full object-cover"
                        />
                        <div>
                          <div className="text-sm font-bold text-ink">{m.name}</div>
                          <div className="text-sm text-muted">{m.email}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-mono px-2.5 py-1 rounded bg-brand/20 text-brand font-bold uppercase">
                          {m.role}
                        </span>
                        {canManageWorkspace && m.role !== 'owner' && (isWorkspaceOwner || m.role !== 'admin') && (
                          <button
                            onClick={() => handleRemoveMember(m.user_id, m.name)}
                            title="Remove member from workspace"
                            className="p-1.5 rounded-lg text-muted hover:text-rose-700 hover:bg-rose-50 transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: INTEGRATIONS */}
          {activeTab === 'integrations' && !canManageWorkspace && <p className="text-sm text-muted">Workspace integrations are managed by your manager.</p>}
          {activeTab === 'integrations' && canManageWorkspace && (
            <div className="space-y-6 animate-fadeIn">
              <div>
                <h2 className="text-2xl font-semibold text-ink">Workspace Integrations</h2>
                <p className="text-sm text-muted mt-0.5">Connect your calendar, import Zoom recordings or send meeting digests to Discord.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* 1. Discord Integration Card */}
                {(() => {
                  const discord = integrations?.find((i) => i.provider === 'discord');
                  const isConn = discord?.is_connected;
                  return (
                    <div className="p-6 rounded-xl bg-surface border border-line space-y-4 flex flex-col justify-between">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-xl bg-[#5865F2]/20 border border-[#5865F2]/40 flex items-center justify-center text-[#5865F2] font-bold">
                              #
                            </div>
                            <div>
                              <div className="text-sm font-semibold text-ink">Discord Webhook</div>
                              <div className="text-sm font-mono text-muted">Digest Bot</div>
                            </div>
                          </div>

                          <span
                            className={`px-2.5 py-0.5 rounded-full text-sm font-mono font-bold flex items-center gap-1.5 ${
                              isConn
                                ? 'bg-emerald-500/20 text-emerald-700 border border-emerald-500/30'
                                : 'bg-surface text-muted border border-line'
                            }`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${isConn ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                            {isConn ? 'Connected' : 'Not Connected'}
                          </span>
                        </div>

                        <p className="text-sm text-ink leading-relaxed">
                          Automatically broadcasts an executive digest (meeting overview, key takeaways, and top action items) to your team's Discord channel when a meeting completes.
                        </p>

                        {isConn && discord?.masked_identifier && (
                          <div className="p-2.5 rounded-xl bg-surface border border-line text-sm font-mono text-muted truncate">
                            Webhook: <span className="text-emerald-700">{discord.masked_identifier}</span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2 pt-2 border-t border-line">
                        <button
                          onClick={() => {
                            setDiscordWebhookInput('');
                            setDiscordModalOpen(true);
                          }}
                          className="px-4 py-2 rounded-xl text-sm font-bold bg-brand hover:bg-brand text-on-brand transition-colors cursor-pointer shadow-sm "
                        >
                          {isConn ? 'Update Webhook' : 'Configure Discord'}
                        </button>

                        {isConn && (
                          <button
                            onClick={() => handleDisconnectIntegration('discord', 'Discord Webhook')}
                            className="px-3.5 py-2 rounded-xl text-sm font-bold text-rose-700 hover:text-rose-700 hover:bg-rose-50 border border-rose-500/30 transition-colors cursor-pointer"
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
                    <div className="p-6 rounded-xl bg-surface border border-line space-y-4 flex flex-col justify-between">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-xl bg-blue-500/20 border border-blue-500/40 flex items-center justify-center text-blue-700 font-bold">
                              <Calendar className="w-4 h-4" />
                            </div>
                            <div>
                              <div className="text-sm font-semibold text-ink">Google Calendar</div>
                              <div className="text-sm font-mono text-muted">Event Sync</div>
                            </div>
                          </div>

                          <span
                            className={`px-2.5 py-0.5 rounded-full text-sm font-mono font-bold flex items-center gap-1.5 ${
                              isConn
                                ? 'bg-emerald-500/20 text-emerald-700 border border-emerald-500/30'
                                : 'bg-surface text-muted border border-line'
                            }`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${isConn ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                            {isConn ? 'Connected' : 'Not Connected'}
                          </span>
                        </div>

                        <p className="text-sm text-ink leading-relaxed">
                          Automatically synchronizes detected action items with assigned due dates into Google Calendar events with direct links to the meeting audio timestamp.
                        </p>

                        {isConn && gcal?.masked_identifier && (
                          <div className="p-2.5 rounded-xl bg-surface border border-line text-sm font-mono text-muted truncate">
                            Account: <span className="text-blue-700">{gcal.masked_identifier}</span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2 pt-2 border-t border-line">
                        <button
                          onClick={handleConnectGoogleCalendar}
                          className="px-4 py-2 rounded-xl text-sm font-bold bg-brand hover:bg-brand text-on-brand transition-colors cursor-pointer shadow-sm "
                        >
                          {isConn ? 'Reconnect Calendar' : 'Connect Google Calendar'}
                        </button>

                        {isConn && (
                          <button
                            onClick={() => handleDisconnectIntegration('google_calendar', 'Google Calendar')}
                            className="px-3.5 py-2 rounded-xl text-sm font-bold text-rose-700 hover:text-rose-700 hover:bg-rose-50 border border-rose-500/30 transition-colors cursor-pointer"
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
                    <div className="p-6 rounded-xl bg-surface border border-line space-y-4 flex flex-col justify-between">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-xl bg-sky-500/20 border border-sky-500/40 flex items-center justify-center text-sky-700 font-bold">
                              <Radio className="w-4 h-4" />
                            </div>
                            <div>
                              <div className="text-sm font-semibold text-ink">Zoom Cloud Recordings</div>
                              <div className="text-sm font-mono text-muted">1-Click Importer</div>
                            </div>
                          </div>

                          <span
                            className={`px-2.5 py-0.5 rounded-full text-sm font-mono font-bold flex items-center gap-1.5 ${
                              isConn
                                ? 'bg-emerald-500/20 text-emerald-700 border border-emerald-500/30'
                                : 'bg-surface text-muted border border-line'
                            }`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${isConn ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                            {isConn ? 'Connected' : 'Not Connected'}
                          </span>
                        </div>

                        <p className="text-sm text-ink leading-relaxed">
                          Fetch and browse Zoom cloud audio/video recordings. Import any recording directly into MeetPilot AI for speech diarization and summary extraction.
                        </p>

                        {isConn && zoom?.masked_identifier && (
                          <div className="p-2.5 rounded-xl bg-surface border border-line text-sm font-mono text-muted truncate">
                            Status: <span className="text-sky-700">{zoom.masked_identifier}</span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2 pt-2 border-t border-line">
                        {isConn ? (
                          <>
                            <button
                              onClick={handleOpenZoomPicker}
                              className="px-4 py-2 rounded-xl text-sm font-bold bg-brand hover:bg-brand text-on-brand transition-colors cursor-pointer shadow-sm "
                            >
                              Browse Recordings
                            </button>
                            <button
                              onClick={() => handleDisconnectIntegration('zoom', 'Zoom Account')}
                              className="px-3.5 py-2 rounded-xl text-sm font-bold text-rose-700 hover:text-rose-700 hover:bg-rose-50 border border-rose-500/30 transition-colors cursor-pointer"
                            >
                              Disconnect
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={handleConnectZoom}
                            className="px-4 py-2 rounded-xl text-sm font-bold bg-brand hover:bg-brand text-on-brand transition-colors cursor-pointer shadow-sm "
                          >
                            Connect Zoom Account
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })()}

                {/* Workspace task board */}
                <div className="p-6 rounded-xl bg-surface border border-line space-y-4 flex flex-col justify-between">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-xl bg-brand/20 border border-brand/40 flex items-center justify-center text-brand font-bold">
                          <Kanban className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-ink">Workspace Tasks</div>
                          <div className="text-sm font-mono text-muted">Meeting follow-up</div>
                        </div>
                      </div>

                      <span className="px-2.5 py-0.5 rounded-full text-sm font-mono font-bold bg-surface text-muted border border-line">
                        Available
                      </span>
                    </div>

                    <p className="text-sm text-ink leading-relaxed">
                      Review extracted action items, correct owners and due dates, and track progress on the workspace board.
                    </p>
                  </div>

                  <div className="flex items-center gap-2 pt-2 border-t border-line">
                    <button
                      onClick={() => setActiveTab('kanban')}
                      className="px-4 py-2 rounded-xl text-sm font-bold bg-surface hover:bg-line text-ink border border-line transition-colors cursor-pointer"
                    >
                      Open Task Board
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
                <h2 className="text-2xl font-semibold text-ink">Notifications & Activity</h2>
                <p className="text-sm text-muted mt-0.5">Live events generated during meeting processing.</p>
              </div>

              <div className="p-6 rounded-xl bg-surface border border-line space-y-3">
                {notifications && notifications.length > 0 ? (
                  notifications.map((n) => (
                    <div key={n.id} className="p-4 rounded-xl bg-surface border border-line flex items-center justify-between">
                      <div>
                        <div className="text-sm font-bold text-ink flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-brand" />
                          <span>{n.message}</span>
                        </div>
                        <div className="text-sm text-muted font-mono mt-0.5 ml-4">
                          Type: {n.type}
                        </div>
                      </div>
                      <span className="text-sm font-mono text-muted">{formatMeetingDate(n.created_at)}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted italic text-center py-6">No recent notifications.</p>
                )}
              </div>
            </div>
          )}

          {/* TAB 9: SETTINGS */}
          {activeTab === 'settings' && (
            <div className="space-y-6 animate-fadeIn">
              <div>
                <h2 className="text-2xl font-semibold text-ink">Workspace Settings</h2>
                <p className="text-sm text-muted mt-0.5">Manage your authenticated profile and workspace configuration.</p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-4 p-4 rounded-xl bg-surface border border-line space-y-1">
                  <button
                    onClick={() => setSettingsTab('profile')}
                    className={`w-full text-left px-3.5 py-2.5 rounded-xl text-sm font-bold transition-colors cursor-pointer ${
                      settingsTab === 'profile' ? 'bg-brand text-on-brand' : 'text-muted hover:text-ink'
                    }`}
                  >
                    User Profile
                  </button>

                  <button
                    onClick={() => setSettingsTab('workspace')}
                    className={`w-full text-left px-3.5 py-2.5 rounded-xl text-sm font-bold transition-colors cursor-pointer ${
                      settingsTab === 'workspace' ? 'bg-brand text-on-brand' : 'text-muted hover:text-ink'
                    }`}
                  >
                    Workspace Details
                  </button>

                  <button onClick={() => setSettingsTab('voice')}
                    className={`w-full text-left px-3.5 py-2.5 rounded-xl text-sm font-bold transition-colors cursor-pointer ${settingsTab === 'voice' ? 'bg-brand text-on-brand' : 'text-muted hover:text-ink'}`}>
                    Bot Voice
                  </button>
                  <button onClick={() => setSettingsTab('appearance')}
                    className={`w-full text-left px-3.5 py-2.5 rounded-xl text-sm font-bold transition-colors cursor-pointer ${settingsTab === 'appearance' ? 'bg-brand text-on-brand' : 'text-muted hover:text-ink'}`}>
                    Appearance
                  </button>
                  <LegalSettings />
                </div>

                <div className="lg:col-span-8 p-6 rounded-xl bg-surface border border-line space-y-6">
                  {settingsTab === 'appearance' && <AppearanceSettings />}
                  {settingsTab === 'profile' && (
                    <div className="space-y-4">
                      <h3 className="text-sm font-bold text-ink uppercase tracking-wider">Profile Information</h3>
                      <div className="space-y-3 text-sm">
                        <div>
                          <span className="text-muted font-mono">Full Name:</span>
                          <div className="text-ink font-bold mt-1">{user?.fullName || user?.firstName || 'User'}</div>
                        </div>
                        <div>
                          <span className="text-muted font-mono">Primary Email:</span>
                          <div className="text-ink font-bold mt-1">{user?.primaryEmailAddress?.emailAddress}</div>
                        </div>
                        <div>
                          <span className="text-muted font-mono">Account reference:</span>
                          <div className="text-muted font-mono text-sm mt-1">{user?.id}</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {settingsTab === 'voice' && activeWorkspace && (
                    canManageWorkspace ? <PilotVoiceSettings key={activeWorkspace.id} workspaceId={activeWorkspace.id} getToken={getToken} /> : <p className="text-sm text-muted">Your manager chooses the workspace bot voice.</p>
                  )}

                  {settingsTab === 'workspace' && (
                    <div className="space-y-6">
                      <div className="space-y-4">
                        <h3 className="text-sm font-bold text-ink uppercase tracking-wider">Workspace Information</h3>
                        <div className="space-y-3 text-sm">
                          <div>
                            <span className="text-muted font-mono">Workspace ID:</span>
                            <div className="text-muted font-mono text-sm mt-1">{activeWorkspace?.id}</div>
                          </div>
                          <div>
                            <span className="text-muted font-mono">Workspace Name:</span>
                            {editingWorkspaceName ? (
                              <form onSubmit={handleRenameWorkspace} className="flex items-center gap-2 mt-1">
                                <input
                                  type="text"
                                  value={workspaceRenameInput}
                                  onChange={(e) => setWorkspaceRenameInput(e.target.value)}
                                  className="px-3 py-1.5 rounded-lg bg-surface border border-brand text-sm text-ink focus:outline-none"
                                  autoFocus
                                />
                                <button
                                  type="submit"
                                  disabled={savingWorkspaceName}
                                  className="px-3 py-1.5 rounded-lg bg-brand hover:bg-brand text-on-brand text-sm font-bold transition-colors cursor-pointer"
                                >
                                  {savingWorkspaceName ? 'Saving...' : 'Save'}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setEditingWorkspaceName(false)}
                                  className="px-3 py-1.5 rounded-lg bg-line hover:bg-line text-ink text-sm transition-colors cursor-pointer"
                                >
                                  Cancel
                                </button>
                              </form>
                            ) : (
                              <div className="flex items-center gap-2 mt-1">
                                <span className="text-ink font-bold">{activeWorkspace?.name}</span>
                                <button
                                  disabled={!canManageWorkspace}
                                  onClick={() => {
                                    setWorkspaceRenameInput(activeWorkspace?.name || '');
                                    setEditingWorkspaceName(true);
                                  }}
                                  className="text-sm text-brand hover:underline font-mono cursor-pointer"
                                >
                                  Rename
                                </button>
                              </div>
                            )}
                          </div>
                          <div>
                            <span className="text-muted font-mono">Total Meetings:</span>
                            <div className="text-ink font-bold mt-1">{meetings?.length || 0} recording(s)</div>
                          </div>
                          <div>
                            <span className="text-muted font-mono">Team Members:</span>
                            <div className="text-ink font-bold mt-1">{members?.length || 0} member(s)</div>
                          </div>
                        </div>
                      </div>

                      {/* Danger Zone: Delete Workspace */}
                      {activeWorkspace && isWorkspaceOwner && (
                        <div className="pt-6 border-t border-line space-y-3">
                          <div className="p-4 rounded-xl border border-red-500/30 bg-red-50 space-y-3">
                            <div className="flex items-center gap-2 text-red-700">
                              <AlertCircle className="w-4 h-4" />
                              <h4 className="text-sm font-bold uppercase tracking-wider">Danger Zone</h4>
                            </div>
                            <p className="text-sm text-ink">
                              Permanently delete <span className="font-bold text-ink">"{activeWorkspace.name}"</span> and all associated recordings, audio files, diarized transcripts, and action items. This destructive action cannot be undone.
                            </p>
                            <div className="pt-1">
                              <button
                                onClick={() => {
                                  setDeleteConfirmText('');
                                  setDeleteWorkspaceError(null);
                                  setDeleteWorkspaceModalOpen(true);
                                }}
                                className="px-4 py-2 rounded-xl bg-red-600/90 hover:bg-red-600 text-ink text-sm font-bold flex items-center gap-2 cursor-pointer transition-colors shadow-sm "
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



                </div>
              </div>
            </div>
          )}
        </main>
      </WorkspaceShell>

      {/* MODALS */}

      {/* 1. Quick Upload Modal */}
      {uploadModalOpen && (
        <Modal label="Upload a meeting recording" onClose={() => setUploadModalOpen(false)} busy={uploading}>
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-ink">Upload Meeting Audio</h3>
            <p className="text-sm text-muted">
              Add a recording to create a transcript, summary and action items linked to the conversation.
            </p>

            <form onSubmit={handleUploadMeeting} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-mono text-muted">Meeting Title</label>
                <input
                  type="text"
                  placeholder="e.g. Q3 Architecture & Security Review"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  className="w-full bg-surface border border-line rounded-xl px-3.5 py-2 text-sm text-ink placeholder-slate-500 focus:outline-none focus:border-brand"
                />
              </div>

              <MeetingLanguageSelect value={uploadLanguage} onChange={setUploadLanguage} disabled={uploading} />
              <div className="space-y-1.5">
                <label className="text-sm font-mono text-muted">Select Audio File</label>
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
                  className="w-full text-sm text-muted file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-brand file:text-ink hover:file:bg-brand cursor-pointer"
                />
              </div>

              {uploadProgressMsg && (
                <div className="flex items-center gap-2 text-sm text-brand font-mono">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>{uploadProgressMsg}</span>
                </div>
              )}

              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setUploadModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-surface hover:bg-line text-sm font-bold text-muted transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!uploadFile || uploading}
                  className="px-5 py-2 rounded-xl bg-brand hover:bg-brand disabled:opacity-40 text-sm font-bold text-on-brand transition-colors cursor-pointer shadow-sm "
                >
                  {uploading ? 'Uploading...' : 'Upload & Process'}
                </button>
              </div>
            </form>
          </div>
        </Modal>
      )}

      {/* Live In-Browser Microphone Recording Modal */}
      {recordModalOpen && (
        <Modal label="Record a meeting" onClose={() => setRecordModalOpen(false)} busy={isRecording || submittingRecording}>
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2.5 text-rose-700 font-bold text-sm">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 " />
                <Mic className="w-4 h-4 text-rose-700" />
                <h3 className="text-ink font-semibold text-base">In-Browser Live Mic Recording</h3>
              </div>
              <span className="text-sm font-mono uppercase text-muted px-2 py-0.5 rounded bg-surface">
                MediaRecorder
              </span>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-mono text-muted">Meeting / Session Title</label>
                <input
                  type="text"
                  placeholder="e.g. Daily Standup / Customer Discovery"
                  value={liveRecordTitle}
                  onChange={(e) => setLiveRecordTitle(e.target.value)}
                  disabled={isRecording}
                  className="w-full bg-surface border border-line rounded-xl px-3.5 py-2 text-sm text-ink placeholder-slate-500 focus:outline-none focus:border-brand"
                />
              </div>

              <MeetingLanguageSelect value={uploadLanguage} onChange={setUploadLanguage} disabled={isRecording || submittingRecording} />
              {/* Live Waveform & Timer Banner */}
              <div className="p-6 rounded-xl bg-surface border border-line text-center space-y-3">
                <div className="text-3xl font-semibold font-mono tracking-wider text-ink">
                  {formatTimestampSeconds(recordingSeconds)}
                </div>

                {isRecording ? (
                  <div className="flex items-center justify-center gap-1.5 py-2">
                    <div className="w-1.5 h-6 bg-rose-500 rounded-full " style={{ animationDelay: '0ms' }} />
                    <div className="w-1.5 h-10 bg-rose-400 rounded-full " style={{ animationDelay: '150ms' }} />
                    <div className="w-1.5 h-7 bg-rose-500 rounded-full " style={{ animationDelay: '300ms' }} />
                    <div className="w-1.5 h-12 bg-brand rounded-full " style={{ animationDelay: '450ms' }} />
                    <div className="w-1.5 h-8 bg-rose-400 rounded-full " style={{ animationDelay: '200ms' }} />
                    <div className="w-1.5 h-5 bg-rose-500 rounded-full " style={{ animationDelay: '100ms' }} />
                  </div>
                ) : (
                  <p className="text-sm text-muted">
                    Click "Start Recording" to capture audio directly through your microphone.
                  </p>
                )}

                {isRecording && (
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/10 text-rose-700 text-sm font-mono">
                    <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                    <span>Capturing live microphone audio stream...</span>
                  </div>
                )}
              </div>

              {recordError && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-500/40 text-sm text-rose-700 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-700 shrink-0" />
                  <span>{recordError}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={cancelLiveRecording}
                  className="px-4 py-2 rounded-xl bg-surface hover:bg-line text-sm font-bold text-muted hover:text-ink transition-colors cursor-pointer"
                >
                  Cancel
                </button>

                {!isRecording ? (
                  <button
                    type="button"
                    onClick={startLiveRecording}
                    disabled={submittingRecording}
                    className="px-5 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-sm font-bold text-on-brand transition-colors cursor-pointer shadow-sm  flex items-center gap-2"
                  >
                    <Radio className="w-3.5 h-3.5" />
                    <span>Start Recording</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={stopAndSubmitRecording}
                    disabled={submittingRecording}
                    className="px-5 py-2 rounded-xl bg-brand hover:bg-brand disabled:opacity-50 text-sm font-bold text-on-brand transition-colors cursor-pointer shadow-sm  flex items-center gap-2"
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
        </Modal>
      )}


      {/* 2. Create Workspace Modal */}
      {newWorkspaceModalOpen && (
        <Modal label="Create workspace" onClose={() => setNewWorkspaceModalOpen(false)} busy={creatingWorkspace}>
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-ink">Create New Workspace</h3>
            <p className="text-sm text-muted">Isolate meetings, transcripts, and action items for a team.</p>

            <form onSubmit={handleCreateWorkspace} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-mono text-muted">Workspace Name</label>
                <input
                  type="text"
                  placeholder="e.g. Platform Architecture"
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  autoFocus
                  className="w-full bg-surface border border-line rounded-xl px-3.5 py-2.5 text-sm text-ink placeholder-slate-500 focus:outline-none focus:border-brand"
                />
              </div>

              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setNewWorkspaceModalOpen(false)}
                  className="px-4 py-2 rounded-xl border border-line text-sm font-semibold text-muted hover:text-ink transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newWorkspaceName.trim() || creatingWorkspace}
                  className="px-4 py-2 rounded-xl bg-brand hover:bg-brand disabled:opacity-50 text-sm font-bold text-on-brand transition-colors cursor-pointer shadow-sm "
                >
                  {creatingWorkspace ? 'Creating...' : 'Create Workspace'}
                </button>
              </div>
            </form>
          </div>
        </Modal>
      )}

      {/* Discord Webhook Configuration Modal */}
      {discordModalOpen && (
        <Modal label="Connect Discord" onClose={() => setDiscordModalOpen(false)} busy={savingDiscord}>
          <div className="space-y-4">
            <div className="flex items-center gap-2.5 text-[#5865F2]">
              <div className="w-8 h-8 rounded-xl bg-[#5865F2]/20 border border-[#5865F2]/40 flex items-center justify-center text-[#5865F2] font-bold">
                #
              </div>
              <div>
                <h3 className="text-lg font-bold text-ink">Configure Discord Webhook</h3>
                <p className="text-sm text-muted">Post automated meeting digests to your Discord channel.</p>
              </div>
            </div>

            <form onSubmit={handleSaveDiscordWebhook} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-mono text-muted">Discord Webhook URL</label>
                <input
                  type="url"
                  placeholder="https://discord.com/api/webhooks/..."
                  value={discordWebhookInput}
                  onChange={(e) => setDiscordWebhookInput(e.target.value)}
                  required
                  autoFocus
                  className="w-full bg-surface border border-line rounded-xl px-3.5 py-2 text-sm text-ink placeholder-slate-500 focus:outline-none focus:border-brand"
                />
              </div>

              <div className="p-3 rounded-xl bg-surface border border-line text-sm text-muted space-y-1">
                <div className="font-bold text-ink flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-emerald-700" />
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
                  className="px-4 py-2 rounded-xl bg-surface hover:bg-line text-sm font-bold text-muted transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingDiscord || !discordWebhookInput.trim()}
                  className="px-5 py-2 rounded-xl bg-brand hover:bg-brand disabled:opacity-50 text-sm font-bold text-on-brand transition-colors cursor-pointer shadow-sm  flex items-center gap-2"
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
        </Modal>
      )}

      {/* Zoom Cloud Recordings Picker Modal */}
      {zoomPickerOpen && (
        <Modal label="Import a Zoom recording" onClose={() => setZoomPickerOpen(false)} busy={Boolean(importingZoomId)} className="mp-wide-modal">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-3">
              <div className="flex items-center gap-2.5 text-sky-700">
                <div className="w-8 h-8 rounded-xl bg-sky-500/20 border border-sky-500/40 flex items-center justify-center text-sky-700 font-bold">
                  <Radio className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-ink">Import Zoom Cloud Recordings</h3>
                  <p className="text-sm text-muted">Select a recording to process with your configured local models.</p>
                </div>
              </div>

              <button
                onClick={() => setZoomPickerOpen(false)}
                aria-label="Close Zoom recordings"
                className="p-1.5 rounded-xl bg-surface hover:bg-line text-muted hover:text-ink cursor-pointer"
              >
                <span aria-hidden="true">&times;</span>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {loadingZoomRecordings ? (
                <div className="p-12 text-center space-y-3">
                  <Loader2 className="w-8 h-8 text-sky-700 animate-spin mx-auto" />
                  <p className="text-sm text-muted">Fetching cloud recordings from Zoom API...</p>
                </div>
              ) : zoomRecordings.length === 0 ? (
                <div className="p-12 text-center border border-dashed border-line rounded-xl space-y-2">
                  <Radio className="w-8 h-8 text-muted mx-auto" />
                  <p className="text-sm text-muted">No cloud recordings found in the last 30 days.</p>
                </div>
              ) : (
                zoomRecordings.map((rec) => (
                  <div
                    key={rec.id}
                    className="p-4 rounded-xl bg-surface border border-line flex items-center justify-between gap-4 hover:border-sky-500/40 transition-colors"
                  >
                    <div className="space-y-1">
                      <div className="text-sm font-bold text-ink flex items-center gap-2">
                        <span>{rec.topic}</span>
                        <span className="px-2 py-0.5 rounded bg-sky-500/20 text-sky-700 font-mono text-sm uppercase font-bold">
                          {rec.file_type}
                        </span>
                      </div>
                      <div className="text-sm text-muted flex items-center gap-3">
                        <span>{formatMeetingDate(rec.start_time)}</span>
                        <span aria-hidden="true">&bull;</span>
                        <span>{rec.duration} mins</span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleImportZoomRecording(rec)}
                      disabled={importingZoomId === rec.id}
                      className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-on-brand text-sm font-bold transition-all shadow-md  shrink-0 flex items-center gap-2 cursor-pointer"
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

            <div className="flex justify-end pt-2 border-t border-line">
              <button
                type="button"
                onClick={() => setZoomPickerOpen(false)}
                className="px-4 py-2 rounded-xl bg-surface hover:bg-line text-sm font-bold text-muted transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* 3. Invite Member Modal */}
      {inviteModalOpen && (

        <Modal label="Invite a teammate" onClose={() => setInviteModalOpen(false)} busy={inviting}>
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-ink">Invite Teammate</h3>
            <p className="text-sm text-muted">Add a registered user by email to {activeWorkspace?.name}.</p>

            <form onSubmit={handleInviteMember} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-mono text-muted">Teammate Email</label>
                <input
                  type="email"
                  placeholder="e.g. sarah@acme.dev"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  autoFocus
                  className="w-full bg-surface border border-line rounded-xl px-3.5 py-2.5 text-sm text-ink placeholder-slate-500 focus:outline-none focus:border-brand"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-mono text-muted">Workspace Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as 'admin' | 'member')}
                  className="w-full bg-surface border border-line rounded-xl px-3.5 py-2.5 text-sm text-ink focus:outline-none focus:border-brand"
                >
                  <option value="member">Teammate (Use knowledge & meetings)</option>
                  {isWorkspaceOwner && <option value="admin">Manager (Manage Workspace)</option>}
                </select>
              </div>

              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setInviteModalOpen(false)}
                  className="px-4 py-2 rounded-xl border border-line text-sm font-semibold text-muted hover:text-ink transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!inviteEmail.trim() || inviting}
                  className="px-4 py-2 rounded-xl bg-brand hover:bg-brand disabled:opacity-50 text-sm font-bold text-on-brand transition-colors cursor-pointer shadow-sm "
                >
                  {inviting ? 'Inviting...' : 'Send Invite'}
                </button>
              </div>
            </form>
          </div>
        </Modal>
      )}

      {/* 4. Delete Workspace Confirmation Modal */}
      {deleteWorkspaceModalOpen && activeWorkspace && (

        <Modal label="Delete workspace" onClose={() => setDeleteWorkspaceModalOpen(false)} busy={deletingWorkspace}>
          <div className="space-y-4">
            <div className="flex items-center gap-3 text-red-700">
              <div className="p-2 rounded-xl bg-red-50 border border-red-500/30">
                <AlertCircle className="w-5 h-5 text-red-700" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-ink">Delete Workspace</h3>
                <p className="text-sm text-red-700 font-mono">Destructive Action Confirmation</p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-surface border border-line text-sm text-ink space-y-2">
              <p>
                Are you sure you want to permanently delete <strong className="text-ink font-bold">{activeWorkspace.name}</strong>?
              </p>
              <ul className="list-disc pl-4 space-y-1 text-muted text-sm">
                <li>All meetings and uploaded audio recordings will be deleted from disk.</li>
                <li>All transcripts, summaries, and action items will be removed.</li>
                <li>Team memberships for this workspace will be revoked.</li>
              </ul>
            </div>

            <form onSubmit={handleDeleteWorkspace} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-mono text-muted">
                  Type <span className="text-red-700 font-bold underline select-all">{activeWorkspace.name}</span> to confirm:
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
                  className="w-full bg-surface border border-red-500/30 rounded-xl px-3.5 py-2.5 text-sm text-ink placeholder-slate-600 focus:outline-none focus:border-red-500 font-mono"
                />
              </div>

              {deleteWorkspaceError && (
                <div className="text-sm text-red-700 font-mono flex items-center gap-1.5">
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
                  className="px-4 py-2 rounded-xl bg-surface hover:bg-line text-sm font-bold text-ink transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={
                    deleteConfirmText.trim().toLowerCase() !== activeWorkspace.name.trim().toLowerCase() ||
                    deletingWorkspace
                  }
                  className="px-5 py-2 rounded-xl bg-red-600 hover:bg-red-700 disabled:opacity-40 text-sm font-bold text-on-brand transition-colors cursor-pointer shadow-sm  flex items-center gap-2"
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
        </Modal>
      )}

      {/* Live meeting form; the action provider handles first-use acknowledgment. */}
      {joinWorkspaceOpen && <JoinWorkspaceModal getToken={getToken} onChange={mutateWorkspaces} onEnter={enterApprovedWorkspace} onClose={() => setJoinWorkspaceOpen(false)} />}
      <LiveMeetingModal
        initialMeetingUrl={retryLiveMeetingUrl}
        isOpen={liveMeetModalOpen}
        onClose={() => { setLiveMeetModalOpen(false); setRetryLiveMeetingUrl(''); }}
        workspaceId={activeWorkspaceId || ''}
        getToken={getToken}
        onSuccess={(created) => {
          mutateMeetings();
          setSelectedMeetingId(created.id);
          setActiveTab('meeting');
          showToast(`Assistant requested. Admission may be required before capture starts.`);
        }}
      />

      {/* Floating Feedback Toast */}
      {toastMessage && (
        <div role="status" aria-live="polite"
          className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl border shadow-sm text-sm font-semibold animate-fadeIn ${
            toastMessage.type === 'error'
              ? 'bg-rose-50 border-rose-500/50 text-rose-700'
              : 'bg-surface/95 border-brand/50 text-ink '
          }`}
        >
          {toastMessage.type === 'error' ? (
            <AlertCircle className="w-4 h-4 text-rose-700 shrink-0" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-brand shrink-0" />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}
    </div>
    </WorkspaceManagerContext.Provider>
  );
};
