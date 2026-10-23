"""Run against the isolated fixture Vite server on :3011, never the Docker stack.
Requires the developer's Python Playwright installation. All API calls are mocked.
"""
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

ROOT = 'http://127.0.0.1:3011'
OUTPUT = Path(os.environ.get('MEETPILOT_UI_OUTPUT', 'scratch/frontend-review'))
OUTPUT.mkdir(parents=True, exist_ok=True)
actor = '11111111-1111-4111-8111-111111111111'
workspace = '22222222-2222-4222-8222-222222222222'
meeting = '33333333-3333-4333-8333-333333333333'
members = [dict(user_id=actor, name='Alex Morgan', email='alex@example.test', role='owner'), dict(user_id='44444444-4444-4444-8444-444444444444', name='Sam Rivera', email='sam@example.test', role='member')]
meetings = [dict(id=meeting, title='Product & engineering review', status='completed', source='live', created_at='2026-10-12T10:00:00Z', duration_seconds=1440, created_by=actor, participants=[dict(name='Alex Morgan'), dict(name='Sam Rivera')]), dict(id='live', title='Customer onboarding sync', status='in_progress', source='live', created_at='2026-10-12T11:00:00Z', duration_seconds=0, created_by='other', participants=[]), dict(id='queued', title='Sprint planning', status='queued', source='upload', created_at='2026-10-11T11:00:00Z', duration_seconds=1800, participants=[]), dict(id='failed', title='Partner call', status='failed', source='live', created_at='2026-10-10T11:00:00Z', duration_seconds=0, participants=[])]
tasks = [dict(id='task-one', meeting_id=meeting, title='Review the launch checklist', assignee_id=actor, assignee_name='Alex Morgan', due_date='2026-10-16', priority='high', status='todo', source_quote='Alex will review the checklist by Friday.', source_speaker='Sam Rivera', transcript_timestamp='00:42'), dict(id='task-two', meeting_id=meeting, title='Finalize the onboarding flow', assignee_id=members[1]['user_id'], assignee_name='Sam Rivera', priority='medium', status='doing'), dict(id='task-three', meeting_id=meeting, title='Publish internal release notes', priority='low', status='done')]
segments = [dict(id='speech-one', speaker='Sam Rivera', text='We decided to focus the launch on the core onboarding flow. Alex will review the checklist by Friday.', start_time=42, end_time=52), dict(id='speech-two', speaker='Alex Morgan', text='I agree. Let’s keep the launch scope focused.', start_time=53, end_time=59)]
docs = [dict(id='doc', workspace_id=workspace, title='Product handbook', filename='product-handbook.pdf', file_type='pdf', file_size=81920, status='ready', chunk_count=12, created_at='2026-10-10', updated_at='2026-10-10')]

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=dict(width=1440, height=1000), device_scale_factor=1, color_scheme='light')
        errors, writes, unmatched = [], [], []
        role = ['owner']
        def route_api(route):
            request = route.request
            path = urlparse(request.url).path
            method = request.method
            body = request.post_data_json if request.post_data else None
            if method not in ['GET', 'OPTIONS']: writes.append((method, path, body))
            status, data = 200, []
            if method == 'OPTIONS': pass
            elif path == '/api/v1/auth/me': data = dict(authenticated=True, user=dict(id=actor, name='Alex Morgan', email='alex@example.test'))
            elif path == '/api/v1/legal/acceptance': data = dict(accepted=True, accepted_at='2026-10-12T10:00:00Z', policies=dict(versions=dict(terms='2026-10-12.1', privacy='2026-10-12.1', recording='2026-10-12.1'), operator=dict(name='', address='', privacy_email='', jurisdiction='', processing='', retention=''), published=False, bundle='fixture-policy'))
            elif path == '/api/v1/legal/policies': data = dict(versions=dict(terms='2026-10-12.1', privacy='2026-10-12.1', recording='2026-10-12.1'), operator=dict(name='', address='', privacy_email='', jurisdiction='', processing='', retention=''), published=False, bundle='fixture-policy')
            elif path == '/api/v1/workspaces': data = [dict(id=workspace, name='Juniper Studio', owner_id=actor, created_at='2026-10-01', current_role=role[0])]
            elif path.endswith('/members'): data = members
            elif path.endswith('/join-requests'): data = []
            elif path == '/api/v1/users/notifications': data = []
            elif path.endswith('/analytics'): data = dict(total_meetings=4, completed_meetings=1, total_speaking_hours=.9, avg_meeting_duration_minutes=18, total_decisions=1, total_tasks=3, completed_tasks=1, in_progress_tasks=1, todo_tasks=1, task_completion_rate=33, speakers_distribution=[])
            elif path == '/api/v1/documents': data = docs
            elif path == '/api/v1/meetings': data = meetings
            elif path == '/api/v1/tasks' and method == 'POST':
                data = dict(body); data.update(id='created-task', assignee_name='Sam Rivera', meeting_id=body.get('meeting_id', meeting))
                tasks.append(data)
            elif path == '/api/v1/tasks': data = tasks if role[0] == 'owner' else [t for t in tasks if t.get('assignee_id') == actor]
            elif path.startswith('/api/v1/tasks/') and method == 'PATCH':
                task = next(t for t in tasks if t['id'] == path.split('/')[-1]); task.update(body); data = task
            elif path == f'/api/v1/integrations/workspace/{workspace}': data = []
            elif path.endswith('/pilot/settings'): data = dict(voice_id='piper', can_edit=role[0] == 'owner', voices=[dict(id='piper', label='Natural voice', available=True)])
            elif path.endswith('/summary-templates'): data = dict(can_manage=role[0] == 'owner', templates=[dict(id='executive', name='Executive', instructions='Summarize with evidence', builtin=True)])
            elif path.endswith('/review/metrics'): data = dict(duration_seconds=1440, speech_seconds=16, silence_seconds=1424, overlap_speaker_seconds=0, speakers=[], notes=['Metrics are derived from transcript timestamps.'])
            elif path.endswith('/review/risks'): data = dict(risks=[], note='No accessible blockers detected.')
            elif path.endswith('/review/artifacts') and method == 'POST': data = dict(id='artifact', kind='summary', status='queued', options={})
            elif path.endswith('/review/artifacts/artifact'): data = dict(id='artifact', kind='summary', status='queued', options={})
            elif path.endswith('/review/artifacts') or path.endswith('/bookmarks') or path.endswith('/identities') or (path.startswith('/api/v1/meetings/') and path.endswith('/chat')): data = []
            elif path.endswith('/transcript'): data = segments
            elif path.endswith('/decisions'): data = [dict(id='decision', meeting_id=meeting, topic='Launch scope', outcome='Prioritize the core onboarding flow.', source_quote=segments[0]['text'], source_speaker='Sam Rivera', transcript_timestamp='00:42', source_segment_id='speech-one')]
            elif path.endswith('/summary'): data = dict(overview='The team aligned on a focused launch and agreed to finish the core onboarding flow before expanding scope.', key_takeaways=['Focus on core onboarding for the first release.'], next_steps=['Review the launch checklist on Friday.'])
            elif path.endswith('/tasks'): data = tasks if role[0] == 'owner' else [t for t in tasks if t.get('assignee_id') == actor]
            elif path.startswith('/api/v1/meetings/') and len(path.split('/')) == 5: data = dict(**meetings[0], workspace_id=workspace, transcription_language='en')
            elif path == '/api/v1/knowledge/chat': data = dict(answer='The team agreed to focus on core onboarding.', citations=[dict(type='meeting', title=meetings[0]['title'], meeting_id=meeting, timestamp='00:42', speaker='Sam Rivera', snippet=segments[0]['text'])])
            elif path in ['/api/v1/integrations/google/callback', '/api/v1/integrations/zoom/callback']: data = dict(is_connected=True, provider='google_calendar', masked_identifier='account@example.test')
            elif path == '/api/v1/search': data = dict(total_results=1, results=[dict(type='decision', meeting_id=meeting, meeting_title=meetings[0]['title'], snippet='Focus on onboarding', timestamp='00:42', speaker='Sam Rivera')])
            else: unmatched.append((method, path)); status, data = 404, dict(detail='Unmocked fixture endpoint')
            route.fulfill(status=status, content_type='application/json', body=json.dumps(data), headers={'Access-Control-Allow-Origin': ROOT, 'Access-Control-Allow-Headers': '*', 'Access-Control-Allow-Methods': '*'})
        context.route('**/api/v1/**', route_api)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(ROOT + '/app')
        expect(page.get_by_role('heading', name=re.compile(r'^Good (morning|afternoon|evening), Alex\.$'))).to_be_visible()
        # Dark + blue-purple are defaults even on a device using light mode.
        expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
        expect(page.locator('html')).to_have_attribute('data-palette', 'indigo')
        page.evaluate('window.scrollTo(0, 0)'); page.screenshot(path=str(OUTPUT / 'overview-desktop.png'), full_page=True)
        page.get_by_role('button', name='Switch to light mode', exact=True).click()
        expect(page.locator('html')).to_have_attribute('data-theme', 'light')
        page.get_by_role('button', name='Switch to dark mode', exact=True).click()
        expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
        expect(page.locator('.mp-sidebar')).to_have_css('background-color', 'rgb(17, 21, 28)')
        expect(page.locator('.mp-metric').first).to_have_css('background-color', 'rgb(17, 21, 28)')
        page.reload()
        expect(page.get_by_role('heading', name=re.compile(r'^Good (morning|afternoon|evening), Alex\.$'))).to_be_visible()
        expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
        page.screenshot(path=str(OUTPUT / 'overview-dark.png'), full_page=True)
        page.get_by_role('button', name='Settings', exact=True).click()
        page.get_by_role('button', name='Appearance', exact=True).click()
        page.get_by_role('radio', name='System', exact=False).check()
        page.emulate_media(color_scheme='light')
        expect(page.locator('html')).to_have_attribute('data-theme', 'light')
        page.emulate_media(color_scheme='dark')
        expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
        page.get_by_role('radio', name='Dark', exact=False).check()
        page.emulate_media(color_scheme='light')
        expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
        # Every palette previews immediately and keeps primary button contrast.
        palettes = [('Blue & purple', 'indigo', '#6640d8', '#b7a5ff'), ('Ocean blue', 'blue', '#2362c6', '#8dbbff'), ('Teal', 'teal', '#176b5e', '#75d7bf'), ('Rose', 'rose', '#ac3469', '#f2a6c7'), ('Amber', 'amber', '#8a580b', '#efc27a')]
        for label, palette_id, light, dark in palettes:
            page.get_by_role('radio', name=label, exact=True).check()
            expect(page.locator('html')).to_have_attribute('data-palette', palette_id)
            stored_palette = page.evaluate("localStorage.getItem('meetpilot:palette')")
            assert stored_palette == palette_id or (palette_id == 'indigo' and stored_palette is None)
            for mode, accent in [('light', light), ('dark', dark)]:
                page.get_by_role('radio', name=mode.title(), exact=True).check()
                rgb = tuple(int(accent[i:i + 2], 16) for i in (1, 3, 5))
                expect(page.get_by_role('button', name='Join meeting', exact=True)).to_have_css('background-color', f'rgb{rgb}')
                contrast = page.get_by_role('button', name='Join meeting', exact=True).evaluate('''el => {
                    const style = getComputedStyle(el);
                    const luminance = value => value.match(/[\d.]+/g).slice(0, 3).map(Number).map(c => c / 255).map(c => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4).reduce((n, c, i) => n + c * [.2126, .7152, .0722][i], 0);
                    const a = luminance(style.color), b = luminance(style.backgroundColor);
                    return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
                }''')
                assert contrast >= 4.5, (label, mode, contrast)
        page.reload()
        expect(page.locator('html')).to_have_attribute('data-palette', 'amber')
        page.get_by_role('button', name='Settings', exact=True).click()
        page.get_by_role('button', name='Appearance', exact=True).click()
        expect(page.get_by_role('radio', name='Amber', exact=True)).to_be_checked()
        page.get_by_role('radio', name='Blue & purple', exact=True).check()
        sibling = context.new_page()
        sibling.goto(ROOT + '/?signedOut=1')
        sibling.get_by_role('button', name='Switch to light mode', exact=True).click()
        expect(page.locator('html')).to_have_attribute('data-theme', 'light')
        expect(page.get_by_role('radio', name='Light', exact=False)).to_be_checked()
        sibling.goto(ROOT + '/app')
        sibling.get_by_role('button', name='Settings', exact=True).click()
        sibling.get_by_role('button', name='Appearance', exact=True).click()
        sibling.get_by_role('radio', name='Ocean blue', exact=True).check()
        expect(page.locator('html')).to_have_attribute('data-palette', 'blue')
        expect(page.get_by_role('radio', name='Ocean blue', exact=True)).to_be_checked()
        sibling.close()
        page.get_by_role('radio', name='Blue & purple', exact=True).check()
        page.get_by_role('radio', name='Dark', exact=False).check()
        expect(page.get_by_role('button', name='Appearance', exact=True)).to_have_css('color', 'rgb(33, 21, 55)')
        page.screenshot(path=str(OUTPUT / 'appearance-dark.png'), full_page=True)
        nav = page.locator('.mp-nav')
        nav.get_by_role('button', name='Meetings', exact=True).click()
        expect(page.get_by_role('heading', name='Every conversation, in one place.')).to_be_visible()
        page.get_by_role('button', name='Live', exact=True).click()
        expect(page.locator('tbody tr')).to_have_count(1)
        expect(page.locator('tbody')).to_contain_text('Customer onboarding sync')
        page.get_by_role('button', name='All meetings', exact=True).click()
        page.get_by_role('textbox', name='Search meetings').fill('Sam')
        expect(page.locator('tbody tr')).to_have_count(1)
        page.get_by_role('textbox', name='Search meetings').fill('')
        page.evaluate('window.scrollTo(0, 0)'); page.screenshot(path=str(OUTPUT / 'meetings-desktop.png'), full_page=True)
        nav.get_by_role('button', name='Action items', exact=True).click()
        page.get_by_role('button', name='New action', exact=True).click()
        dialog = page.get_by_role('dialog', name='New action item')
        dialog.get_by_label('Action', exact=True).fill('Check the release plan')
        dialog.get_by_label('Assignee', exact=True).select_option(members[1]['user_id'])
        dialog.get_by_role('button', name='Create action').click()
        expect(page.get_by_role('heading', name='Check the release plan', exact=True)).to_be_visible()
        create = next(body for method, path, body in writes if method == 'POST' and path == '/api/v1/tasks')
        assert create['workspace_id'] == workspace and create['assignee_id'] == members[1]['user_id'] and 'due_date' not in create
        page.locator('#status-task-three').select_option('todo')
        page.evaluate('window.scrollTo(0, 0)'); page.screenshot(path=str(OUTPUT / 'actions-desktop.png'), full_page=True)
        nav.get_by_role('button', name='Knowledge', exact=True).click()
        expect(page.get_by_role('heading', name='Ask your workspace', exact=True)).to_be_visible()
        page.get_by_role('textbox', name='Ask workspace knowledge').fill('What did we decide?')
        page.get_by_role('button', name='Ask AI', exact=True).click()
        expect(page.get_by_text('The team agreed to focus on core onboarding.', exact=True)).to_be_visible()
        page.evaluate('window.scrollTo(0, 0)'); page.screenshot(path=str(OUTPUT / 'knowledge-desktop.png'), full_page=True)
        nav.get_by_role('button', name='Search', exact=True).click()
        page.get_by_role('textbox', name='Search workspace knowledge').fill('onboarding')
        page.locator('form button[type="submit"]').click()
        page.get_by_role('button', name='Open meeting at timestamp', exact=True).click()
        expect(page.get_by_role('heading', name=meetings[0]['title'], exact=True)).to_be_visible()
        page.get_by_role('button', name='Summary & decisions', exact=True).click()
        page.evaluate('window.scrollTo(0, 0)'); page.screenshot(path=str(OUTPUT / 'meeting-desktop.png'), full_page=True)
        page.emulate_media(media='print')
        expect(page.locator('.mp-print-report')).to_be_visible()
        expect(page.locator('.mp-print-report')).to_have_css('color', 'rgb(17, 24, 39)')
        expect(page.locator('.mp-print-report')).to_have_css('background-color', 'rgb(255, 255, 255)')
        expect(page.locator('.mp-app')).not_to_be_visible()
        page.pdf(path=str(OUTPUT / 'meeting-report.pdf'), format='A4', margin=dict(top='20mm', bottom='20mm', left='18mm', right='18mm'))
        page.emulate_media(media='screen')
        page.get_by_role('button', name='Review tools', exact=True).click()
        expect(page.get_by_role('button', name='Generate draft', exact=True)).to_be_enabled()
        page.get_by_role('button', name='Generate draft', exact=True).click()
        assert any(path.endswith('/review/artifacts') and method == 'POST' for method, path, body in writes)
        page.evaluate('window.scrollTo(0, 0)'); page.screenshot(path=str(OUTPUT / 'review-desktop.png'), full_page=True)
        page.get_by_role('button', name='Settings', exact=True).click()
        page.get_by_role('button', name='Bot Voice', exact=True).click()
        expect(page.get_by_role('combobox')).to_have_value('piper')
        page.evaluate('window.scrollTo(0, 0)'); page.screenshot(path=str(OUTPUT / 'settings-desktop.png'), full_page=True)
        nav.get_by_role('button', name='People & access', exact=True).click()
        page.evaluate('window.scrollTo(0, 0)'); page.screenshot(path=str(OUTPUT / 'team-desktop.png'), full_page=True)
        # Role controls remain constrained after the redesign.
        role[0] = 'member'; page.reload()
        nav.get_by_role('button', name='Meetings', exact=True).click()
        expect(page.get_by_role('button', name='Delete Customer onboarding sync', exact=True)).to_have_count(0)
        expect(page.get_by_role('button', name='Delete Product & engineering review', exact=True)).to_be_visible()
        nav.get_by_role('button', name='Action items', exact=True).click()
        expect(page.get_by_role('button', name='New action', exact=True)).to_have_count(0)
        expect(page.get_by_role('heading', name='Finalize the onboarding flow', exact=True)).to_have_count(0)
        assert page.locator('.mp-nav').get_by_role('button', name='Integrations', exact=True).count() == 0
        page.set_viewport_size(dict(width=390, height=844))
        page.get_by_role('button', name='Open navigation', exact=True).click()
        page.locator('.mp-nav').get_by_role('button', name='Overview', exact=True).click()
        expect(page.locator('.mp-sidebar')).not_to_have_class('mp-sidebar is-open')
        page.wait_for_function('document.querySelector(".mp-sidebar").getBoundingClientRect().right < 1')
        page.evaluate('window.scrollTo(0, 0)'); page.screenshot(path=str(OUTPUT / 'overview-mobile.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), page.evaluate('''() => [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1 && getComputedStyle(e).position !== 'fixed').slice(0,20).map(e => ({tag:e.tagName, cls:e.className, right:e.getBoundingClientRect().right}))''')
        page.evaluate('window.scrollTo(0, 0)'); page.screenshot(path=str(OUTPUT / 'overview-mobile.png'), full_page=True)
        page.get_by_role('button', name='Open navigation', exact=True).click()
        page.get_by_role('button', name='Settings', exact=True).click()
        page.get_by_role('button', name='Appearance', exact=True).click()
        page.get_by_role('radio', name='Rose', exact=True).check()
        expect(page.locator('html')).to_have_attribute('data-palette', 'rose')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(OUTPUT / 'appearance-mobile.png'), full_page=True)
        page.get_by_role('radio', name='Blue & purple', exact=True).check()
        page.get_by_role('button', name='Open navigation', exact=True).click()
        page.locator('.mp-nav').get_by_role('button', name='Overview', exact=True).click()
        page.get_by_role('button', name='Join meeting', exact=True).click()
        expect(page.get_by_role('dialog', name='Join a live meeting', exact=True)).to_be_visible()
        page.evaluate('window.scrollTo(0, 0)'); page.screenshot(path=str(OUTPUT / 'join-mobile.png'), full_page=True)
        page.keyboard.press('Escape')
        expect(page.get_by_role('dialog')).to_have_count(0)
        page.goto(ROOT + '/?signedOut=1')
        expect(page.get_by_role('heading', name='Better meetings. Clearer next steps.')).to_be_visible()
        page.evaluate('window.scrollTo(0, 0)'); page.screenshot(path=str(OUTPUT / 'landing-mobile.png'), full_page=True)
        page.set_viewport_size(dict(width=1440, height=1000))
        page.evaluate('window.scrollTo(0, 0)'); page.screenshot(path=str(OUTPUT / 'landing-desktop.png'), full_page=True)
        page.get_by_role('button', name='Product guide', exact=True).first.click()
        expect(page.get_by_role('dialog')).to_be_visible()
        page.keyboard.press('Escape')
        page.get_by_role('button', name='Switch to light mode', exact=True).click()
        expect(page.locator('.mp-landing')).to_have_css('background-color', 'rgb(245, 241, 232)')
        # No storage permission is required to switch the current tab's appearance.
        restricted = browser.new_context()
        restricted.add_init_script("Object.defineProperty(window, 'localStorage', {get() {throw new DOMException('Blocked', 'SecurityError')}})")
        restricted_page = restricted.new_page()
        restricted_page.goto(ROOT + '/?signedOut=1')
        expect(restricted_page.locator('html')).to_have_attribute('data-theme', 'dark')
        restricted_page.get_by_role('button', name='Switch to light mode', exact=True).click()
        expect(restricted_page.locator('html')).to_have_attribute('data-theme', 'light')
        restricted.close()
        # Saved theme applies even before the React module can execute.
        prepaint = browser.new_context()
        prepaint.add_init_script("localStorage.setItem('meetpilot:theme', 'dark'); localStorage.setItem('meetpilot:palette', 'rose')")
        prepaint.route('**/src/main.tsx', lambda route: route.abort())
        initial_page = prepaint.new_page()
        initial_page.goto(ROOT)
        expect(initial_page.locator('html')).to_have_attribute('data-theme', 'dark')
        expect(initial_page.locator('html')).to_have_attribute('data-palette', 'rose')
        prepaint.close()
        # Callback completes a server exchange once and rejects unsolicited returns.
        page.goto(ROOT + '/app')
        page.evaluate('''() => sessionStorage.setItem('meetpilot:oauth:google', JSON.stringify({state:'fixture-nonce', workspaceId:'22222222-2222-4222-8222-222222222222', actorId:'fixture-clerk-user', createdAt:Date.now()}))''')
        page.goto(ROOT + '/oauth/google/callback?state=fixture-nonce&code=fixture-code')
        expect(page.get_by_role('heading', name='You’re connected.', exact=True)).to_be_visible()
        assert len([1 for method, path, body in writes if path == '/api/v1/integrations/google/callback']) == 1
        assert 'fixture-code' not in page.url
        page.goto(ROOT + '/oauth/zoom/callback?state=unsolicited&code=fixture-code')
        expect(page.get_by_role('heading', name='Connection wasn’t completed.', exact=True)).to_be_visible()
        assert not any(path == '/api/v1/integrations/zoom/callback' for method, path, body in writes)
        assert not errors, errors
        assert not unmatched, unmatched
        print(json.dumps(dict(result='passed', screenshots=str(OUTPUT.resolve()), mutations=len(writes), browser_errors=errors)))
        browser.close()

if __name__ == '__main__': run()
