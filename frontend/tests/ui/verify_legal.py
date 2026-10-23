"""Policy routes and actual acknowledgment/capture UI with fixture auth and APIs."""
import json
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect
from verify_workspace import actor, workspace, meetings, members

ROOT = 'http://127.0.0.1:3011'
OUTPUT = Path('scratch/frontend-legal')
OUTPUT.mkdir(parents=True, exist_ok=True)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=dict(width=1440, height=1000))
        state = dict(accepted=False, fail=False, bundle='policy-1', version='2026-10-12.1')
        writes, errors, reads, operations = [], [], [], []
        def route_api(route):
            request = route.request
            path = urlparse(request.url).path
            metadata = dict(versions=dict(terms=state['version'], privacy=state['version'], recording=state['version']), operator=dict(name='', address='', privacy_email='', jurisdiction='', processing='', retention=''), published=False, bundle=state['bundle'])
            status, data = 200, []
            if path == '/api/v1/legal/policies': data = metadata
            elif path == '/api/v1/legal/acceptance':
                if state['fail']: status, data = 503, dict(detail='Policy service unavailable')
                elif request.method == 'POST':
                    payload = request.post_data_json
                    writes.append(payload)
                    if payload['bundle'] != state['bundle']: status, data = 409, dict(detail='Policies changed. Review the current pages and acknowledge them again.')
                    else: state['accepted'], data = True, dict(accepted=True, accepted_at='2026-10-12T10:00:00Z', bundle=state['bundle'], accepted_versions=metadata['versions'])
                else:
                    reads.append(path)
                    data = dict(policies=metadata, accepted=state['accepted'], accepted_at='2026-10-12T10:00:00Z' if state['accepted'] else None, accepted_versions=dict(terms='2026-10-12.1', privacy='2026-10-12.1', recording='2026-10-12.1') if state['accepted'] else None)
            elif path == '/api/v1/auth/me': data = dict(authenticated=True, user=dict(id=actor, name='Alex Morgan', email='alex@example.test'))
            elif path == '/api/v1/workspaces': data = [dict(id=workspace, name='Legal test workspace', owner_id=actor, current_role='owner')]
            elif path == '/api/v1/meetings': data = meetings
            elif path.endswith('/members'): data = members
            elif path == '/api/v1/tasks' and request.method == 'POST':
                operations.append(path)
                data = {**request.post_data_json, 'id': 'new-action', 'status': 'todo'}
            elif path.endswith('/analytics'): data = dict(total_meetings=4, total_duration_seconds=1440, pending_tasks=0, completed_tasks=0, speaking_time_by_member=[])
            route.fulfill(status=status, content_type='application/json', body=json.dumps(data), headers={'Access-Control-Allow-Origin': ROOT, 'Access-Control-Allow-Headers': '*'})
        context.route('http://localhost:8000/**', route_api)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        # Public documents must stay public for both signed-out and signed-in users.
        for suffix in ['?signedOut=1', '']:
            for path, title in [('terms', 'Terms of Service'), ('privacy', 'Privacy Policy'), ('recording-policy', 'Recording Policy')]:
                page.goto(f'{ROOT}/{path}{suffix}')
                expect(page.get_by_role('heading', name=title, exact=True)).to_be_visible()
                expect(page.get_by_label('Policy publication status')).to_contain_text('Pre-launch draft')
                expect(page.locator('.mp-legal-copy')).to_contain_text('Not finalized')
                assert urlparse(page.url).path == '/' + path
        page.goto(ROOT + '/terms')
        page.locator('.mp-legal-main > nav').get_by_role('link', name='Privacy Policy', exact=True).click()
        expect(page.get_by_role('heading', name='Privacy Policy', exact=True)).to_be_visible()
        page.go_back()
        expect(page.get_by_role('heading', name='Terms of Service', exact=True)).to_be_visible()
        page.screenshot(path=str(OUTPUT / 'terms-dark.png'), full_page=True)
        page.get_by_role('button', name='Switch to light mode').click()
        page.screenshot(path=str(OUTPUT / 'terms-light.png'), full_page=True)
        page.emulate_media(media='print')
        expect(page.locator('.mp-public-header')).to_be_hidden()
        expect(page.get_by_role('heading', name='Terms of Service', exact=True)).to_be_visible()
        page.emulate_media(media='screen')
        page.goto(ROOT + '/app')
        expect(page.locator('.mp-sidebar')).to_be_visible()
        expect(page.get_by_role('dialog')).to_have_count(0)
        assert not reads and not writes, 'Entry must not check or prompt for acknowledgment'
        page.get_by_role('button', name='Join meeting', exact=True).click()
        prompt = page.get_by_role('dialog', name='Before your first action')
        expect(prompt).to_be_visible()
        expect(page.get_by_role('dialog', name='Join a live meeting')).to_have_count(0)
        prompt.get_by_role('button', name='Not now').click()
        expect(page.get_by_role('dialog')).to_have_count(0)
        assert not writes, 'Cancelling must not agree or run the action'
        page.get_by_role('button', name='Join meeting', exact=True).click()
        expect(prompt).to_be_visible()
        button = page.get_by_role('button', name='Agree & continue', exact=True)
        expect(button).to_be_disabled()
        box = prompt.get_by_role('checkbox')
        box.check()
        page.screenshot(path=str(OUTPUT / 'acknowledgment.png'), full_page=True)
        # Before first acceptance, reject a stale document snapshot.
        state['bundle'] = 'policy-2'
        button.click()
        expect(page.get_by_role('alert')).to_contain_text('Policies changed')
        page.get_by_role('button', name='Reload policies').click()
        expect(box).not_to_be_checked()
        box.check()
        button.click()
        expect(page.get_by_role('dialog', name='Join a live meeting')).to_be_visible()
        expect(prompt).to_have_count(0)
        assert writes[-1] == dict(bundle='policy-2', terms_agreed=True, privacy_acknowledged=True, recording_responsibilities_acknowledged=True)
        # No repeated recording checkbox remains after the one-time agreement.
        dialog = page.get_by_role('dialog', name='Join a live meeting')
        dialog.get_by_placeholder('https://meet.google.com/abc-defg-hij').fill('https://meet.google.com/abc-defg-hij')
        expect(dialog.get_by_role('checkbox')).to_have_count(0)
        expect(dialog.get_by_role('button', name='Join meeting', exact=True)).to_be_enabled()
        page.keyboard.press('Escape')
        page.get_by_role('button', name='Record', exact=True).click()
        dialog = page.get_by_role('dialog', name='Record a meeting')
        expect(dialog.get_by_role('checkbox')).to_have_count(0)
        expect(dialog.get_by_role('button', name='Start Recording', exact=True)).to_be_enabled()
        page.keyboard.press('Escape')
        page.get_by_role('button', name='Upload', exact=True).first.click()
        dialog = page.get_by_role('dialog', name='Upload a meeting recording')
        dialog.locator('input[type=file]').set_input_files(dict(name='test.wav', mimeType='audio/wav', buffer=b'test'))
        expect(dialog.get_by_role('checkbox')).to_have_count(0)
        expect(dialog.get_by_role('button', name='Upload & Process')).to_be_enabled()
        page.keyboard.press('Escape')
        # Re-login/reload and even a new document version must not reprompt.
        state['bundle'], state['version'] = 'future-policy', 'future-version'
        page.reload()
        expect(page.locator('.mp-sidebar')).to_be_visible()
        page.get_by_role('button', name='Join meeting', exact=True).click()
        expect(page.get_by_role('dialog', name='Join a live meeting')).to_be_visible()
        expect(prompt).to_have_count(0)
        page.keyboard.press('Escape')
        page.get_by_role('button', name='Settings', exact=True).click()
        expect(page.get_by_label('Trust and policies')).to_contain_text('No further prompts')
        expect(page.get_by_label('Trust and policies').get_by_role('link', name='Terms of Service')).to_be_visible()
        # First-use errors block only the requested action, not dashboard entry.
        state['version'] = '2026-10-12.1'
        state['accepted'], state['fail'] = False, True
        page.reload()
        expect(page.locator('.mp-sidebar')).to_be_visible()
        expect(prompt).to_have_count(0)
        page.get_by_role('button', name='Record', exact=True).click()
        expect(page.get_by_role('alert')).to_contain_text('Policy service unavailable')
        expect(page.get_by_role('dialog', name='Record a meeting')).to_have_count(0)
        state['fail'] = False
        page.get_by_role('button', name='Reload policies').click()
        expect(page.locator('.mp-legal-checks')).to_be_visible()
        page.set_viewport_size(dict(width=390, height=844))
        page.screenshot(path=str(OUTPUT / 'acknowledgment-mobile.png'), full_page=True)
        prompt.get_by_role('button', name='Not now').click()
        # Other work is deferred at the API boundary, with form contents intact.
        page.set_viewport_size(dict(width=1440, height=1000))
        page.locator('.mp-nav').get_by_role('button', name='Action items', exact=True).click()
        page.get_by_role('button', name='New action', exact=True).click()
        task_dialog = page.get_by_role('dialog', name='New action item')
        task_dialog.get_by_placeholder('What needs to happen?').fill('Review the first-use flow')
        task_dialog.get_by_role('button', name='Create action').click()
        expect(prompt).to_be_visible()
        assert not operations, 'The task must not be submitted before agreement'
        # Escape affects only the topmost prompt and keeps the draft underneath.
        page.keyboard.press('Escape')
        expect(prompt).to_have_count(0)
        expect(task_dialog.get_by_placeholder('What needs to happen?')).to_have_value('Review the first-use flow')
        task_dialog.get_by_role('button', name='Create action').click()
        prompt.get_by_role('checkbox').check()
        prompt.get_by_role('button', name='Agree & continue').click()
        expect(task_dialog).to_have_count(0)
        assert operations == ['/api/v1/tasks'], operations
        page.set_viewport_size(dict(width=390, height=844))
        page.goto(ROOT + '/privacy?signedOut=1')
        expect(page.get_by_role('heading', name='Privacy Policy', exact=True)).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Policy page overflows mobile viewport'
        page.screenshot(path=str(OUTPUT / 'privacy-mobile.png'), full_page=True)
        assert not errors, errors
        browser.close()
        print('PASS: no signup/entry prompt, first-action resume/cancel, once per account across revisions, Settings, deferred task, capture forms, public pages, print and mobile')


if __name__ == '__main__':
    run()
