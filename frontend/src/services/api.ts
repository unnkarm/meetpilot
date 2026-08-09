import useSWR from 'swr';
import {
  ApiAuthSession,
  ApiChatMessage,
  ApiDecision,
  ApiMeetingDetail,
  ApiMeetingListItem,
  ApiMeetingSummary,
  ApiNotification,
  ApiSearchResponse,
  ApiTask,
  ApiTranscriptSegment,
  ApiWorkspace,
  ApiWorkspaceMember,
  TaskPriority,
  TaskStatus,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

let globalClerkUser: { email?: string; name?: string; avatar?: string } | null = null;

export function setClerkUserContext(userCtx: { email?: string; name?: string; avatar?: string } | null) {
  globalClerkUser = userCtx;
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  getToken?: () => Promise<string | null>
): Promise<T> {
  const headers = new Headers(options.headers || {});

  if (getToken) {
    try {
      const token = await getToken();
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
    } catch (err) {
      console.warn('Failed to retrieve Clerk session token:', err);
    }
  }

  if (globalClerkUser) {
    if (globalClerkUser.email) headers.set('X-User-Email', globalClerkUser.email);
    if (globalClerkUser.name) headers.set('X-User-Name', globalClerkUser.name);
    if (globalClerkUser.avatar) headers.set('X-User-Avatar', globalClerkUser.avatar);
  }

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || `API Request Failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export function getAudioStreamUrl(meetingId: string): string {
  return `${API_BASE_URL}/api/v1/meetings/${meetingId}/audio`;
}

// SWR Fetcher with Token Injection
export const createTokenFetcher = (getToken?: () => Promise<string | null>) => {
  return async <T>(url: string): Promise<T> => {
    return apiFetch<T>(url, {}, getToken);
  };
};

// Typed SWR Hooks for MeetPilot AI

export function useAuthMe(getToken?: () => Promise<string | null>) {
  return useSWR<ApiAuthSession>(
    '/api/v1/auth/me',
    createTokenFetcher(getToken),
    { revalidateOnFocus: false, shouldRetryOnError: false }
  );
}

export function useWorkspaces(getToken?: () => Promise<string | null>) {
  return useSWR<ApiWorkspace[]>(
    '/api/v1/workspaces',
    createTokenFetcher(getToken),
    { revalidateOnFocus: true }
  );
}

export function useWorkspaceMembers(workspaceId?: string | null, getToken?: () => Promise<string | null>) {
  return useSWR<ApiWorkspaceMember[]>(
    workspaceId ? `/api/v1/workspaces/${workspaceId}/members` : null,
    createTokenFetcher(getToken),
    { revalidateOnFocus: false }
  );
}

export function useMeetings(workspaceId?: string | null, getToken?: () => Promise<string | null>) {
  return useSWR<ApiMeetingListItem[]>(
    workspaceId ? `/api/v1/meetings?workspace_id=${workspaceId}` : null,
    createTokenFetcher(getToken),
    { revalidateOnFocus: true, refreshInterval: 5000 }
  );
}

export function useMeetingDetail(meetingId?: string | null, getToken?: () => Promise<string | null>) {
  return useSWR<ApiMeetingDetail>(
    meetingId && meetingId !== 'empty' ? `/api/v1/meetings/${meetingId}` : null,
    createTokenFetcher(getToken),
    {
      refreshInterval: (latestData) => {
        // Poll every 3 seconds if meeting is in_progress, queued or processing
        if (
          latestData?.status === 'in_progress' ||
          latestData?.status === 'queued' ||
          latestData?.status === 'processing'
        ) {
          return 3000;
        }
        return 0;
      },
    }
  );
}

export function useMeetingSummary(meetingId?: string | null, isProcessing = false, getToken?: () => Promise<string | null>) {
  return useSWR<ApiMeetingSummary>(
    meetingId && meetingId !== 'empty' && !isProcessing ? `/api/v1/meetings/${meetingId}/summary` : null,
    createTokenFetcher(getToken),
    { shouldRetryOnError: false }
  );
}

export function useMeetingTranscript(meetingId?: string | null, isProcessing = false, getToken?: () => Promise<string | null>) {
  return useSWR<ApiTranscriptSegment[]>(
    meetingId && meetingId !== 'empty' && !isProcessing ? `/api/v1/meetings/${meetingId}/transcript` : null,
    createTokenFetcher(getToken),
    {
      refreshInterval: 2500,
      shouldRetryOnError: false,
    }
  );
}

export function useMeetingDecisions(meetingId?: string | null, isProcessing = false, getToken?: () => Promise<string | null>) {
  return useSWR<ApiDecision[]>(
    meetingId && meetingId !== 'empty' && !isProcessing ? `/api/v1/meetings/${meetingId}/decisions` : null,
    createTokenFetcher(getToken),
    { shouldRetryOnError: false }
  );
}

export function useMeetingTasks(meetingId?: string | null, isProcessing = false, getToken?: () => Promise<string | null>) {
  return useSWR<ApiTask[]>(
    meetingId && meetingId !== 'empty' && !isProcessing ? `/api/v1/meetings/${meetingId}/tasks` : null,
    createTokenFetcher(getToken),
    { shouldRetryOnError: false }
  );
}

export function useWorkspaceTasks(workspaceId?: string | null, getToken?: () => Promise<string | null>) {
  return useSWR<ApiTask[]>(
    workspaceId ? `/api/v1/tasks?workspace_id=${workspaceId}` : null,
    createTokenFetcher(getToken),
    { revalidateOnFocus: true }
  );
}

export function useMeetingChat(meetingId?: string | null, getToken?: () => Promise<string | null>) {
  return useSWR<ApiChatMessage[]>(
    meetingId && meetingId !== 'empty' ? `/api/v1/meetings/${meetingId}/chat` : null,
    createTokenFetcher(getToken),
    { revalidateOnFocus: false }
  );
}

export function useWorkspaceIntegrations(workspaceId?: string | null, getToken?: () => Promise<string | null>) {
  return useSWR<WorkspaceIntegrationItem[]>(
    workspaceId ? `/api/v1/integrations/workspace/${workspaceId}` : null,
    createTokenFetcher(getToken),
    { revalidateOnFocus: true }
  );
}


export function useNotifications(getToken?: () => Promise<string | null>) {
  return useSWR<ApiNotification[]>(
    '/api/v1/users/notifications',
    createTokenFetcher(getToken),
    { refreshInterval: 15000 }
  );
}

export function useSearch(query: string, workspaceId?: string | null, getToken?: () => Promise<string | null>) {
  const trimmed = query.trim();
  return useSWR<ApiSearchResponse>(
    trimmed && workspaceId ? `/api/v1/search?q=${encodeURIComponent(trimmed)}&workspace_id=${workspaceId}` : null,
    createTokenFetcher(getToken),
    { dedupingInterval: 300 }
  );
}

// Mutation Operations

export async function uploadMeetingAudio(
  workspaceId: string,
  title: string,
  file: File,
  getToken?: () => Promise<string | null>
): Promise<{ id: string; title: string; status: string }> {
  const formData = new FormData();
  formData.append('workspace_id', workspaceId);
  formData.append('title', title);
  formData.append('file', file);

  return apiFetch<{ id: string; title: string; status: string }>(
    '/api/v1/meetings/upload',
    {
      method: 'POST',
      body: formData,
    },
    getToken
  );
}

export async function createWorkspaceApi(
  name: string,
  getToken?: () => Promise<string | null>
): Promise<ApiWorkspace> {
  return apiFetch<ApiWorkspace>(
    '/api/v1/workspaces',
    {
      method: 'POST',
      body: JSON.stringify({ name }),
    },
    getToken
  );
}

export async function inviteWorkspaceMemberApi(
  workspaceId: string,
  email: string,
  role: 'owner' | 'admin' | 'member' = 'member',
  getToken?: () => Promise<string | null>
): Promise<ApiWorkspaceMember> {
  return apiFetch<ApiWorkspaceMember>(
    `/api/v1/workspaces/${workspaceId}/invite`,
    {
      method: 'POST',
      body: JSON.stringify({ email, role }),
    },
    getToken
  );
}

export async function updateTaskApi(
  taskId: string,
  updates: {
    status?: TaskStatus;
    priority?: TaskPriority;
    title?: string;
    due_date?: string | null;
    assignee_name?: string | null;
  },
  getToken?: () => Promise<string | null>
): Promise<ApiTask> {
  return apiFetch<ApiTask>(
    `/api/v1/tasks/${taskId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(updates),
    },
    getToken
  );
}

export async function createTaskApi(
  taskData: {
    title: string;
    workspace_id?: string;
    meeting_id?: string;
    assignee_name?: string;
    due_date?: string;
    priority?: TaskPriority;
    status?: TaskStatus;
  },
  getToken?: () => Promise<string | null>
): Promise<ApiTask> {
  return apiFetch<ApiTask>(
    '/api/v1/tasks',
    {
      method: 'POST',
      body: JSON.stringify(taskData),
    },
    getToken
  );
}

export async function sendChatMessageApi(
  meetingId: string,
  question: string,
  getToken?: () => Promise<string | null>
): Promise<{ answer: string; cited_timestamp: string | null }> {
  return apiFetch<{ answer: string; cited_timestamp: string | null }>(
    `/api/v1/meetings/${meetingId}/chat`,
    {
      method: 'POST',
      body: JSON.stringify({ question }),
    },
    getToken
  );
}

export async function deleteMeetingApi(
  meetingId: string,
  getToken?: () => Promise<string | null>
): Promise<void> {
  await apiFetch<void>(
    `/api/v1/meetings/${meetingId}`,
    {
      method: 'DELETE',
    },
    getToken
  );
}

export async function updateMeetingApi(
  meetingId: string,
  updates: { title?: string },
  getToken?: () => Promise<string | null>
): Promise<ApiMeetingDetail> {
  return apiFetch<ApiMeetingDetail>(
    `/api/v1/meetings/${meetingId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(updates),
    },
    getToken
  );
}

export async function deleteTaskApi(
  taskId: string,
  getToken?: () => Promise<string | null>
): Promise<void> {
  await apiFetch<void>(
    `/api/v1/tasks/${taskId}`,
    {
      method: 'DELETE',
    },
    getToken
  );
}

export async function retryMeetingApi(
  meetingId: string,
  getToken?: () => Promise<string | null>
): Promise<{ id: string; title: string; status: string }> {

  return apiFetch<{ id: string; title: string; status: string }>(
    `/api/v1/meetings/${meetingId}/retry`,
    {
      method: 'POST',
    },
    getToken
  );
}


export async function deleteWorkspaceApi(
  workspaceId: string,
  getToken?: () => Promise<string | null>
): Promise<void> {
  await apiFetch<void>(
    `/api/v1/workspaces/${workspaceId}`,
    {
      method: 'DELETE',
    },
    getToken
  );
}

// --- Phase C: Third-Party Integrations API ---

export interface WorkspaceIntegrationItem {
  provider: string;
  is_connected: boolean;
  masked_identifier: string | null;
  updated_at: string | null;
}

export interface ZoomCloudRecording {
  id: string;
  topic: string;
  start_time: string;
  duration: number;
  download_url: string;
  file_type: string;
  file_size?: number;
}

export async function fetchWorkspaceIntegrationsApi(
  workspaceId: string,
  getToken?: () => Promise<string | null>
): Promise<WorkspaceIntegrationItem[]> {
  return apiFetch<WorkspaceIntegrationItem[]>(
    `/api/v1/integrations/workspace/${workspaceId}`,
    {},
    getToken
  );
}

export async function setupDiscordWebhookApi(
  workspaceId: string,
  webhookUrl: string,
  getToken?: () => Promise<string | null>
): Promise<WorkspaceIntegrationItem> {
  return apiFetch<WorkspaceIntegrationItem>(
    `/api/v1/integrations/workspace/${workspaceId}/discord`,
    {
      method: 'POST',
      body: JSON.stringify({ webhook_url: webhookUrl }),
    },
    getToken
  );
}

export async function disconnectIntegrationApi(
  workspaceId: string,
  provider: string,
  getToken?: () => Promise<string | null>
): Promise<void> {
  await apiFetch<void>(
    `/api/v1/integrations/workspace/${workspaceId}/${provider}`,
    {
      method: 'DELETE',
    },
    getToken
  );
}

export async function getGoogleAuthUrlApi(
  workspaceId: string,
  getToken?: () => Promise<string | null>
): Promise<{ url: string }> {
  return apiFetch<{ url: string }>(
    `/api/v1/integrations/google/auth-url?workspace_id=${workspaceId}`,
    {},
    getToken
  );
}

export async function exchangeGoogleOAuthApi(
  workspaceId: string,
  code: string,
  getToken?: () => Promise<string | null>
): Promise<WorkspaceIntegrationItem> {
  return apiFetch<WorkspaceIntegrationItem>(
    `/api/v1/integrations/google/callback`,
    {
      method: 'POST',
      body: JSON.stringify({ workspace_id: workspaceId, code }),
    },
    getToken
  );
}

export async function getZoomAuthUrlApi(
  workspaceId: string,
  getToken?: () => Promise<string | null>
): Promise<{ url: string }> {
  return apiFetch<{ url: string }>(
    `/api/v1/integrations/zoom/auth-url?workspace_id=${workspaceId}`,
    {},
    getToken
  );
}

export async function exchangeZoomOAuthApi(
  workspaceId: string,
  code: string,
  getToken?: () => Promise<string | null>
): Promise<WorkspaceIntegrationItem> {
  return apiFetch<WorkspaceIntegrationItem>(
    `/api/v1/integrations/zoom/callback`,
    {
      method: 'POST',
      body: JSON.stringify({ workspace_id: workspaceId, code }),
    },
    getToken
  );
}

export async function fetchZoomRecordingsApi(
  workspaceId: string,
  getToken?: () => Promise<string | null>
): Promise<ZoomCloudRecording[]> {
  return apiFetch<ZoomCloudRecording[]>(
    `/api/v1/integrations/workspace/${workspaceId}/zoom/recordings`,
    {},
    getToken
  );
}

export async function importZoomRecordingApi(
  workspaceId: string,
  topic: string,
  downloadUrl: string,
  fileType: string = 'M4A',
  getToken?: () => Promise<string | null>
): Promise<{ id: string; title: string; status: string; message: string }> {
  return apiFetch<{ id: string; title: string; status: string; message: string }>(
    `/api/v1/integrations/workspace/${workspaceId}/zoom/import`,
    {
      method: 'POST',
      body: JSON.stringify({
        topic,
        download_url: downloadUrl,
        file_type: fileType,
      }),
    },
    getToken
  );
}

export async function startLiveMeeting(
  workspaceId: string,
  meetingUrl: string,
  title?: string,
  getToken?: () => Promise<string | null>
): Promise<ApiMeetingDetail> {
  return apiFetch<ApiMeetingDetail>(
    '/api/v1/meetings/live/start',
    {
      method: 'POST',
      body: JSON.stringify({
        workspace_id: workspaceId,
        meeting_url: meetingUrl,
        title: title || undefined,
      }),
    },
    getToken
  );
}

export async function stopLiveMeeting(
  meetingId: string,
  getToken?: () => Promise<string | null>
): Promise<ApiMeetingDetail> {
  return apiFetch<ApiMeetingDetail>(
    `/api/v1/meetings/live/${meetingId}/stop`,
    {
      method: 'POST',
    },
    getToken
  );
}


