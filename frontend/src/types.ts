export type TaskPriority = 'low' | 'medium' | 'high';
export type TaskStatus = 'todo' | 'doing' | 'done';
export type MeetingStatus = 'in_progress' | 'queued' | 'processing' | 'completed' | 'failed';

export interface TaskItem {
  id: string;
  meetingId?: string;
  title: string;
  assignee: {
    name: string;
    avatar: string;
    role: string;
  };
  dueDate: string;
  completed: boolean;
  timestamp: string;
  priority: TaskPriority;
  status: TaskStatus;
}

export interface DecisionItem {
  id: string;
  topic: string;
  outcome: string;
  timestamp: string;
}

export interface TranscriptLine {
  id: string;
  speaker: string;
  avatar: string;
  time: string;
  startTime: number;
  endTime: number;
  text: string;
  highlight?: boolean;
}

export interface Meeting {
  id: string;
  workspaceId: string;
  title: string;
  status: MeetingStatus;
  source?: 'upload' | 'live' | string;
  native_meeting_id?: string | null;
  date: string;
  duration: string;
  durationSeconds?: number | null;
  audioUrl?: string | null;
  failureReason?: string | null;
  participants: { name: string; avatar: string; role: string }[];
  summary: {
    overview: string;
    keyTakeaways: string[];
    nextSteps: string[];
  };
  tasks: TaskItem[];
  decisions: DecisionItem[];
  transcript: TranscriptLine[];
  sampleQuestions?: { question: string; answer: string; timestamp?: string }[];
}

export interface ApiWorkspace {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
}

export interface ApiWorkspaceMember {
  user_id: string;
  role: 'owner' | 'admin' | 'member';
  name: string;
  email: string;
  avatar_url?: string | null;
}

export interface ApiAuthSession {
  user: {
    id?: string;
    name: string;
    email: string;
    avatar_url?: string | null;
  };
  clerk_id?: string | null;
  authenticated: boolean;
}

export interface ApiMeetingListItem {
  id: string;
  title: string;
  status: MeetingStatus;
  source?: 'upload' | 'live' | string;
  native_meeting_id?: string | null;
  duration_seconds?: number | null;
  created_at: string;
  participants: Array<{
    name: string;
    avatar_url?: string | null;
    role?: string | null;
  }>;
}

export interface ApiMeetingDetail extends ApiMeetingListItem {
  audio_url?: string | null;
  failure_reason?: string | null;
}

export interface ApiMeetingSummary {
  overview?: string | null;
  key_takeaways: string[];
  next_steps: string[];
}

export interface ApiTranscriptSegment {
  id: string;
  speaker: string;
  start_time: number;
  end_time: number;
  text: string;
}

export interface ApiTask {
  id: string;
  meeting_id: string;
  title: string;
  assignee_name?: string | null;
  due_date?: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  transcript_timestamp?: string | null;
  created_at?: string;
}

export interface ApiDecision {
  id: string;
  meeting_id: string;
  topic: string;
  outcome: string;
  transcript_timestamp?: string | null;
  created_at?: string;
}

export interface ApiChatMessage {
  id: string;
  user_id?: string | null;
  role: 'user' | 'assistant';
  content: string;
  cited_timestamp?: string | null;
  created_at: string;
}

export interface ApiNotification {
  id: string;
  user_id: string;
  type: string;
  message: string;
  meeting_id?: string | null;
  read: boolean;
  created_at: string;
}

export interface ApiSearchResult {
  type: 'meeting' | 'transcript' | 'task' | 'decision';
  meeting_id: string;
  meeting_title: string;
  snippet: string;
  timestamp?: string | null;
}

export interface ApiSearchResponse {
  query: string;
  results: ApiSearchResult[];
}

export interface TechStackItem {
  name: string;
  role: string;
  iconName: string;
  color: string;
}

export interface FeatureCard {
  id: string;
  title: string;
  description: string;
  icon: string;
  badge?: string;
  colSpan?: string;
}

