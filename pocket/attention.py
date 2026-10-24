"""A deliberately non-live reading queue for public agent discussions.

No network, no posting, no private data; planning and receipt comparison only.
A human or agent still chooses which connections and ideas deserve attention.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

SCHEMA = 'puter.attention.v1'
ID = re.compile(r'^[0-9a-f]{32}$')
PUTER_FINGERPRINT = 'ef32e3f5f6dbc621c0265c4c25eeabe5d798978faf7483bd0e89c5470719c042'


def load(path: str | Path) -> dict:
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    if raw.get('schema') != SCHEMA or not isinstance(raw.get('threads'), list):
        raise ValueError('unrecognized attention queue schema')
    ids = [x.get('id') for x in raw['threads']]
    if len(ids) != len(set(ids)) or not all(isinstance(i, str) and ID.fullmatch(i) for i in ids):
        raise ValueError('duplicate or invalid thread ids')
    return raw


def plan(data: dict, today: str, limit: int = 3) -> dict:
    """Always budget 2 historic reviews before 1 recent when available.

    Historic means original post at least 10 days old; ranking is by whether
    a thread has never been examined and when a revisit is due, not its likes.
    """
    day = date.fromisoformat(today)
    eligible = [t for t in data['threads'] if t.get('status', 'open') == 'open'
                and (not t.get('next_due') or date.fromisoformat(t['next_due']) <= day)]
    older = [t for t in eligible if date.fromisoformat(t['created_on']) <= day - timedelta(days=10)]
    recent = [t for t in eligible if t not in older]
    key = lambda t: (t.get('last_read') is not None,
                     t.get('next_due') or '0000-01-01',
                     t.get('last_read') or '', t['created_on'], t['id'])
    older.sort(key=key)
    recent.sort(key=key)
    selected = older[:min(2, limit)]
    selected += recent[:max(0, limit - len(selected))]
    if len(selected) < limit:
        selected += [t for t in older if t not in selected][:limit-len(selected)]
    if len(selected) < limit:
        selected += [t for t in recent if t not in selected][:limit-len(selected)]
    return {'as_of': today, 'rule': 'historic-first (2), recent (1); no popularity ranking',
            'selected': [{'id': t['id'], 'title': t['title'], 'url': t['url'],
                          'reason': t['follow_for'], 'last_read': t.get('last_read')}
                         for t in selected],
            'historic_selected': sum(date.fromisoformat(t['created_on']) <= day - timedelta(days=10)
                                     for t in selected),
            'due_remaining': len(eligible) - len(selected)}


def record(data: dict, root_id: str, thread_response: dict, today: str,
           observation: str = '') -> tuple[dict, dict]:
    """Record a completed full public-thread read; never infer unseen messages.

    Initial reading establishes a baseline, not a new notification.
    Subsequent reads report newly observed IDs and text edits separately.
    """
    date.fromisoformat(today)
    if thread_response.get('ok') is not True:
        raise ValueError('thread read did not succeed')
    meta = thread_response.get('data') or {}
    if meta.get('root_id') != root_id or meta.get('has_more') is True:
        raise ValueError('wrong root or incomplete thread pagination')
    messages = thread_response.get('messages')
    if not isinstance(messages, list) or not messages or messages[0].get('id') != root_id:
        raise ValueError('missing or invalid root message')
    updated = deepcopy(data)
    matches = [t for t in updated['threads'] if t['id'] == root_id]
    if len(matches) != 1:
        raise ValueError('thread not in discovery queue')
    target = matches[0]
    hashes = {}
    for msg in messages:
        mid, body = msg.get('id'), msg.get('text')
        if not isinstance(mid, str) or not ID.fullmatch(mid) or not isinstance(body, str) or mid in hashes:
            raise ValueError('invalid, duplicate, or incomplete message')
        hashes[mid] = hashlib.sha256(body.encode('utf-8')).hexdigest()
    earlier = target.get('fingerprints')
    baseline = earlier is None
    previous = earlier or {}
    new = sorted(set(hashes) - set(previous)) if not baseline else []
    own_new = sorted(msg['id'] for msg in messages
                     if msg.get('author') == PUTER_FINGERPRINT and msg['id'] in new)
    new = sorted(set(new) - set(own_new))
    edited = sorted(i for i in hashes.keys() & previous.keys() if hashes[i] != previous[i])
    missing = sorted(set(previous) - set(hashes)) if not baseline else []
    target['fingerprints'] = dict(sorted(hashes.items()))
    target['last_read'] = today
    target['next_due'] = (date.fromisoformat(today) + timedelta(days=7 if new or edited or missing else 14)).isoformat()
    if observation:
        if len(observation) > 500:
            raise ValueError('observation exceeds 500 characters')
        target['observation'] = observation
    event = {'id': root_id, 'at': today, 'baseline': baseline, 'new_ids': new,
             'edited_ids': edited, 'missing_ids': missing, 'self_ids': own_new,
             'message_count': len(hashes)}
    updated.setdefault('visits', []).append(event)
    updated['visits'] = updated['visits'][-100:]
    return updated, event


def save(path: str | Path, data: dict) -> None:
    """Atomic local save; caller coordinates any cross-process edits."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError('queue symlink unsupported')
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode()
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent, prefix='.attention-', delete=False) as h:
            tmp = Path(h.name)
            h.write(content)
            h.flush()
            os.fsync(h.fileno())
        os.replace(tmp, path)
        tmp = None
        parent = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description='Historical-first public reading queue, offline')
    cli.add_argument('queue')
    command = cli.add_subparsers(dest='action', required=True)
    next_cmd = command.add_parser('next')
    next_cmd.add_argument('--date', default=date.today().isoformat())
    next_cmd.add_argument('--limit', type=int, default=3)
    review_cmd = command.add_parser('record')
    review_cmd.add_argument('id')
    review_cmd.add_argument('read_thread_json')
    review_cmd.add_argument('--date', default=date.today().isoformat())
    review_cmd.add_argument('--observation', default='')
    args = cli.parse_args(argv)
    if args.action == 'next':
        result = plan(load(args.queue), args.date, args.limit)
    else:
        raw = json.loads(Path(args.read_thread_json).read_text(encoding='utf-8'))
        updated, result = record(load(args.queue), args.id, raw, args.date, args.observation)
        save(args.queue, updated)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
