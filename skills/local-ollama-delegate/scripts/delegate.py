"""Standard-library local delegation; generated code requires master review."""
import argparse
import ast
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / 'assets' / 'config.json'
SYSTEM = '''You are a local coding worker. Implement exactly ONE small Python file.
Return only complete Python code, without markdown or commentary. Follow the task at
the END of this prompt. Preserve existing APIs. Include correct imports. Use integer
arithmetic for money. Do not invent APIs or requirements. You have no tools and must
not claim tests were run. The master owns transactions, integration and verification.
Output must be concise; no extra accessors, scaffolding or unrelated tests.'''
BLOCKED = {'.git', '.aws', '.codex', '.agents', '.env', 'node_modules', '.venv', 'venv', '__pycache__', '.local-delegation'}

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')

def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None

def contained(root, name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Use relative paths with forward slashes')
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or any(p in BLOCKED for p in relative.parts):
        raise ValueError('Path escapes scope or selects protected metadata: ' + name)
    resolved = (Path(root) / relative).resolve()
    if not resolved.is_relative_to(Path(root).resolve()):
        raise ValueError('Symlink/path escapes project: ' + name)
    return resolved

def config(path=DEFAULT_CONFIG):
    value = read_json(path)
    parsed = urllib.parse.urlsplit(value['endpoint'])
    if parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1', '::1') or parsed.username or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise ValueError('Endpoint must be a local Ollama HTTP service')
    for name in ('num_ctx', 'num_predict', 'max_context_chars', 'max_output_lines', 'timeout_seconds'):
        if type(value[name]) is not int or value[name] <= 0:
            raise ValueError(name + ' must be a positive integer')
    if value['num_predict'] >= value['num_ctx']:
        raise ValueError('Output budget must leave room for input')
    if type(value['max_repairs']) is not int or not 0 <= value['max_repairs'] <= 1:
        raise ValueError('This workflow supports zero or one repair')
    return value

def call(settings, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(settings['endpoint'].rstrip('/') + path, data=data,
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=settings['timeout_seconds']) as response:
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise ValueError('Ollama response exceeds artifact budget')
    return json.loads(raw)

def options(settings):
    return {key: settings[key] for key in ('num_ctx', 'num_predict', 'temperature', 'seed')}

def doctor(settings, smoke=False):
    tags = call(settings, '/api/tags')
    selected = next((m for m in tags['models'] if m['name'] == settings['model']), None)
    if selected is None:
        raise ValueError('Configured model is not installed: ' + settings['model'])
    capacity = selected.get('details', {}).get('context_length')
    if capacity is not None and settings['num_ctx'] > capacity:
        raise ValueError('Requested context exceeds advertised model context')
    result = {'model': settings['model'], 'model_digest': selected['digest'], 'settings': options(settings)}
    if smoke:
        response = call(settings, '/api/generate', {'model': settings['model'],
            'prompt': 'Reply with exactly READY.', 'stream': False,
            'options': dict(options(settings), num_predict=32)})
        if not response.get('done') or response.get('response', '').strip() != 'READY':
            raise ValueError('Inference smoke failed: ' + response.get('response', '')[:120])
        result['smoke'] = 'passed'
    result['runtime'] = call(settings, '/api/ps')
    return result

def validate_task(task, project):
    required = {'id', 'kind', 'scope', 'goal', 'target', 'context', 'snapshot_paths', 'constraints', 'acceptance', 'baseline_commands', 'test_commands'}
    if set(task) != required:
        raise ValueError('Task fields must be exactly: ' + ', '.join(sorted(required)))
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', task['id']):
        raise ValueError('Task id must be a short lowercase identifier')
    if task['kind'] not in ('helper', 'tests') or task['scope'] != 'unit':
        raise ValueError('Split broad feature work into a unit helper or a few tests')
    if not isinstance(task['goal'], str) or not task['goal'].strip():
        raise ValueError('Specify a concrete goal')
    if contained(project, task['target']).suffix != '.py':
        raise ValueError('This runner currently supports one Python output file')
    for key in ('constraints', 'acceptance'):
        if not isinstance(task[key], list) or len(task[key]) < (2 if key == 'acceptance' else 1) or not all(isinstance(x, str) and x.strip() for x in task[key]):
            raise ValueError('Provide explicit ' + key)
    if not task['context'] or not task['snapshot_paths']:
        raise ValueError('Provide narrow source context and snapshot paths')
    for entry in task['context']:
        if not isinstance(entry, dict) or set(entry) - {'path', 'start', 'end'} or 'path' not in entry:
            raise ValueError('Context entries need path and optional start/end')
        source = contained(project, entry['path'])
        if source.suffix != '.py' or not source.is_file():
            raise ValueError('Context must select existing Python source')
    for key in ('baseline_commands', 'test_commands'):
        if not isinstance(task[key], list) or not task[key] or not all(isinstance(c, list) and c and all(isinstance(a, str) and a for a in c) for c in task[key]):
            raise ValueError(key + ' must contain explicit command arrays')

def execute_commands(commands, folder, log_folder, prefix):
    results = []
    log_folder.mkdir(parents=True, exist_ok=True)
    for index, command in enumerate(commands):
        stdout = log_folder / f'{prefix}-{index}-stdout.txt'
        stderr = log_folder / f'{prefix}-{index}-stderr.txt'
        started = time.monotonic()
        with stdout.open('w', encoding='utf-8') as out, stderr.open('w', encoding='utf-8') as err:
            try:
                process = subprocess.run(command, cwd=folder, stdout=out, stderr=err, timeout=60, shell=False)
                code = process.returncode
            except subprocess.TimeoutExpired:
                code = 124; err.write('\nCommand exceeded 60-second limit.\n')
            except OSError as exc:
                code = 127; err.write(str(exc))
        results.append({'command': command, 'returncode': code, 'seconds': round(time.monotonic()-started, 3),
                        'stdout': str(stdout), 'stderr': str(stderr)})
        if code: break
    return results

def snapshot(project, task, folder):
    hashes = {}; total = 0
    for name in task['snapshot_paths']:
        source = contained(project, name)
        if not source.exists(): raise ValueError('Snapshot source missing: ' + name)
        candidates = list(source.rglob('*.py')) if source.is_dir() else [source]
        for item in candidates:
            relative = item.relative_to(project).as_posix()
            if any(part in BLOCKED for part in item.relative_to(project).parts): continue
            contained(project, relative)
            total += item.stat().st_size
            if total > 2_000_000: raise ValueError('Snapshot too large; select narrower paths')
            target = folder / relative; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, target); hashes[relative] = file_digest(item)
    for entry in task['context']:
        if entry['path'] not in hashes: raise ValueError('Context file must be included in snapshot: ' + entry['path'])
    return hashes

def build_prompt(task, frozen):
    sources = []
    for entry in task['context']:
        lines = contained(frozen, entry['path']).read_text(encoding='utf-8').splitlines()
        start = entry.get('start', 1); end = entry.get('end', len(lines))
        if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
            raise ValueError('Invalid inclusive source line range')
        sources.append(f"FILE {entry['path']} lines {start}-{end}\n" + '\n'.join(lines[start-1:end]))
    source_text = '\n\n'.join(sources)
    contract = {key: task[key] for key in ('id', 'kind', 'goal', 'target', 'constraints', 'acceptance')}
    return source_text + '\n\nYOUR ONLY TASK:\n' + json.dumps(contract, indent=2), len(source_text)

def normalize_answer(raw, settings, stop_reason):
    if stop_reason != 'stop': raise ValueError('Incomplete generation: ' + str(stop_reason))
    value = raw.strip()
    fence = re.fullmatch(r'```(?:python)?\s*\n(.*?)\n```', value, re.S)
    if fence: value = fence.group(1)
    if not value or len(value.splitlines()) > settings['max_output_lines']:
        raise ValueError('Empty or oversized answer; narrow the assignment')
    ast.parse(value)
    return value.rstrip() + '\n'

def persist_meta(folder, meta):
    write_json(folder / 'meta.json', meta)

def load_run(folder):
    folder = Path(folder).resolve(); meta = read_json(folder / 'meta.json')
    project = Path(meta['project']).resolve()
    expected = project / '.local-delegation' / 'runs'
    if folder.parent != expected or not folder.name.startswith('run-'):
        raise ValueError('Run directory does not match recorded project')
    return folder, meta, project

def generate(folder, meta, settings, feedback=None):
    task = read_json(folder / 'task.json')
    prompt, source_chars = build_prompt(task, folder / 'snapshot')
    if source_chars > settings['max_context_chars']: raise ValueError('Source exceeds context budget')
    if feedback is not None:
        prompt += '\n\nPREVIOUS PROPOSAL:\n' + (folder / 'previous-proposal.txt').read_text(encoding='utf-8')
        prompt += '\n\nREPAIR ONLY THE REPORTED ERRORS:\n' + feedback[:4000]
    estimated = math.ceil((len(SYSTEM) + len(prompt)) / 3)
    if estimated + settings['num_predict'] + 256 > settings['num_ctx']:
        raise ValueError('Estimated input/output exceed context allocation; reduce source/task')
    write_json(folder / 'request.json', {'model': settings['model'], 'system': SYSTEM, 'prompt': prompt,
                                       'stream': False, 'options': options(settings)})
    (folder / 'prompt.txt').write_text(SYSTEM + '\n\n' + prompt, encoding='utf-8')
    started = time.monotonic()
    try:
        response = call(settings, '/api/generate', read_json(folder / 'request.json'))
        write_json(folder / 'response.json', response)
        meta['local'] = {key: response.get(key) for key in ('prompt_eval_count', 'eval_count', 'done_reason', 'total_duration', 'load_duration', 'eval_duration')}
        meta['local']['wall_seconds'] = round(time.monotonic()-started, 3)
        meta['runtime'] = call(settings, '/api/ps')
        raw = response.get('response', '')
        (folder / 'raw-answer.txt').write_text(raw, encoding='utf-8')
        # Save source even if syntax/length fails, so one repair has concrete input.
        (folder / 'previous-proposal.txt').write_text(raw, encoding='utf-8')
        code = normalize_answer(raw, settings, response.get('done_reason'))
        (folder / 'proposal.py').write_text(code, encoding='utf-8')
        meta['proposal_hash'] = file_digest(folder / 'proposal.py')
        meta['status'] = 'ready_for_review'
    except Exception as exc:
        meta['status'] = 'needs_repair'; meta['error'] = str(exc)
    persist_meta(folder, meta)
    return {'run': str(folder), 'status': meta['status'], 'error': meta.get('error'), 'local': meta.get('local')}

def start_run(task_path, project, settings):
    project = Path(project).resolve()
    if not project.is_dir(): raise ValueError('Project must be an existing directory')
    task = read_json(task_path); validate_task(task, project)
    prerequisites = doctor(settings)
    parent = project / '.local-delegation' / 'runs'
    if not parent.resolve().is_relative_to(project): raise ValueError('Artifact directory escapes project')
    parent.mkdir(parents=True, exist_ok=True)
    folder = parent / ('run-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:8])
    folder.mkdir()
    meta = {'id': task['id'], 'project': str(project), 'settings': settings, 'attempt': 0,
            'created_at': datetime.now(timezone.utc).isoformat(), 'status': 'preparing', 'outcome': None,
            'target_original_hash': file_digest(contained(project, task['target']))}
    write_json(folder / 'task.json', task); write_json(folder / 'prerequisites.json', prerequisites)
    try:
        meta['baseline_hashes'] = snapshot(project, task, folder / 'snapshot')
        results = execute_commands(task['baseline_commands'], project, folder / 'logs', 'baseline')
        write_json(folder / 'baseline-checks.json', results)
        if any(item['returncode'] for item in results): raise ValueError('Baseline checks failed; model request not sent')
        if any(file_digest(contained(project,name)) != value for name,value in meta['baseline_hashes'].items()):
            raise ValueError('Baseline command changed source; review changes before dispatch')
        persist_meta(folder, meta)
        return generate(folder, meta, settings)
    except Exception as exc:
        meta['status'] = 'blocked_before_generation'; meta['error'] = str(exc); persist_meta(folder, meta)
        return {'run': str(folder), 'status': meta['status'], 'error': str(exc)}

def verify(folder):
    folder, meta, project = load_run(folder); task = read_json(folder / 'task.json')
    if meta['status'] in ('superseded','applied') or meta.get('outcome') == 'rejected':
        raise ValueError('This run is no longer active')
    if not (folder / 'proposal.py').is_file(): raise ValueError('No valid proposal to review; repair or reject')
    candidate = folder / 'candidate'
    if not candidate.exists():
        shutil.copytree(folder / 'snapshot', candidate)
        target = contained(candidate, task['target']); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(folder / 'proposal.py', target)
    target = contained(candidate, task['target'])
    ast.parse(target.read_text(encoding='utf-8'))
    results = execute_commands(task['test_commands'], candidate, folder / 'logs', 'verify')
    write_json(folder / 'checks.json', results)
    modified = [name for name, expected in meta['baseline_hashes'].items()
                if name != task['target'] and file_digest(contained(candidate, name)) != expected]
    if any(item['returncode'] for item in results) or modified:
        meta['status'] = 'needs_repair'; meta['error'] = 'Checks failed or baseline files modified: ' + ', '.join(modified)
        meta.pop('verified_hash', None)
    else:
        meta['status'] = 'verified'; meta['verified_hash'] = file_digest(target); meta.pop('error', None)
    # Changing/rechecking a candidate invalidates any prior outcome decision.
    meta['outcome'] = None
    persist_meta(folder, meta)
    return {'run': str(folder), 'status': meta['status'], 'checks': results, 'modified_baseline': modified}

def repair(folder, feedback_path):
    folder, meta, project = load_run(folder)
    if meta['status'] != 'needs_repair' or meta.get('outcome') is not None:
        raise ValueError('Repair requires a failed, unfinished attempt')
    if meta['attempt'] >= meta['settings']['max_repairs']: raise ValueError('Repair budget exhausted; primary agent should finish')
    feedback = Path(feedback_path).read_text(encoding='utf-8').strip()
    if not feedback: raise ValueError('Supply concrete errors')
    parent = folder.parent; new = parent / ('run-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:8])
    new.mkdir(); shutil.copytree(folder / 'snapshot', new / 'snapshot')
    shutil.copyfile(folder / 'task.json', new / 'task.json')
    previous = folder / 'candidate' / read_json(folder / 'task.json')['target']
    if not previous.exists(): previous = folder / 'previous-proposal.txt'
    if not previous.exists(): raise ValueError('No proposal available; reject failed transport request')
    shutil.copyfile(previous, new / 'previous-proposal.txt')
    newer = dict(meta, attempt=meta['attempt'] + 1, parent_run=str(folder), status='preparing', outcome=None,
                 created_at=datetime.now(timezone.utc).isoformat())
    for key in ('local', 'runtime', 'error', 'proposal_hash', 'verified_hash'): newer.pop(key, None)
    meta['status'] = 'superseded'; meta['child_run'] = str(new); persist_meta(folder, meta)
    persist_meta(new, newer)
    (new / 'feedback.txt').write_text(feedback, encoding='utf-8')
    return generate(new, newer, newer['settings'], feedback)

def finish(folder, outcome, reason, review_minutes=0, primary_usage_units=None):
    folder, meta, project = load_run(folder)
    if meta['status'] in ('superseded', 'applied'): raise ValueError('Finish the active attempt; applied runs retain their decision')
    if not reason.strip(): raise ValueError('Record review evidence')
    if outcome != 'rejected':
        target = folder / 'candidate' / read_json(folder / 'task.json')['target']
        if meta['status'] != 'verified' or file_digest(target) != meta.get('verified_hash'):
            raise ValueError('Reverify candidate before recording acceptance')
        changed = file_digest(target) != meta['proposal_hash']
        if changed != (outcome == 'accepted_with_changes'):
            raise ValueError('Use accepted_with_changes exactly when the candidate differs from the worker proposal')
    for value in (review_minutes, primary_usage_units):
        if value is not None and (not math.isfinite(value) or value < 0): raise ValueError('Usage/time must be finite and nonnegative')
    meta.update(outcome=outcome, reason=reason, review_minutes=review_minutes, primary_usage_units=primary_usage_units)
    persist_meta(folder, meta)
    return {'run': str(folder), 'outcome': outcome}

def apply(folder):
    folder, meta, project = load_run(folder); task = read_json(folder / 'task.json')
    candidate = contained(folder / 'candidate', task['target']); target = contained(project, task['target'])
    if meta.get('outcome') not in ('accepted', 'accepted_with_changes') or meta['status'] != 'verified' or file_digest(candidate) != meta.get('verified_hash'):
        raise ValueError('Apply requires an accepted, unchanged verified candidate')
    if file_digest(target) != meta['target_original_hash']: raise ValueError('Target changed since generation; refusing overwrite')
    for name, expected in meta['baseline_hashes'].items():
        if file_digest(contained(project, name)) != expected: raise ValueError('Baseline changed since generation: ' + name)
    if target.exists(): shutil.copyfile(target, folder / 'target-before-apply.py')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidate, target); meta['status'] = 'applied'; persist_meta(folder, meta)
    return {'applied': str(target), 'run': str(folder)}

def report(project):
    parent = Path(project).resolve() / '.local-delegation' / 'runs'
    runs = [read_json(path) for path in sorted(parent.glob('run-*/meta.json'))]
    return {'attempts': len(runs), 'root_tasks': sum(r.get('attempt') == 0 for r in runs),
            'outcomes': {name: sum(r.get('outcome') == name for r in runs) for name in ('accepted', 'accepted_with_changes', 'rejected')},
            'local_prompt_tokens': sum(r.get('local', {}).get('prompt_eval_count') or 0 for r in runs),
            'local_output_tokens': sum(r.get('local', {}).get('eval_count') or 0 for r in runs),
            'local_seconds': round(sum(r.get('local', {}).get('wall_seconds') or 0 for r in runs), 3),
            'recorded_review_minutes': sum(r.get('review_minutes', 0) for r in runs),
            'primary_usage_units_entered': sum(r.get('primary_usage_units') or 0 for r in runs),
            'primary_usage_entries': sum(r.get('primary_usage_units') is not None for r in runs),
            'net_primary_usage_saved': None,
            'note': 'Local tokens are not avoided cloud tokens. Net savings require a matched primary-only usage baseline.'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('doctor'); p.add_argument('--smoke', action='store_true')
    p = commands.add_parser('run'); p.add_argument('task', type=Path); p.add_argument('--project', type=Path, required=True)
    p = commands.add_parser('repair'); p.add_argument('run', type=Path); p.add_argument('--feedback', type=Path, required=True)
    for name in ('verify', 'apply'):
        p = commands.add_parser(name); p.add_argument('run', type=Path); p.add_argument('--reviewed', action='store_true', required=True)
    p = commands.add_parser('finish'); p.add_argument('run', type=Path)
    p.add_argument('--outcome', choices=['accepted', 'accepted_with_changes', 'rejected'], required=True)
    p.add_argument('--reason', required=True); p.add_argument('--review-minutes', type=float, default=0)
    p.add_argument('--primary-usage-units', type=float)
    p = commands.add_parser('report'); p.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'doctor': result = doctor(config(args.config), args.smoke)
        elif args.command == 'run': result = start_run(args.task, args.project, config(args.config))
        elif args.command == 'verify': result = verify(args.run)
        elif args.command == 'repair': result = repair(args.run, args.feedback)
        elif args.command == 'finish': result = finish(args.run, args.outcome, args.reason, args.review_minutes, args.primary_usage_units)
        elif args.command == 'apply': result = apply(args.run)
        else: result = report(args.project)
        print(json.dumps(result, indent=2))
        if result.get('status') in ('needs_repair', 'blocked_before_generation'): return 2
        return 0
    except Exception as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr); return 1

if __name__ == '__main__': sys.exit(main())
