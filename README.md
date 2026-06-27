# Server Monitor 服务器监控面板

[中文](#中文文档) | [English](#english-documentation)

---

## 中文文档

跨平台服务器监控面板，液态玻璃高透 UI，实时硬件状态监控，自动壁纸，热重载，版本管理，单文件一键部署。

### 介绍

Server Monitor 是一个轻量级的服务器监控面板，无需 Docker、无需 Node.js，只需 Python 即可运行。后端基于 Python 内置 `http.server` + `psutil`，前端纯 HTML + Tailwind CSS + Chart.js，单文件部署，开箱即用。

支持 Windows / Linux / macOS 三平台，自动检测硬件信息，实时展示 CPU、内存、磁盘、网络、GPU 等指标，适合家庭服务器、NAS、VPS 等场景的日常监控。

### 功能

- 实时 CPU 使用率、物理核心 / 逻辑线程数、频率
- 实时内存使用率、已用 / 总量 / 可用、Swap
- 磁盘总使用率、分区详情、磁盘 I/O 读写速率
- 网络上下行速率、总流量
- GPU 使用率 / 温度 / 显存（NVIDIA）
- 硬件信息：CPU 型号、主板、BIOS、内存条、硬盘、网卡
- Top 进程（按 CPU 排序）
- CPU / 内存 / 网络 / 磁盘 I/O 历史趋势图（时间桶平均，JSON 持久化）
- 版本管理：面板内检测 GitHub 新版本，一键更新 / 切换版本
- 自动壁纸（桌面 / 手机自适应）
- 热重载：修改 `.py` 文件自动重启
- 液态玻璃高透 UI，中英文一键切换
- 跨平台：Windows / Linux / macOS

### 一键部署

项目提供两个单文件自解压安装包，内嵌完整源码 + tar 归档，无需 clone 仓库，下载单个文件即可部署：

#### Windows — `server-monitor.bat`

下载：https://github.com/2099742859-lgtm/server-monitor/releases/download/v1.1.2/server-monitor.bat

```cmd
:: 下载后双击运行
server-monitor.bat
```

#### Linux / macOS — `server-monitor.sh`

下载：https://github.com/2099742859-lgtm/server-monitor/releases/download/v1.1.2/server-monitor.sh

```bash
curl -fsSL -o server-monitor.sh https://github.com/2099742859-lgtm/server-monitor/releases/download/v1.1.2/server-monitor.sh
bash server-monitor.sh
```

> **注意**：不能直接 `curl | bash`，因为自解压脚本需要读取自身文件。请先下载再运行。

自动完成：安装 uv → 安装 Python → 解压 → 创建 venv → 安装依赖 → 启动。

启动后会自动检测并输出本机局域网 IP，直接访问即可。

### 从源码运行

```bash
git clone https://github.com/2099742859-lgtm/server-monitor.git
cd server-monitor
pip install psutil
python app.py
```

打开 `http://localhost:5000`

### 局域网访问

默认监听 `0.0.0.0:5000`，局域网设备通过 `http://本机IP:5000` 访问。

```powershell
# Windows 防火墙
netsh advfirewall firewall add rule name="Server Monitor 5000" dir=in action=allow protocol=TCP localport=5000
```

```bash
# Linux 防火墙
sudo ufw allow 5000/tcp              # Ubuntu / Debian
sudo firewall-cmd --permanent --add-port=5000/tcp && sudo firewall-cmd --reload  # CentOS / RHEL
```

### 版本管理

面板底部「版本管理」区域会自动检测 GitHub Releases，显示当前版本和最新版本。点击「更新」按钮即可下载并切换到指定版本，服务自动热重载重启。

### 文件说明

| 文件 | 说明 |
|------|------|
| `app.py` | 后端主程序（ThreadedHTTPServer + psutil + 热重载 + IO 速率 + IP 检测） |
| `hardware.py` | 跨平台硬件检测（CPU、主板、BIOS、内存条、硬盘、网卡） |
| `gpu.py` | 显卡检测（nvidia-smi + wmic/lspci 备用方案） |
| `utils.py` | 共享工具函数（run_cmd 等） |
| `history.py` | 历史数据采集与持久化（JSON 存储，时间桶平均） |
| `version.py` | 版本管理（GitHub Releases 检测 + 在线更新） |
| `static/index.html` | 前端页面（液态玻璃 UI + 中英文切换） |
| `requirements.txt` | Python 依赖（psutil） |
| `server-monitor.bat` | Windows 单文件自解压安装包（uv 自动安装） |
| `server-monitor.sh` | Linux/macOS 单文件自解压安装包（uv 自动安装） |

### API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/metrics` | 实时硬件指标（CPU、内存、磁盘、网络、GPU、进程） |
| `GET /api/history?range=1h\|6h\|24h\|7d` | 历史趋势数据（时间桶平均聚合） |
| `GET /api/version` | 当前版本 + GitHub 可用版本列表 |
| `POST /api/update?tag=vX` | 触发在线更新到指定版本 |

### 注意事项

- NVIDIA 显卡需安装驱动才能检测 GPU
- 无显卡设备自动隐藏 GPU 板块
- Linux 部分硬件信息（dmidecode）可能需要 root 权限
- `boot_time` 为 ISO 8601 格式（UTC 时区）
- `history.json` 自动生成，重启后保留历史数据

### License

MIT

---

## English Documentation

Cross-platform server monitoring dashboard with liquid glass UI, real-time hardware metrics, auto wallpaper, hot reload, version management, and single-file deployment.

### Introduction

Server Monitor is a lightweight server monitoring dashboard. No Docker, no Node.js — just Python. Backend uses Python's built-in `http.server` + `psutil`; frontend is plain HTML + Tailwind CSS + Chart.js. Single-file deployment, works out of the box.

Supports Windows / Linux / macOS with automatic hardware detection and real-time CPU, memory, disk, network, and GPU metrics. Ideal for home servers, NAS, VPS, and daily monitoring.

### Features

- Real-time CPU usage, physical/logical core count, frequency
- Real-time memory usage, used / total / available, Swap
- Disk usage, partition details, disk I/O read/write rates
- Network upload/download rates, total traffic
- GPU usage / temperature / VRAM (NVIDIA)
- Hardware info: CPU model, motherboard, BIOS, RAM modules, drives, network cards
- Top processes (sorted by CPU)
- CPU / Memory / Network / Disk I/O history charts (time-bucket averaging, JSON persistence)
- Version manager: detect GitHub releases from the dashboard, update/switch versions in-place
- Auto wallpaper (desktop/mobile adaptive)
- Hot reload: auto-restart on `.py` file changes
- Liquid glass UI with ZH/EN toggle
- Cross-platform: Windows / Linux / macOS

### Quick Deploy

Two self-extracting installers are available, each embedding the full source as a tar archive. No need to clone — just download and run:

#### Windows — `server-monitor.bat`

Download: https://github.com/2099742859-lgtm/server-monitor/releases/download/v1.1.2/server-monitor.bat

```cmd
:: Download and double-click
server-monitor.bat
```

#### Linux / macOS — `server-monitor.sh`

Download: https://github.com/2099742859-lgtm/server-monitor/releases/download/v1.1.2/server-monitor.sh

```bash
curl -fsSL -o server-monitor.sh https://github.com/2099742859-lgtm/server-monitor/releases/download/v1.1.2/server-monitor.sh
bash server-monitor.sh
```

> **Note**: Do not pipe `curl | bash` — the self-extracting script needs to read itself as a file. Download first, then run.

This automatically: installs uv → installs Python → extracts → creates venv → installs deps → starts server.

On startup, it detects and prints all local network IPs for easy access.

### Run from Source

```bash
git clone https://github.com/2099742859-lgtm/server-monitor.git
cd server-monitor
pip install psutil
python app.py
```

Open `http://localhost:5000`

### LAN Access

Listens on `0.0.0.0:5000` by default. Access from other devices at `http://YOUR_IP:5000`.

```powershell
# Windows Firewall
netsh advfirewall firewall add rule name="Server Monitor 5000" dir=in action=allow protocol=TCP localport=5000
```

```bash
# Linux Firewall
sudo ufw allow 5000/tcp              # Ubuntu / Debian
sudo firewall-cmd --permanent --add-port=5000/tcp && sudo firewall-cmd --reload  # CentOS / RHEL
```

### Version Manager

The "Version Manager" panel at the bottom automatically checks GitHub Releases, showing the current and latest versions. Click "Update" to download and switch to any version — the server hot-reloads automatically.

### File Overview

| File | Description |
|------|-------------|
| `app.py` | Backend main (ThreadedHTTPServer + psutil + hot reload + IO rates + IP detection) |
| `hardware.py` | Cross-platform hardware detection (CPU, motherboard, BIOS, RAM, drives, NICs) |
| `gpu.py` | GPU detection (nvidia-smi + wmic/lspci fallback) |
| `utils.py` | Shared utilities (run_cmd, etc.) |
| `history.py` | History sampling & persistence (JSON storage, time-bucket averaging) |
| `version.py` | Version management (GitHub Releases detection + in-place update) |
| `static/index.html` | Frontend (liquid glass UI + ZH/EN toggle) |
| `requirements.txt` | Python dependency (psutil) |
| `server-monitor.bat` | Windows self-extracting installer (uv auto-install) |
| `server-monitor.sh` | Linux/macOS self-extracting installer (uv auto-install) |

### API

| Endpoint | Description |
|----------|-------------|
| `GET /api/metrics` | Real-time hardware metrics (CPU, memory, disk, network, GPU, processes) |
| `GET /api/history?range=1h\|6h\|24h\|7d` | Historical trend data (time-bucket averaged) |
| `GET /api/version` | Current version + available GitHub releases |
| `POST /api/update?tag=vX` | Trigger in-place update to specified version |

### Notes

- NVIDIA drivers required for GPU detection
- GPU panel auto-hides if no GPU found
- Some Linux hardware info (dmidecode) may require root
- `boot_time` is ISO 8601 format (UTC)
- `history.json` is auto-generated; history persists across restarts

### License

MIT
