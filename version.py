import io
import json
import os
import tarfile
import urllib.request

VERSION = "v1.1.1"
REPO = "2099742859-lgtm/server-monitor"

_MIRRORS = {
    'github': 'https://github.com/{repo}/archive/refs/tags/{tag}.tar.gz',
    'ghproxy': 'https://ghproxy.com/https://github.com/{repo}/archive/refs/tags/{tag}.tar.gz',
    'moeyy': 'https://github.moeyy.xyz/https://github.com/{repo}/archive/refs/tags/{tag}.tar.gz',
    'kkgithub': 'https://kkgithub.com/{repo}/archive/refs/tags/{tag}.tar.gz',
}


def _fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'server-monitor',
        'Accept': 'application/vnd.github.v3+json',
    })
    proxies = [None]
    for var in ('HTTPS_PROXY', 'HTTP_PROXY', 'https_proxy', 'http_proxy'):
        v = os.environ.get(var)
        if v and v not in proxies:
            proxies.append(v)
    proxies.extend(['http://127.0.0.1:7897', 'http://127.0.0.1:1080'])
    last_err = None
    for p in proxies:
        try:
            if p:
                handler = urllib.request.ProxyHandler({'http': p, 'https': p})
                opener = urllib.request.build_opener(handler)
            else:
                opener = urllib.request.build_opener()
            return opener.open(req, timeout=timeout)
        except Exception as e:
            last_err = e
            continue
    raise last_err


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


def perform_update(tag, script_dir, mirror='github'):
    template = _MIRRORS.get(mirror, _MIRRORS['github'])
    url = template.format(repo=REPO, tag=tag)
    resp = _fetch(url, timeout=120)
    data = resp.read()

    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
        for m in tar.getmembers():
            parts = m.name.split('/', 1)
            if len(parts) > 1 and parts[1]:
                m.name = parts[1]
                tar.extract(m, script_dir)

    return True, f"Updated to {tag}"
