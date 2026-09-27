"""Read-only conversation menu. Works directly before the framework is installed.

The agent performs semantic interpretation and authorized operations. This helper
never executes selections, calls a model/network, modifies a study, or reads secrets.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
import unicodedata

CATALOG = Path(__file__).parent / 'assets/menu.json'
MAX_BYTES = 8 * 1024 * 1024
HELP = {'菜单', '功能菜单', '帮助', '帮助菜单', 'help', 'menu', '开始', '有哪些功能', '返回菜单'}

class MenuError(ValueError):
    """Safe, user-readable navigation failure."""

def _read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise MenuError('无法安全读取本地项目资料；请由 agent 检查文件权限和格式。')
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise MenuError('项目资料无法解析；保留原文件，先检查或恢复。') from exc
    if not isinstance(value, dict):
        raise MenuError('项目资料格式异常；请先检查，勿重新初始化已有论文。')
    return value

def catalog() -> dict:
    data = _read(CATALOG)
    if data.get('menu_version') != 1 or not isinstance(data.get('items'), list):
        raise MenuError('菜单版本无法识别，请由 agent 检查框架版本。')
    numbers = [i.get('number') for i in data['items'] if isinstance(i, dict)]
    if len(numbers) != 10 or set(numbers) != set('0123456789'):
        raise MenuError('菜单编号不完整，请由 agent 修复框架文件。')
    return data

def _normalize(value: str) -> str:
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value)).casefold()

def resolve_selection(text: str, *, in_menu: bool = False) -> dict:
    """Exact controls only. Free text stays with the host, never a shell dispatcher."""
    if not isinstance(text, str) or len(text.encode('utf-8')) > 8000:
        raise MenuError('请用一句话描述要做的事。')
    value = _normalize(text).strip('。.!！?？')
    data = catalog()
    if value in {_normalize(h) for h in HELP} or not value:
        return {'kind': 'menu', 'execute': False}
    if value in ('返回', '取消', '算了', 'cancel', 'back'):
        return {'kind': 'cancel', 'execute': False,
                'instruction': 'Cancel only pending work; keep completed changes and report them honestly.'}
    if value in ('继续', 'continue', '接着做'):
        return {'kind': 'resume', 'execute': False,
                'instruction': 'Read the current project and unfinished tasks. Ask once if the intended project/task is ambiguous.'}
    numeric = re.fullmatch(r'(?:我选|选择|选|第)?([0-9])(?:项|个)?', value)
    if numeric and in_menu:
        item = next(i for i in data['items'] if i['number'] == numeric.group(1))
        return {'kind': 'selection', 'execute': False, 'item': item}
    for item in data['items']:
        if value in {_normalize(v) for v in [item['id'], item['title'], *item['aliases']]}:
            return {'kind': 'selection', 'execute': False, 'item': item}
    # Do not echo arbitrary input: it could contain private text or credentials.
    return {'kind': 'free_text', 'execute': False,
            'instruction': 'The agent interprets the actual request using workspace-guide and auto-route. Do not force an exact menu label.'}

def project_summary(location: str | Path | None = None) -> dict:
    explicit = location is not None
    start = Path(location).expanduser() if explicit else Path.cwd()
    if start.is_symlink():
        raise MenuError('请选择论文的真实目录，避免使用符号链接入口。')
    if not start.is_dir():
        raise MenuError('指定目录不存在；请确认论文位置，不会自动创建或切换项目。')
    start = start.resolve()
    roots = [start] if explicit else [start, *start.parents]
    root = None
    for candidate in roots:
        folder = candidate / 'workspace'
        state_file = folder / 'state.json'
        if folder.is_symlink() or state_file.is_symlink():
            raise MenuError('项目状态指向符号链接；停止读取并检查路径。')
        if state_file.exists():
            root = candidate
            break
    if root is None:
        return {'state': 'not_selected', 'label': '未选择论文',
                'next': '可以新建论文，或通过“项目与设置”打开已有论文。'}
    state = _read(root / 'workspace/state.json')
    if state.get('schema_version') != 1 or not isinstance(state.get('project'), dict):
        raise MenuError('当前研究格式需要检查；请保留旧项目，由 agent 处理兼容性。')
    if any(not isinstance(state.get(key), typ) for key, typ in (('tasks', list), ('issues', dict))):
        raise MenuError('项目待办资料不完整；不会把读取失败显示成“没有问题”。')
    tasks = state['tasks']
    issues = list(state['issues'].values())
    if not all(isinstance(t, dict) for t in tasks + issues):
        raise MenuError('项目待办格式异常；请由 agent 检查。')
    name = state['project'].get('name')
    if not isinstance(name, str) or not name.strip():
        raise MenuError('项目名称缺失；请先检查现有研究状态。')
    return {'state': 'selected', 'label': name, 'project': str(root),
            'open_tasks': sum(t.get('status') == 'open' for t in tasks),
            'open_issues': sum(i.get('status') == 'open' for i in issues),
            'quality': '未在菜单中重新审查',
            'boundary': 'Read-only summary; task counts do not establish submission readiness.'}

def _display(text: str) -> str:
    """Project names are untrusted data, not Markdown or instructions."""
    text = ' '.join(text.split())[:120]
    for char in ('\\', '`', '*', '_', '[', ']', '|', '<', '>', '#'):
        text = text.replace(char, '\\' + char)
    return text

def render(summary: dict | None = None) -> str:
    data = catalog()
    current = summary or {'state': 'not_selected', 'label': '未选择论文'}
    lines = ['## ' + data['title'], '', '**当前论文：' + _display(current['label']) + '**']
    if current['state'] == 'selected':
        lines.append(f"待办 {current['open_tasks']} 项 · 未解决问题 {current['open_issues']} 项 · 本次尚未重新审查")
    else:
        lines.append('可以新建论文，或打开已经写过的论文。')
    lines += ['', '| 选择 | 功能 |', '|---|---|']
    lines += [f"| {i['number']} | {i['title']} |" for i in data['items']]
    lines += ['', data['description'],
              '例如：“选 1，我想开始一篇会议论文”或“直接帮我改摘要”。',
              '输入“菜单”可返回这里；目标明确时可直接办理。',
              '本地读写和执行需由已授权的 agent 提供；登录与必要权限由你确认。']
    return '\n'.join(lines) + '\n'

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', help='Explicit study root; omitted means current directory or its ancestors only')
    parser.add_argument('--select', help='Exact menu reply, alias, or free text; never executed')
    parser.add_argument('--menu-reply', action='store_true', help='Interpret a standalone number only after a menu has actually been shown')
    parser.add_argument('--json', action='store_true', help='Machine-readable read-only context for the agent')
    args = parser.parse_args(argv)
    try:
        summary = project_summary(args.project)
        selection = resolve_selection(args.select, in_menu=args.menu_reply) if args.select is not None else None
        if args.json or selection:
            output = {'context': summary, 'menu': catalog(), 'selection': selection, 'side_effects': []}
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(render(summary), end='')
        return 0
    except (MenuError, OSError) as exc:
        print(json.dumps({'error': str(exc), 'preserved_project': True}, ensure_ascii=False), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
