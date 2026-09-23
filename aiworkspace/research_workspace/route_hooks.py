"""Optional local Claude hooks. Merge settings, preserve user hooks, never read transcripts."""
from __future__ import annotations
import json
from pathlib import Path
import shlex
import sys
from .model import WorkspaceError, now, pretty, require
from .store import Store, atomic_write, file_hash, project_lock, read_text, safe_path
from .routing import capture

SETTINGS = '.claude/settings.local.json'
RECEIPT = '.rw/auto-route-hooks.json'
EVENTS = ('SessionStart', 'UserPromptSubmit', 'PostToolUse', 'Stop', 'PreCompact')


def configure(store: Store, *, approve: bool = False, remove: bool = False) -> dict:
    path = safe_path(store.root, SETTINGS, governed=False)
    receipt_path = safe_path(store.root, RECEIPT, governed=False)
    old_text = read_text(path) if path.exists() else None
    config = json.loads(old_text) if old_text else {}
    require(isinstance(config, dict), 'Claude local settings must be a JSON object.')
    hooks = config.setdefault('hooks', {})
    require(isinstance(hooks, dict), 'Invalid hooks settings; leave them unchanged and inspect manually.')
    command = ' '.join(shlex.quote(x) for x in (Path(sys.executable).as_posix(), '-I', '-m', 'research_workspace',
                                               '--project', store.root.as_posix(), 'route', '--hook'))
    old_receipt = json.loads(read_text(receipt_path)) if receipt_path.exists() else {}
    old_command = old_receipt.get('command')
    if remove and not old_command:
        return {'action': 'remove', 'changed': False, 'applied': False, 'message': 'No recorded auto-route hooks to remove.'}
    # Remove only exactly recorded handlers. Unrelated configuration remains intact.
    for event in EVENTS:
        entries = hooks.get(event, [])
        require(isinstance(entries, list), 'Invalid event entries: ' + event)
        kept = []
        for entry in entries:
            require(isinstance(entry, dict) and isinstance(entry.get('hooks'), list), 'Invalid hook group.')
            require(all(isinstance(h, dict) for h in entry['hooks']), 'Invalid hook handler.')
            handlers = [h for h in entry['hooks'] if not old_command or h.get('command') != old_command]
            if handlers: kept.append({**entry, 'hooks': handlers})
        if not remove:
            handler = {'type': 'command', 'command': command, 'timeout': 30}
            if not any(h.get('command') == command for entry in kept for h in entry['hooks']):
                entry = {'hooks': [handler]}
                if event == 'PostToolUse': entry['matcher'] = 'Write|Edit|MultiEdit|Bash'
                kept.append(entry)
        if kept: hooks[event] = kept
        else: hooks.pop(event, None)
    if not hooks: config.pop('hooks', None)
    new_text = pretty(config)
    report = {'action': 'remove' if remove else 'install', 'settings': str(path), 'command': command,
              'events': list(EVENTS), 'changed': new_text != old_text, 'applied': False,
              'boundary': 'Local capture only; no network, transcript ingestion, model invocation, scientific approval or blocking Stop loop.'}
    if not approve: return {**report, 'preserved_other_settings': True, 'next': 'Inspect the command and permissions, then pass --approve.'}
    if new_text == old_text: return report
    with project_lock(store.root):
        require((read_text(path) if path.exists() else None) == old_text, 'Settings changed concurrently; retry.')
        require(not safe_path(store.root, '.rw/transaction.json', governed=False).exists() and
                not safe_path(store.root, '.rw/update-transaction.json', governed=False).exists(), 'Recover project transaction first.')
        # Before/after backup is durable before settings are written. A crash cannot lose
        # the original configuration; restore it only after inspecting subsequent edits.
        backup = {'command': None if remove else command, 'previous_command': old_command,
                  'before': old_text, 'after': new_text, 'at': now(), 'settings': SETTINGS}
        atomic_write(receipt_path, pretty(backup))
        atomic_write(path, new_text)
    return {**report, 'applied': True, 'backup': str(receipt_path),
            'next': 'Restart the host and verify its hooks are active. Review existing hook policy before processing private research.'}


def _handle(root: str | Path, stream=None) -> dict:
    """Do not echo hook input, prompts, tool arguments, or transcript paths."""
    stream = stream or sys.stdin
    raw = stream.read(65537)
    require(len(raw.encode('utf-8')) <= 65536, 'Hook input exceeds 64 KB.')
    data = json.loads(raw)
    require(isinstance(data, dict) and data.get('hook_event_name') in EVENTS, 'Unsupported hook event.')
    event = data['hook_event_name']
    result = capture(Store(root), 'auto-route:claude-hook')
    output = {'suppressOutput': True}
    if event in ('SessionStart', 'UserPromptSubmit', 'PostToolUse') and result.get('pending_tasks') and (result.get('captured') or event != 'PostToolUse'):
        output['hookSpecificOutput'] = {'hookEventName': event, 'additionalContext':
            'Auto-route has pending local change records. Read workspace/skills/auto-route/SKILL.md and run rw route status. '
            'Handle relevant routed tasks within the user request. Preserve unresolved scientific decisions; never forge human verification. '
            'Capture is not completion; report only substantive blockers to the user.'}
    # Stop and PreCompact only persist. They never block, restart or recursively request
    # another assistant turn, including when stop_hook_active is true.
    return output


def handle(root: str | Path, stream=None) -> dict:
    try:
        return _handle(root, stream)
    except (WorkspaceError, OSError, ValueError, TypeError, KeyError):
        return {'suppressOutput': True, 'systemMessage':
                'Auto-route capture failed; edits remain unprocessed. Run rw route to inspect and recover. No scientific state was auto-approved.'}
