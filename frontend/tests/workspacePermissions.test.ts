import assert from 'node:assert/strict';
import { test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { isWorkspaceManager, WorkspaceManagerContext } from '../src/utils/workspacePermissions';
import { ActionItemsView } from '../src/components/workspace/ActionItemsView';
import { JoinRequestList, WorkspaceOnboarding } from '../src/components/workspace/WorkspaceAccessPanel';
import type { JoinRequest } from '../src/components/workspace/WorkspaceAccessPanel';

test('only owner and admin expose manager controls; missing roles fail closed', () => {
  assert.equal(isWorkspaceManager('owner'), true);
  assert.equal(isWorkspaceManager('admin'), true);
  for (const role of [undefined, 'member', 'manager', 'Owner']) assert.equal(isWorkspaceManager(role), false);
});

test('pending, rejected, and removed applications never offer workspace entry', () => {
  const request: JoinRequest = { id: 'request', workspace_id: 'workspace', workspace_name: 'Company', user_id: 'applicant', name: 'Alice', email: 'alice@example.test', status: 'pending', created_at: '2026-10-08' };
  const html = (status: JoinRequest['status']) => renderToStaticMarkup(React.createElement(JoinRequestList, { requests: [{ ...request, status }], onEnter: () => {} }));
  assert.match(html('pending'), /Waiting for manager approval/);
  assert.match(html('removed'), /Access removed/);
  for (const status of ['pending', 'rejected', 'removed'] as const) assert.ok(!html(status).includes('Enter workspace'));
  assert.ok(html('approved').includes('Enter workspace'));
});

test('a new teammate can choose joining without an automatically created workspace', () => {
  const html = renderToStaticMarkup(React.createElement(WorkspaceOnboarding, {
    getToken: async () => null, onEnter: async () => {}, loading: false,
    onRetry: () => {}, onBack: () => {}, onSignOut: () => {},
  }));
  assert.ok(html.includes('Join Workspace with Code'));
  assert.ok(html.includes('Create workspace'));
  assert.ok(html.includes('wait for approval'));
});
test('teammate task view keeps status controls but omits the assignment form', () => {
  const props = { tasks: [{ id: 'task', meeting_id: 'meeting', title: 'Review my PR', assignee_id: 'user', assignee_name: 'Alice', status: 'todo' as const, priority: 'medium' as const }],
    members: [], onUpdateTaskStatus: async () => {}, onDeleteTask: () => {}, onAddTask: async () => {}, onSeek: () => {}, onOpenKanban: () => {}, onUpdateTask: async () => {} };
  const html = (manager: boolean) => renderToStaticMarkup(React.createElement(WorkspaceManagerContext.Provider, { value: manager }, React.createElement(ActionItemsView, props)));
  assert.ok(html(false).includes('Review my PR'));
  assert.ok(!html(false).includes('Quick Add Action Item'));
  assert.ok(html(true).includes('Quick Add Action Item'));
  assert.match(html(false), /button disabled=""[^>]*aria-label="Edit task/);
});
