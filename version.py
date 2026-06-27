import io
import json
import os
import shutil
import tarfile
import urllib.request

VERSION = "v1.1.2"
REPO = "2099742859-lgtm/server-monitor"

_MIRRORS = {
    'github': 'https://github.com/{repo}/archive/refs/tags/{tag}.tar.gz',
    'ghproxy': 'https://ghproxy.com/https://github.com/{repo}/archive/refs/tags/{tag}.tar.gz',
    'moeyy': 'https://github.moeyy.xyz/https://github.com/{repo}/archive/refs/tags/{tag}.tar.gz',
    'kkgithub': 'https://kkgithub.com/{repo}/archive/refs/tags/{tag}.tar.gz',
}

_MIRROR_ORDER = ['github', 'ghproxy', 'moeyy', 'kkgithub']


def _fetch(url, timeout=15, allow_proxy=True):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'server-monitor',
        'Accept': 'application/vnd.github.v3+json',
    })
    # Try direct first
    try:
        opener = urllib.request.build_opener()
        return opener.open(req, timeout=timeout)
    except Exception:
        pass
    if not allow_proxy:
        raise Exception(f"Cannot reach {url}")
    # Try environment proxies
    for var in ('HTTPS_PROXY', 'HTTP_PROXY', 'https_proxy', 'http_proxy'):
        v = os.environ.get(var)
        if v:
            try:
                handler = urllib.request.ProxyHandler({'http': v, 'https': v})
                opener = urllib.request.build_opener(handler)
                return opener.open(req, timeout=timeout)
            except Exception:
                continue
    # Try common local proxies (dev machine only)
    for p in ['http://127.0.0.1:7897', 'http://127.0.0.1:1080']:
        try:
            handler = urllib.request.ProxyHandler({'http': p, 'https': p})
            opener = urllib.request.build_opener(handler)
            return opener.open(req, timeout=timeout)
        except Exception:
            continue
    raise Exception(f"Cannot reach {url}")


def get_releases():
    try:
        resp = _fetch(f"https://api.github.com/repos/{REPO}/releases?per_page=30")
        data = json.loads(resp.read())
        return [{
            'tag': r['tag_name'],
            'name': r['name'] or r['tag_name'],
            'date': r['published_at'],
            'body': (r.get('body') or '')[:500],
        } for r in data]
    except Exception as e:
        return []


def check_updates():
    releases = get_releases()
    latest = releases[0]['tag'] if releases else None
    return {
        'current': VERSION,
        'latest': latest,
        'has_update': latest is not None and latest != VERSION,
        'releases': releases,
    }


def _backup(script_dir):
    backup_dir = script_dir + '.backup'
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)
    shutil.copytree(script_dir, backup_dir, dirs_existorder=False,
                    ignore=shutil.ignore_patterns('.venv', '__pycache__', 'history.json', '.git'))
    return backup_dir


def _restore(backup_dir, script_dir):
    if not os.path.exists(backup_dir):
        return False
    shutil.rmtree(script_dir, ignore_errors=True)
    shutil.copytree(backup_dir, script_dir, dirs_existorder=False,
                    ignore=shutil.ignore_patterns('.backup'))
    return True


def perform_update(tag, script_dir, mirror='github'):
    backup_dir = _backup(script_dir)
    try:
        mirrors_to_try = [mirror]
        for m in _MIRROR_ORDER:
            if m not in mirrors_to_try:
                mirrors_to_try.append(m)

        data = None
        errors = []
        for m in mirrors_to_try:
            template = _MIRRORS.get(m, _MIRRORS['github'])
            url = template.format(repo=REPO, tag=tag)
            try:
                resp = _fetch(url, timeout=60)
                data = resp.read()
                break
            except Exception as e:
                errors.append(f"{m}: {e}")
                continue

        if data is None:
            _restore(backup_dir, script_dir)
            return False, f"All mirrors failed: {'; '.join(errors)}"

        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
            for m in tar.getmembers():
                parts = m.name.split('/', 1)
                if len(parts) > 1 and parts[1]:
                    m.name = parts[1]
                    tar.extract(m, script_dir)

        shutil.rmtree(backup_dir, ignore_errors=True)
        return True, f"Updated to {tag}"
    except Exception as e:
        _restore(backup_dir, script_dir)
        return False, f"Update failed, rolled back: {e}"
