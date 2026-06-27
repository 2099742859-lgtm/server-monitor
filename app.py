from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse
import psutil
import time
import os
import sys
import json
import math
import platform
import socket
from datetime import datetime, timezone

# Ensure script directory is in path (for embedded Python)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hardware
import gpu
import history
import version


# Cache hardware info that rarely changes (30 seconds)
_hardware_cache = {}
_hardware_cache_ttl = 30

# IO rate state
_io_state = {
    'last_time': 0,
    'last_disk': None,
    'last_net': None,
    'disk_rates': {'read': 0.0, 'write': 0.0},
    'net_rates': {'sent': 0.0, 'recv': 0.0}
}


def get_hardware_info():
    now = time.time()
    if 'data' in _hardware_cache and now - _hardware_cache.get('ts', 0) < _hardware_cache_ttl:
        return _hardware_cache['data']

    info = {
        'cpu_model': hardware.get_cpu_model(),
        'motherboard': hardware.get_motherboard(),
        'bios': hardware.get_bios(),
        'memory_modules': hardware.get_memory_modules(),
        'disk_drives': hardware.get_disk_drives(),
        'gpus': gpu.get_gpus(),
        'network_cards': hardware.get_network_cards(),
    }
    _hardware_cache['data'] = info
    _hardware_cache['ts'] = now
    return info


def get_io_rates(disk_io, net, now):
    """Compute disk/network rates in KB/s. Updates internal state."""
    state = _io_state
    dt = now - state['last_time']

    if state['last_disk'] is not None and state['last_net'] is not None and dt > 0:
        state['disk_rates']['read'] = max(0.0, (disk_io.read_bytes - state['last_disk'].read_bytes) / dt / 1024)
        state['disk_rates']['write'] = max(0.0, (disk_io.write_bytes - state['last_disk'].write_bytes) / dt / 1024)
        state['net_rates']['sent'] = max(0.0, (net.bytes_sent - state['last_net'].bytes_sent) / dt / 1024)
        state['net_rates']['recv'] = max(0.0, (net.bytes_recv - state['last_net'].bytes_recv) / dt / 1024)

    state['last_disk'] = disk_io
    state['last_net'] = net
    state['last_time'] = now
    return state['disk_rates'], state['net_rates']


def get_network_interfaces():
    interfaces = []
    try:
        for name, stats in psutil.net_io_counters(pernic=True).items():
            if 'Loopback' in name or 'Virtual' in name:
                continue
            interfaces.append({
                'name': name,
                'bytes_sent': stats.bytes_sent,
                'bytes_recv': stats.bytes_recv
            })
    except Exception:
        pass
    return interfaces


def get_metrics():
    # Single call to get per-core and average CPU usage
    per_core = psutil.cpu_percent(interval=0.1, percpu=True)
    cpu_percent = round(sum(per_core) / len(per_core), 1) if per_core else 0.0
    physical_cores = psutil.cpu_count(logical=False) or 0
    logical_cores = psutil.cpu_count(logical=True) or 0

    mem = psutil.virtual_memory()
    net = psutil.net_io_counters()
    disk_io = psutil.disk_io_counters()
    boot_time = psutil.boot_time()
    now = time.time()
    disk_rates, net_rates = get_io_rates(disk_io, net, now)

    # Aggregate all readable disk partitions
    partitions = []
    seen_devices = set()
    for part in psutil.disk_partitions(all=True):
        if part.fstype in ('', 'tmpfs', 'devtmpfs', 'proc', 'sysfs', 'squashfs', 'overlay', 'cgroup', 'cgroup2', 'mqueue', 'hugetlbfs', 'debugfs', 'tracefs', 'fusectl', 'configfs', 'securityfs', 'pstore', 'bpf', 'autofs', 'ramfs', 'devpts', 'none'):
            continue
        if 'cdrom' in part.opts or part.fstype == 'iso9660':
            continue
        if part.device in seen_devices:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                'device': part.device,
                'mountpoint': part.mountpoint,
                'fstype': part.fstype,
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': usage.percent
            })
            seen_devices.add(part.device)
        except Exception:
            pass

    # Aggregate totals across all partitions
    total_size = sum(p['total'] for p in partitions)
    used_size = sum(p['used'] for p in partitions)
    free_size = sum(p['free'] for p in partitions)
    disk_percent = round(used_size / total_size * 100, 1) if total_size > 0 else 0.0

    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            processes.append(proc.info)
        except Exception:
            pass
    processes = sorted(processes, key=lambda x: x.get('cpu_percent', 0), reverse=True)[:10]

    hw = get_hardware_info()

    return {
        'timestamp': now * 1000,
        'cpu': {
            'percent': cpu_percent,
            'per_core': per_core,
            'physical_cores': physical_cores,
            'logical_cores': logical_cores,
            'model': hw['cpu_model']
        },
        'memory': {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'percent': mem.percent,
            'free': mem.free,
            'modules': hw['memory_modules']
        },
        'disk': {
            'total': total_size,
            'used': used_size,
            'free': free_size,
            'percent': disk_percent,
            'partitions': partitions,
            'drives': hw['disk_drives'],
            'io': {
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
                'read_count': disk_io.read_count,
                'write_count': disk_io.write_count,
                'read_rate': disk_rates['read'],
                'write_rate': disk_rates['write']
            }
        },
        'network': {
            'bytes_sent': net.bytes_sent,
            'bytes_recv': net.bytes_recv,
            'packets_sent': net.packets_sent,
            'packets_recv': net.packets_recv,
            'sent_rate': net_rates['sent'],
            'recv_rate': net_rates['recv'],
            'interfaces': get_network_interfaces()
        },
        'gpu': {
            'gpus': hw['gpus'],
            'count': len(hw['gpus'])
        },
        'system': {
            'hostname': platform.node() or os.environ.get('COMPUTERNAME', 'unknown'),
            'platform': platform.system() or 'Unknown',
            'platform_version': platform.release(),
            'kernel': platform.version(),
            'boot_time': datetime.fromtimestamp(boot_time, tz=timezone.utc).isoformat(),
            'uptime': now - boot_time,
            'motherboard': hw['motherboard'],
            'bios': hw['bios']
        },
        'network_cards': hw['network_cards'],
        'processes': processes
    }


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        path = urlparse(self.path).path

        if path == '/':
            index_path = os.path.join(script_dir, 'static', 'index.html')
            try:
                with open(index_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'index.html not found')

        elif path == '/api/metrics':
            try:
                data = get_metrics()
                body = json.dumps(data).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())

        elif path == '/api/history':
            try:
                from urllib.parse import parse_qs
                qs = parse_qs(urlparse(self.path).query)
                rng = qs.get('range', ['1h'])[0]
                data = history.query_history(rng)
                body = json.dumps(data).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())

        elif path == '/api/version':
            try:
                data = version.check_updates()
                body = json.dumps(data).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

    def do_POST(self):
        path = urlparse(self.path).path

        if path == '/api/update':
            try:
                from urllib.parse import parse_qs
                qs = parse_qs(urlparse(self.path).query)
                tag = qs.get('tag', [''])[0]
                if not tag:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Missing tag'}).encode())
                    return
                script_dir = os.path.dirname(os.path.abspath(__file__))
                ok, msg = version.perform_update(tag, script_dir)
                body = json.dumps({'ok': ok, 'msg': msg}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')


def get_local_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ip not in ips and not ip.startswith('127.') and not ip.startswith('169.254'):
                ips.append(ip)
    except Exception:
        pass
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ips.append(s.getsockname()[0])
            s.close()
        except Exception:
            pass
    return ips


def serve(host='0.0.0.0', port=5000):
    history.init_store()
    history.start_sampler()
    server = ThreadedHTTPServer((host, port), RequestHandler)
    local_ips = get_local_ips()
    print(f"Server Monitor running at:")
    for ip in local_ips:
        print(f"  http://{ip}:{port}")
    if not local_ips:
        print(f"  http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        history.stop_sampler()
        server.shutdown()


def run(host='0.0.0.0', port=5000):
    import subprocess
    import glob as _glob
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(script_dir, 'app.py')
    env = os.environ.copy()
    # Avoid recursion: child should not watch
    env['SERVER_MONITOR_NO_WATCH'] = '1'

    while True:
        print(f"[hot-reload] Starting server at {host}:{port}")
        proc = subprocess.Popen([sys.executable, script, '--serve', '--host', str(host), '--port', str(port)],
                                cwd=script_dir, env=env)
        mtimes = {}
        for f in _glob.glob(os.path.join(script_dir, '*.py')):
            mtimes[f] = os.path.getmtime(f)
        try:
            while True:
                time.sleep(1)
                changed = False
                for f in _glob.glob(os.path.join(script_dir, '*.py')):
                    current = os.path.getmtime(f)
                    if f in mtimes and current != mtimes[f]:
                        changed = True
                        break
                    mtimes[f] = current
                if changed:
                    print("[hot-reload] File changed, restarting...")
                    break
        except KeyboardInterrupt:
            print("\n[hot-reload] Shutting down...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
            proc.wait()
        time.sleep(0.5)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true', help='Run server only (no watcher)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind')
    args = parser.parse_args()

    if args.serve:
        serve(args.host, args.port)
    else:
        run(args.host, args.port)
