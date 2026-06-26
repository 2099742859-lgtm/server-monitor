import platform
import subprocess
import os
from utils import run_cmd, run_cmd_json


def run_wmic_csv(query):
    """Run a wmic query and parse CSV output. Returns list of dicts."""
    try:
        result = subprocess.run(
            ['wmic'] + query.split() + ['/format:csv'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []
        lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        if len(lines) < 2:
            return []
        headers = [h.strip() for h in lines[0].split(',')]
        items = []
        for line in lines[1:]:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= len(headers):
                items.append(dict(zip(headers, parts)))
        return items
    except Exception:
        return []


def get_cpu_model():
    system = platform.system()
    try:
        if system == 'Windows':
            data = run_wmic_csv('cpu get Name')
            if data and 'Name' in data[0]:
                return data[0]['Name']
        elif system == 'Linux':
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            return line.split(':', 1)[1].strip()
            except Exception:
                pass
        elif system == 'Darwin':
            model = run_cmd('sysctl -n machdep.cpu.brand_string')
            if model:
                return model
    except Exception:
        pass
    return platform.processor() or 'Unknown'


def get_motherboard():
    system = platform.system()
    try:
        if system == 'Windows':
            data = run_wmic_csv('baseboard get Manufacturer,Product')
            if data:
                manufacturer = data[0].get('Manufacturer', '').strip()
                product = data[0].get('Product', '').strip()
                result = f"{manufacturer} {product}".strip()
                if result:
                    return result
        elif system == 'Linux':
            vendor = ''
            name = ''
            try:
                if os.path.exists('/sys/class/dmi/id/board_vendor'):
                    with open('/sys/class/dmi/id/board_vendor', 'r') as f:
                        vendor = f.read().strip()
                if os.path.exists('/sys/class/dmi/id/board_name'):
                    with open('/sys/class/dmi/id/board_name', 'r') as f:
                        name = f.read().strip()
            except Exception:
                pass
            result = f"{vendor} {name}".strip()
            if result:
                return result
        elif system == 'Darwin':
            model = run_cmd('sysctl -n hw.model')
            if model:
                return model
    except Exception:
        pass
    return 'Unknown'


def get_bios():
    system = platform.system()
    try:
        if system == 'Windows':
            data = run_wmic_csv('bios get Manufacturer,Name,Version')
            if data:
                manufacturer = data[0].get('Manufacturer', '').strip()
                name = data[0].get('Name', '').strip()
                version = data[0].get('Version', '').strip()
                result = f"{manufacturer} {name} {version}".strip()
                if result:
                    return result
        elif system == 'Linux':
            vendor = ''
            version = ''
            try:
                if os.path.exists('/sys/class/dmi/id/bios_vendor'):
                    with open('/sys/class/dmi/id/bios_vendor', 'r') as f:
                        vendor = f.read().strip()
                if os.path.exists('/sys/class/dmi/id/bios_version'):
                    with open('/sys/class/dmi/id/bios_version', 'r') as f:
                        version = f.read().strip()
            except Exception:
                pass
            result = f"{vendor} {version}".strip()
            if result:
                return result
        elif system == 'Darwin':
            bios = run_cmd("system_profiler SPHardwareDataType | grep 'Boot ROM Version'")
            if bios:
                return bios.split(':', 1)[-1].strip()
    except Exception:
        pass
    return 'Unknown'


def get_memory_modules():
    system = platform.system()
    modules = []
    try:
        if system == 'Windows':
            data = run_wmic_csv('memorychip get Capacity,Speed,Manufacturer,PartNumber')
            for item in data:
                try:
                    capacity = int(item.get('Capacity', 0))
                    speed = item.get('Speed', '0').strip()
                    manufacturer = item.get('Manufacturer', 'Unknown').strip()
                    part_number = item.get('PartNumber', 'Unknown').strip()
                    modules.append({
                        'size': capacity,
                        'size_text': format_bytes(capacity),
                        'speed': f"{speed} MHz" if speed and speed.isdigit() else speed,
                        'manufacturer': manufacturer,
                        'part_number': part_number
                    })
                except Exception:
                    continue
        elif system == 'Linux':
            output = run_cmd('dmidecode -t memory')
            if output:
                from collections import defaultdict
                stick = defaultdict(str)
                in_device = False
                for line in output.splitlines():
                    line = line.strip()
                    if line.startswith('Memory Device'):
                        if in_device and stick.get('Size'):
                            modules.append({
                                'size': parse_size(stick.get('Size', '0')),
                                'size_text': stick.get('Size', 'Unknown'),
                                'speed': stick.get('Speed', 'Unknown'),
                                'manufacturer': stick.get('Manufacturer', 'Unknown'),
                                'part_number': stick.get('Part Number', 'Unknown')
                            })
                        stick = defaultdict(str)
                        in_device = True
                    if ':' in line:
                        k, v = line.split(':', 1)
                        stick[k.strip()] = v.strip()
                if in_device and stick.get('Size'):
                    modules.append({
                        'size': parse_size(stick.get('Size', '0')),
                        'size_text': stick.get('Size', 'Unknown'),
                        'speed': stick.get('Speed', 'Unknown'),
                        'manufacturer': stick.get('Manufacturer', 'Unknown'),
                        'part_number': stick.get('Part Number', 'Unknown')
                    })
        elif system == 'Darwin':
            output = run_cmd('system_profiler SPMemoryDataType')
            if output:
                current = {}
                for line in output.splitlines():
                    line = line.strip()
                    if line.startswith('Size:') and 'GB' in line:
                        current['size_text'] = line.split(':', 1)[1].strip()
                        current['size'] = parse_size(current['size_text'])
                    elif line.startswith('Speed:') and current:
                        current['speed'] = line.split(':', 1)[1].strip()
                    elif line.startswith('Manufacturer:') and current:
                        current['manufacturer'] = line.split(':', 1)[1].strip()
                    elif line.startswith('Part Number:') and current:
                        current['part_number'] = line.split(':', 1)[1].strip()
                    elif line == '' and current:
                        if 'size' in current:
                            modules.append(current)
                        current = {}
    except Exception:
        pass
    return modules


def get_disk_drives():
    system = platform.system()
    drives = []
    try:
        if system == 'Windows':
            data = run_wmic_csv('diskdrive get Model,Size,InterfaceType')
            for item in data:
                try:
                    size = int(item.get('Size', 0))
                    drives.append({
                        'model': item.get('Model', 'Unknown').strip(),
                        'size': size,
                        'size_text': format_bytes(size),
                        'interface': item.get('InterfaceType', 'Unknown').strip()
                    })
                except Exception:
                    continue
        elif system == 'Linux':
            output = run_cmd('lsblk -J -o NAME,MODEL,SIZE,TRAN,TYPE')
            if output:
                import json as _json
                try:
                    data = _json.loads(output)
                    for dev in data.get('blockdevices', []):
                        if dev.get('type') == 'disk':
                            size_str = dev.get('size', '0')
                            drives.append({
                                'model': dev.get('model', 'Unknown').strip(),
                                'size': parse_size(size_str),
                                'size_text': size_str,
                                'interface': dev.get('tran', 'Unknown').upper()
                            })
                except Exception:
                    pass
        elif system == 'Darwin':
            output = run_cmd('system_profiler SPStorageDataType')
            if output:
                current = {}
                for line in output.splitlines():
                    line = line.strip()
                    if line.startswith('Device Identifier:'):
                        current = {'model': line.split(':', 1)[1].strip(), 'interface': 'Unknown'}
                    elif line.startswith('Capacity:') and current:
                        current['size_text'] = line.split(':', 1)[1].strip()
                        current['size'] = parse_size(current['size_text'])
                        drives.append(current)
                        current = {}
    except Exception:
        pass
    return drives


def get_network_cards():
    """Return list of physical network interfaces with MAC, IPs, speed."""
    cards = []
    try:
        import psutil as _psutil
        addrs = _psutil.net_if_addrs()
        stats = _psutil.net_if_stats()
        for name, addr_list in addrs.items():
            # Skip loopback and virtual interfaces
            if 'loopback' in name.lower() or name.lower() == 'lo':
                continue
            # Skip common virtual/tunnel adapters
            skip_prefixes = ('veth', 'docker', 'br-', 'tun', 'tap', 'wg', 'ppp')
            if any(name.startswith(prefix) for prefix in skip_prefixes):
                continue

            mac = ''
            ips = []
            for addr in addr_list:
                if addr.family == _psutil.AF_LINK:
                    mac = addr.address
                elif addr.family.name == 'AF_INET':
                    ips.append(addr.address)
                elif addr.family.name == 'AF_INET6':
                    ips.append(addr.address)

            if not mac and not ips:
                continue

            stat = stats.get(name)
            cards.append({
                'name': name,
                'mac': mac,
                'ips': ips,
                'speed': stat.speed if stat else None,  # Mbps
                'is_up': stat.isup if stat else None
            })
    except Exception:
        pass
    return cards


def format_bytes(bytes_value):
    if bytes_value == 0:
        return '0 B'
    k = 1024
    sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    import math
    i = int(math.floor(math.log(bytes_value) / math.log(k))) if bytes_value > 0 else 0
    return f"{bytes_value / (k ** i):.2f} {sizes[i]}"


def parse_size(size_str):
    """Parse strings like '500 GB', '1.5TB', '16GiB' into bytes."""
    if not size_str:
        return 0
    size_str = size_str.strip().replace(',', '').replace('i', '').upper()
    import re
    match = re.match(r'([\d.]+)\s*([A-Z]*)', size_str)
    if not match:
        return 0
    val = float(match.group(1))
    unit = match.group(2)
    units = {'B': 0, 'KB': 1, 'MB': 2, 'GB': 3, 'TB': 4, 'PB': 5, 'K': 1, 'M': 2, 'G': 3, 'T': 4, 'P': 5}
    exp = units.get(unit, 0)
    return int(val * (1024 ** exp))
