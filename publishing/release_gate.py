#!/usr/bin/env python3
"""Puter's reusable, owner-authorized NIP-5A release gate.

Source-only approval. Never reads NIP-46 credentials, signs or publishes.
The pinned GitHub Action and nsyte do the network work after this gate passes.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import time

REPOSITORY = 'br3avery-maker/Puters_SwarmMemo'
INBOX_ISSUE = 11
SCHEMA = 'puter.nsite-release.v1'
EXPECTED_PUTER_PUBKEY = 'ab71b3f86d3428d62530dbe7344995188eaa8197db23b3a45c3eb3cac6ae3e45'
RELAYS = ('wss://relay.nsite.lol',)
# Two servers succeeded in real run #44881156605. The older candidates failed.
SERVERS = ('https://nostr.download', 'https://blossom.primal.net')
ID = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?\Z')
SITE = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,11}[a-z0-9])?\Z')
HEX = re.compile(r'[0-9a-f]{64}\Z')
REQUEST = re.compile(r'/publish-release ([a-z0-9-]+) sha256:([0-9a-f]{64})\Z')
SEGMENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*\Z')
BANNED = {'.git', '.github', 'node_modules', 'publishing', '.nsite', '.puter-publication',
          '__pycache__', 'dist-info', 'venv', '.venv', '.env', '.npmrc', '.pypirc'}
MAX_FILES = 3000
MAX_BYTES = 250_000_000
MAX_RELEASE_BYTES = 600_000


class ReleaseError(ValueError):
    """Failed closed before accessing a signer."""


def digest(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    with path.open('rb') as src:
        for part in iter(lambda: src.read(1024 * 1024), b''):
            h.update(part)
            n += len(part)
    return h.hexdigest(), n


def canonical_dir(root: Path, directory: str) -> Path:
    if not isinstance(directory, str) or not directory or '\\' in directory or '${{' in directory:
        raise ReleaseError('invalid directory')
    p = PurePosixPath(directory)
    if p.is_absolute() or any(not SEGMENT.fullmatch(x) or x in BANNED for x in p.parts):
        raise ReleaseError('directory must be a safe repository-relative static output path')
    if p.as_posix() != directory:
        raise ReleaseError('directory path is not canonical')
    at = root
    for piece in p.parts:
        at /= piece
        if at.is_symlink():
            raise ReleaseError('symlinked output folder is not allowed')
    if not at.is_dir() or not at.resolve().is_relative_to(root.resolve()):
        raise ReleaseError('output folder missing or outside repository')
    return at


def inspect_files(root: Path, directory: str) -> list[dict]:
    site = canonical_dir(root, directory)
    files, total = [], 0
    for p in sorted(site.rglob('*')):
        relative = p.relative_to(site)
        if p.is_symlink():
            raise ReleaseError('symlink in site: ' + relative.as_posix())
        if not p.is_file():
            continue
        if any(x in BANNED for x in relative.parts) or p.name.lower().startswith('.env') or p.name.lower().endswith(('.pem', '.key', '.p12', '.pfx')):
            raise ReleaseError('secret or development file inside site: ' + relative.as_posix())
        if any(x in ('.', '..', '') for x in relative.parts):
            raise ReleaseError('noncanonical site path')
        h, n = digest(p)
        total += n
        files.append({'path': relative.as_posix(), 'sha256': h, 'size': n})
        if len(files) > MAX_FILES or total > MAX_BYTES:
            raise ReleaseError('release exceeds bounded file-count/byte budget')
    if not files or not any(f['path'] == 'index.html' for f in files):
        raise ReleaseError('static release requires index.html')
    return files


def require_text(value: str, label: str, max_length: int) -> str:
    if not isinstance(value, str) or not (1 <= len(value) <= max_length):
        raise ReleaseError(f'{label} must be text of 1–{max_length} characters')
    if any(ord(x) < 32 or ord(x) == 127 for x in value) or '${{' in value:
        raise ReleaseError(f'{label} has forbidden control/interpolation sequence')
    return value


def make_release(root: Path, release_id: str, directory: str,
                 name: str, title: str, description: str) -> dict:
    if not ID.fullmatch(release_id) or not SITE.fullmatch(name):
        raise ReleaseError('invalid release ID or NIP-5A site name')
    return {
        'schema': SCHEMA,
        'release_id': release_id,
        'name': name,
        'directory': directory,
        'title': require_text(title, 'title', 180),
        'description': require_text(description, 'description', 350),
        'files': inspect_files(root, directory),
    }


def load_release(root: Path, release_id: str) -> tuple[dict, str]:
    if not isinstance(release_id, str) or not ID.fullmatch(release_id):
        raise ReleaseError('invalid release identifier')
    p = root / 'publishing' / 'releases' / (release_id + '.json')
    if p.is_symlink() or not p.is_file() or p.stat().st_size > MAX_RELEASE_BYTES:
        raise ReleaseError('missing, symlinked or oversized release record')
    sha, _ = digest(p)
    try:
        obj = json.loads(p.read_text(encoding='utf-8'))
    except (UnicodeError, json.JSONDecodeError) as e:
        raise ReleaseError('invalid release JSON') from e
    if not isinstance(obj, dict) or set(obj) != {'schema','release_id','name','directory','title','description','files'}:
        raise ReleaseError('unexpected release schema/fields')
    if obj['schema'] != SCHEMA or obj['release_id'] != release_id:
        raise ReleaseError('schema/release identifier mismatch')
    expected = make_release(root, obj['release_id'], obj['directory'], obj['name'], obj['title'], obj['description'])
    if obj != expected:
        raise ReleaseError('release inventory differs from source content or includes unlisted files')
    return obj, sha


def authorize(event_name: str, event: dict, ref: str, actor_id: str,
              triggering_actor: str) -> tuple[str, str]:
    repo = event.get('repository', {})
    owner = repo.get('owner', {})
    sender = event.get('sender', {})
    uid = owner.get('id')
    if (repo.get('full_name') != REPOSITORY or ref != 'refs/heads/main'
            or type(uid) is not int or uid <= 0 or str(uid) != str(actor_id)
            or not owner.get('login') or triggering_actor != owner['login']
            or sender.get('id') != uid or sender.get('type') != 'User'):
        raise ReleaseError('request is not from the repository owner on main')
    if event_name == 'issue_comment':
        issue, comment = event.get('issue', {}), event.get('comment', {})
        if (event.get('action') != 'created' or issue.get('number') != INBOX_ISSUE
                or 'pull_request' in issue or comment.get('author_association') != 'OWNER'
                or comment.get('user', {}).get('id') != uid
                or comment.get('user', {}).get('type') != 'User'):
            raise ReleaseError('not an authorized publish inbox comment')
        m = REQUEST.fullmatch(comment.get('body', ''))
        if m is None:
            raise ReleaseError('publish request syntax mismatch')
        release_id, sha = m.groups()
    elif event_name == 'workflow_dispatch':
        inp = event.get('inputs', {})
        release_id, sha = inp.get('release_id'), inp.get('manifest_sha256')
    else:
        raise ReleaseError('unsupported request event')
    if not isinstance(release_id, str) or not ID.fullmatch(release_id) or not isinstance(sha, str) or not HEX.fullmatch(sha):
        raise ReleaseError('invalid release ID or release-manifest SHA-256')
    return release_id, sha


def write_config(root: Path, release: dict) -> None:
    target = root / '.puter-publication'
    if target.exists() and target.is_symlink():
        raise ReleaseError('publication configuration directory must not be a symlink')
    target.mkdir(exist_ok=True)
    p = target / 'config.json'
    if p.is_symlink():
        raise ReleaseError('publication config must not be symlinked')
    config = {'relays': list(RELAYS), 'servers': list(SERVERS),
              'id': release['name'], 'title': release['title'],
              'description': release['description']}
    p.write_text(json.dumps(config, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')


def stage(root: Path, event_file: Path, env: dict) -> dict:
    event = json.loads(event_file.read_text(encoding='utf-8'))
    release_id, expected_digest = authorize(env['GITHUB_EVENT_NAME'], event, env['GITHUB_REF'],
                                            env['GITHUB_ACTOR_ID'], env['GITHUB_TRIGGERING_ACTOR'])
    release, actual_digest = load_release(root, release_id)
    if actual_digest != expected_digest:
        raise ReleaseError('approved release-manifest SHA-256 does not match checked-out main')
    write_config(root, release)
    outputs = {'release_id': release_id, 'site_name': release['name'],
               'directory': release['directory'], 'manifest_sha256': actual_digest,
               'file_count': str(len(release['files']))}
    out_path = env.get('GITHUB_OUTPUT')
    if out_path:
        with Path(out_path).open('a', encoding='utf-8') as out:
            for k, v in outputs.items():
                out.write(k + '=' + v + '\n')
    return outputs


def verify(root: Path, release_id: str, upstream: Path) -> None:
    """Independently download every published path through named Nostr manifest lookup."""
    release, _ = load_release(root, release_id)
    source = upstream / 'src' / 'cli.ts'
    config = upstream / 'deno.json'
    lock = upstream / 'deno.lock'
    if not all(p.is_file() for p in (source, config, lock)):
        raise ReleaseError('pinned nsyte source not checked out')
    with tempfile.TemporaryDirectory(prefix='puter-nsite-readback-') as tmp:
        tmpdir = Path(tmp)
        def fetch_one(entry: dict, index: int) -> str:
            remote = '/' + entry['path']
            target = tmpdir / f'{index:04d}-readback'
            args = ['deno', 'run', '-A', '--frozen', '--config', str(config), '--lock', str(lock),
                    str(source), 'get', remote, '--pubkey', EXPECTED_PUTER_PUBKEY,
                    '--name', release['name'], '--relays', ','.join(RELAYS),
                    '--servers', ','.join(SERVERS), '--output', str(target)]
            for attempt in range(3):
                try:
                    proc = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                          timeout=75, cwd=root, check=False)
                except subprocess.TimeoutExpired:
                    proc = None
                if proc is not None and proc.returncode == 0 and target.is_file():
                    downloaded_sha, downloaded_size = digest(target)
                    if downloaded_sha == entry['sha256'] and downloaded_size == entry['size']:
                        return remote
                target.unlink(missing_ok=True)
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
            raise ReleaseError('named-site path readback failed: ' + remote)
        # Per-file path verification, not just raw content-addressed blobs.
        # Threads share immutable checked-out bytes; each response has its own temporary file.
        with ThreadPoolExecutor(max_workers=4) as pool:
            tasks = [pool.submit(fetch_one, f, i) for i, f in enumerate(release['files'])]
            for f in as_completed(tasks):
                f.result()
    print(json.dumps({'status': 'VERIFIED', 'release_id': release_id,
                      'site_name': release['name'], 'files': len(release['files'])}, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    actions = parser.add_subparsers(dest='command', required=True)
    prepare = actions.add_parser('prepare')
    prepare.add_argument('--id', required=True)
    prepare.add_argument('--directory', required=True)
    prepare.add_argument('--name', required=True)
    prepare.add_argument('--title', required=True)
    prepare.add_argument('--description', required=True)
    v = actions.add_parser('validate')
    v.add_argument('--id', required=True)
    actions.add_parser('stage')
    verify_cmd = actions.add_parser('verify')
    verify_cmd.add_argument('--id', required=True)
    verify_cmd.add_argument('--upstream', type=Path, default=Path('.nsyte-upstream'))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == 'prepare':
            obj = make_release(root, args.id, args.directory, args.name, args.title, args.description)
            target = root / 'publishing' / 'releases' / (args.id + '.json')
            if target.exists():
                raise ReleaseError('release ID already exists; use a new ID for a new revision')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            sha, _ = digest(target)
            print('Release prepared. Commit assets and: ' + target.relative_to(root).as_posix())
            print(f'Authorization command: /publish-release {args.id} sha256:{sha}')
        elif args.command == 'validate':
            _, sha = load_release(root, args.id)
            print('VERIFIED release inventory ' + args.id + ' sha256:' + sha)
        elif args.command == 'stage':
            print(json.dumps(stage(root, Path(os.environ['GITHUB_EVENT_PATH']), os.environ), sort_keys=True))
        elif args.command == 'verify':
            verify(root, args.id, (root / args.upstream).resolve())
    except (ReleaseError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print('Release rejected: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
