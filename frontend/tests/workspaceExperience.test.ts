import assert from 'node:assert/strict';
import { test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { filterMeetings, meetingState } from '../src/utils/meetingPresentation';
import { MeetingRows } from '../src/components/workspace/MeetingLibrary';
import { WorkspaceTaskBoard } from '../src/components/workspace/WorkspaceTaskBoard';
import { MeetingPrintReport } from '../src/components/workspace/MeetingPrintReport';
import { validateOAuthAttempt } from '../src/utils/integrationOAuth';
import type { ApiMeetingListItem } from '../src/types';
const meetings: ApiMeetingListItem[] = [
  { id: 'one', title: 'Product review', status: 'completed', created_by: 'alice', created_at: '2026-10-10', participants: [{ name: 'Sam' }] },
  { id: 'two', title: 'Engineering sync', status: 'in_progress', created_by: 'bob', created_at: '2026-10-12', participants: [] },
  { id: 'three', title: 'Budget', status: 'transcribing', created_at: '2026-10-11', participants: [] },
];
test('library status/search/sort preserve live meetings and never mutate API rows', () => {
  assert.equal(meetingState('in_progress').label, 'Live');
  assert.equal(meetingState('failed').label, 'Needs attention');
  assert.deepEqual(filterMeetings(meetings, '', 'all').map(m => m.id), ['two', 'three', 'one']);
  assert.deepEqual(filterMeetings(meetings, 'SAM', 'completed').map(m => m.id), ['one']);
  assert.deepEqual(filterMeetings(meetings, '', 'processing').map(m => m.id), ['three']);
  assert.deepEqual(filterMeetings(meetings, '', 'live').map(m => m.id), ['two']);
  assert.deepEqual(meetings.map(m => m.id), ['one', 'two', 'three']);
});
test('meeting library only exposes deletion for managers or the meeting creator', () => {
  const html = (manager: boolean, actorId?: string) => renderToStaticMarkup(React.createElement(MeetingRows, { meetings, manager, actorId, onOpen: () => {}, onDelete: () => {} }));
  assert.ok(!html(false).includes('Delete Product review'));
  assert.ok(html(false, 'alice').includes('Delete Product review'));
  assert.ok(!html(false, 'alice').includes('Delete Engineering sync'));
  assert.ok(html(true).includes('Delete Engineering sync'));
});
test('board exposes creation only to managers, allows status changes and preserves unknown deadlines', () => {
  const props = { tasks: [{ id: 'task', meeting_id: 'one', title: 'Review launch', status: 'done' as const, priority: 'medium' as const }], meetings, members: [], onRetry: () => {}, onCreate: async () => {}, onStatus: async () => {}, onDelete: () => {}, onOpenMeeting: () => {} };
  const html = (manager: boolean) => renderToStaticMarkup(React.createElement(WorkspaceTaskBoard, { ...props, manager }));
  assert.ok(html(true).includes('New action'));
  assert.ok(!html(false).includes('New action'));
  assert.ok(html(false).includes('No deadline'));
  assert.ok(html(false).includes('Unassigned'));
  assert.match(html(false), /<option value="todo">To do/);
});
test('print report includes decisions, task evidence and transcript independently of active tab', () => {
  const html = renderToStaticMarkup(React.createElement(MeetingPrintReport, { meeting: { ...meetings[0], workspace_id: 'workspace' }, summary: { overview: 'Summary evidence', key_takeaways: [], next_steps: [] }, decisions: [{ id: 'd', meeting_id: 'one', topic: 'Launch scope', outcome: 'Core onboarding', source_quote: 'Finish onboarding first.' }], tasks: [], transcript: [{ id: 's', speaker: 'Sam', text: 'Real speech', start_time: 42, end_time: 46 }] }));
  for (const text of ['Summary evidence', 'Core onboarding', 'Finish onboarding first.', 'Real speech', '00:42']) assert.ok(html.includes(text));
});
test('OAuth return requires matching state, account and a recent initiation', () => {
  const attempt = { state: 'nonce', workspaceId: 'workspace', actorId: 'alice', createdAt: 1000 };
  assert.equal(validateOAuthAttempt(attempt, 'nonce', 'alice', 2000), attempt);
  for (const [state, actor, now] of [['wrong', 'alice', 2000], ['nonce', 'bob', 2000], ['nonce', 'alice', 602000], ['nonce', 'alice', 0]] as const) assert.throws(() => validateOAuthAttempt(attempt, state, actor, now));
  assert.throws(() => validateOAuthAttempt(null, 'nonce', 'alice'));
});
