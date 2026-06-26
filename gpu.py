import subprocess
import platform
from utils import run_cmd


def get_gpus():
    """Detect GPUs. Returns list of dicts with name, usage%, temperature, memory."""
    gpus = []
    system = platform.system()

    # Try NVIDIA first (nvidia-smi works on Windows/Linux)
    try:
        output = run_cmd(
            'nvidia-smi --query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total '
            '--format=csv,noheader,nounits'
        )
        if output:
            for line in output.splitlines():
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 5:
                    gpus.append({
                        'name': parts[0],
                        'usage': float(parts[1]) if parts[1] else 0.0,
                        'temperature': float(parts[2]) if parts[2] else 0.0,
                        'memory_used': float(parts[3]) * 1024 * 1024 if parts[3] else 0.0,
                        'memory_total': float(parts[4]) * 1024 * 1024 if parts[4] else 0.0,
                        'vendor': 'NVIDIA'
                    })
            if gpus:
                return gpus
    except Exception:
        pass

    # Fallback: list video controllers without usage/temp
    try:
        if system == 'Windows':
            result = subprocess.run(
                ['wmic', 'path', 'win32_VideoController', 'get', 'Name', '/format:csv'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                if len(lines) >= 2:
                    for line in lines[1:]:
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 2 and parts[1]:
                            gpus.append({
                                'name': parts[1],
                                'usage': 0.0,
                                'temperature': 0.0,
                                'memory_used': 0.0,
                                'memory_total': 0.0,
                                'vendor': 'Unknown'
                            })
        elif system == 'Linux':
            output = run_cmd("lspci | grep -i 'vga\\|3d\\|display'")
            if output:
                for line in output.splitlines():
                    name = line.split(':')[-1].strip()
                    if name:
                        gpus.append({
                            'name': name,
                            'usage': 0.0,
                            'temperature': 0.0,
                            'memory_used': 0.0,
                            'memory_total': 0.0,
                            'vendor': 'Unknown'
                        })
    except Exception:
        pass

    return gpus
