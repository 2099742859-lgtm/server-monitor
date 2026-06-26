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
MAX_POINTS_QUERY = 300
FLUSH_EVERY = 12

_RANGE_SECONDS = {
    '1h': 3600,
    '6h': 21600,
    '24h': 86400,
    '7d': 604800,
}


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
    for part in psutil.disk_partitions(all=True):
        if part.fstype in ('', 'tmpfs', 'devtmpfs', 'proc', 'sysfs', 'squashfs', 'overlay'):
            continue
        if 'cdrom' in part.opts or part.fstype == 'iso9660':
            continue
        try:
            u = psutil.disk_usage(part.mountpoint)
            total += u.total
            used += u.used
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
    since = int(time.time()) - secs
    with _LOCK:
        pts = [p for p in _data if p['ts'] >= since]
    if len(pts) > MAX_POINTS_QUERY:
        step = len(pts) // MAX_POINTS_QUERY
        pts = pts[::step]
    out = [{'ts': p['ts'] * 1000, **{k: v for k, v in p.items() if k != 'ts'}} for p in pts]
    return {'range': range_key, 'points': out, 'count': len(out)}
