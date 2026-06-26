import subprocess


def run_cmd(cmd, timeout=10):
    """Run a shell command and return stdout string."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            return ''
        return result.stdout.strip()
    except Exception:
        return ''


def run_cmd_json(cmd, timeout=10):
    """Run a shell command expecting JSON output."""
    import json as _json
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            return None
        return _json.loads(result.stdout)
    except Exception:
        return None
