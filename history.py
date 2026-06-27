import json
import os
import threading
import time
import psutil

_data = []
_LOCK = threading.Lock()
_SAMPLER_THREAD = None
_STOP = threading.Event()
_DATA_PATH = None

INTERVAL = 5
RETENTION_DAYS = 7
FLUSH_EVERY = 12

_RANGE_SECONDS = {
    '1h': 3600,
    '6h': 21600,
    '24h': 86400,
    '7d': 604800,
}

_AVG_FIELDS = [
    'cpu', 'mem_percent', 'mem_used', 'disk_percent',
    'disk_read_rate', 'disk_write_rate',
    'net_sent_rate', 'net_recv_rate',
    'net_bytes_sent', 'net_bytes_recv',
    'gpu_usage', 'gpu_temp',
]


def _data_path():
    global _DATA_PATH
    if _DATA_PATH is None:
        _DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'history.json')
    return _DATA_PATH


def init_store():
    global _data
    try:
        with open(_data_path(), 'r', encoding='utf-8') as f:
            _data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _data = []
    _trim()
    print(f'[history] loaded {len(_data)} points from {_data_path()}')


def _trim():
    cutoff = time.time() - RETENTION_DAYS * 86400
    with _LOCK:
        _data[:] = [p for p in _data if p['ts'] >= cutoff]


def _flush():
    tmp = _data_path() + '.tmp'
    with _LOCK:
        snapshot = list(_data)
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f)
    os.replace(tmp, _data_path())


def _sample_once(prev):
    now = time.time()
    per_core = psutil.cpu_percent(interval=0.1, percpu=True)
    cpu = round(sum(per_core) / len(per_core), 1) if per_core else 0.0
    mem = psutil.virtual_memory()
    net = psutil.net_io_counters()
    dio = psutil.disk_io_counters()

    dr = wr = ns = nr = 0.0
    if prev is not None and dio is not None and prev.get('dio') is not None:
        dt = now - prev['ts']
        if dt > 0:
            pd = prev['dio']
            pn = prev['net']
            dr = max(0.0, (dio.read_bytes - pd.read_bytes) / dt / 1024)
            wr = max(0.0, (dio.write_bytes - pd.write_bytes) / dt / 1024)
            ns = max(0.0, (net.bytes_sent - pn.bytes_sent) / dt / 1024)
            nr = max(0.0, (net.bytes_recv - pn.bytes_recv) / dt / 1024)

    total = used = 0
    seen_devs = set()
    for part in psutil.disk_partitions(all=True):
        if part.fstype in ('', 'tmpfs', 'devtmpfs', 'proc', 'sysfs', 'squashfs', 'overlay', 'cgroup', 'cgroup2', 'mqueue', 'hugetlbfs', 'debugfs', 'tracefs', 'fusectl', 'configfs', 'securityfs', 'pstore', 'bpf', 'autofs', 'ramfs', 'devpts', 'none', 'binfmt_misc', 'nsfs', 'fuse.gvfsd-fuse', 'fuse.snapfuse'):
            continue
        if 'cdrom' in part.opts or part.fstype == 'iso9660':
            continue
        if part.device in seen_devs:
            continue
        try:
            u = psutil.disk_usage(part.mountpoint)
            total += u.total
            used += u.used
            seen_devs.add(part.device)
        except Exception:
            pass
    disk_percent = round(used / total * 100, 1) if total > 0 else 0.0

    gpu_usage = None
    gpu_temp = None
    try:
        import gpu as _gpu
        gpus = _gpu.get_gpus()
        if gpus:
            gpu_usage = gpus[0].get('usage')
            gpu_temp = gpus[0].get('temperature')
    except Exception:
        pass

    point = {
        'ts': int(now),
        'cpu': cpu,
        'mem_percent': round(mem.percent, 1),
        'mem_used': mem.used,
        'disk_percent': disk_percent,
        'disk_read_rate': round(dr, 1),
        'disk_write_rate': round(wr, 1),
        'net_sent_rate': round(ns, 1),
        'net_recv_rate': round(nr, 1),
        'net_bytes_sent': net.bytes_sent,
        'net_bytes_recv': net.bytes_recv,
        'gpu_usage': gpu_usage,
        'gpu_temp': gpu_temp,
    }
    with _LOCK:
        _data.append(point)
    return {'ts': now, 'dio': dio, 'net': net}


def _sampler_loop():
    init_store()
    prev = None
    flush_count = 0
    while not _STOP.is_set():
        try:
            prev = _sample_once(prev)
            flush_count += 1
            if flush_count >= FLUSH_EVERY:
                _trim()
                _flush()
                flush_count = 0
        except Exception as e:
            print(f'[history] sample error: {e}')
        _STOP.wait(INTERVAL)
    _flush()


def start_sampler():
    global _SAMPLER_THREAD
    if _SAMPLER_THREAD is not None and _SAMPLER_THREAD.is_alive():
        return
    _STOP.clear()
    _SAMPLER_THREAD = threading.Thread(target=_sampler_loop, daemon=True, name='history-sampler')
    _SAMPLER_THREAD.start()
    print(f'[history] sampler started (interval={INTERVAL}s, retention={RETENTION_DAYS}d, flush_every={FLUSH_EVERY} samples)')


def stop_sampler():
    _STOP.set()


def query_history(range_key='1h'):
    secs = _RANGE_SECONDS.get(range_key, 3600)
    bucket = {3600: 60, 21600: 300, 86400: 1800, 604800: 7200}.get(secs, 60)
    since = int(time.time()) - secs
    with _LOCK:
        pts = [p for p in _data if p['ts'] >= since]
    if not pts:
        return {'range': range_key, 'points': [], 'count': 0, 'bucket': bucket}

    buckets = {}
    for p in pts:
        bt = (p['ts'] // bucket) * bucket
        buckets.setdefault(bt, []).append(p)

    out = []
    for bt in sorted(buckets.keys()):
        grp = buckets[bt]
        row = {'ts': (bt + bucket // 2) * 1000}
        for f in _AVG_FIELDS:
            vals = [p[f] for p in grp if p.get(f) is not None]
            if vals:
                v = sum(vals) / len(vals)
                row[f] = round(v, 1) if isinstance(vals[0], float) else int(v)
            else:
                row[f] = None
        out.append(row)
    return {'range': range_key, 'points': out, 'count': len(out), 'bucket': bucket}
