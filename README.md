# Server Monitor 服务器监控面板

跨平台服务器监控面板，液态玻璃高透 UI，实时硬件状态监控，自动壁纸，热重载，单文件一键部署。

## 介绍

Server Monitor 是一个轻量级的服务器监控面板，无需 Docker、无需 Node.js，只需 Python 即可运行。后端基于 Python 内置 `http.server` + `psutil`，前端纯 HTML + Tailwind CSS + Chart.js，单文件部署，开箱即用。

支持 Windows / Linux / macOS 三平台，自动检测硬件信息，实时展示 CPU、内存、磁盘、网络、GPU 等指标，适合家庭服务器、NAS、VPS 等场景的日常监控。

## 技术栈

### 后端

| 技术 | 说明 |
|------|------|
| Python 3.7+ | 运行环境 |
| psutil | 系统指标采集（CPU、内存、磁盘、网络、进程） |
| http.server | 内置 HTTP 服务器，无需 Flask/Django |
| ThreadedMixIn | 多线程处理，支持并发请求 |
| wmic / dmidecode / sysctl | 跨平台硬件信息检测 |
| nvidia-smi | NVIDIA GPU 状态检测 |
| uv | Python 包管理器，自动安装 Python + 依赖 |

### 前端

| 技术 | 说明 |
|------|------|
| HTML5 | 单文件页面，无构建步骤 |
| Tailwind CSS | 原子化 CSS，CDN 加载 |
| Chart.js | CPU / 内存 / 网络 / 磁盘趋势图 |
| CSS backdrop-filter | 液态玻璃高透效果 |
| JavaScript | 原生 JS，无框架依赖 |

### 部署

| 技术 | 说明 |
|------|------|
| Shell 自解压脚本 | base64 + tar 内嵌归档，单文件分发 |
| uv | 自动安装 Python + 虚拟环境 + 依赖 |

## 功能

- 实时 CPU 使用率、物理核心 / 逻辑线程数、频率
- 实时内存使用率、已用 / 总量 / 可用、Swap
- 磁盘总使用率、分区详情、磁盘 I/O 读写速率
- 网络上下行速率、总流量
- GPU 使用率 / 温度 / 显存（NVIDIA）
- 硬件信息：CPU 型号、主板、BIOS、内存条、硬盘、网卡
- Top 进程（按 CPU 排序）
- CPU / 内存 / 网络 / 磁盘 I/O 历史趋势图
- 自动壁纸（桌面 / 手机自适应）
- 热重载：修改 `.py` 文件自动重启
- 液态玻璃高透 UI，中英文一键切换
- 跨平台：Windows / Linux / macOS

## 一键部署

项目提供两个单文件自解压安装包，内嵌完整源码 + tar 归档，无需 clone 仓库，下载单个文件即可部署：

### Windows — `server-monitor.bat`

下载：https://raw.githubusercontent.com/2099742859-lgtm/server-monitor/main/server-monitor.bat

```cmd
:: 下载后直接双击运行，或在命令行执行：
server-monitor.bat

:: 或用 PowerShell 一行下载并运行：
irm https://raw.githubusercontent.com/2099742859-lgtm/server-monitor/main/server-monitor.bat | Out-File -Encoding ASCII server-monitor.bat; ./server-monitor.bat
```

自动完成：
1. 检测并安装 [uv](https://github.com/astral-sh/uv)
2. `uv python install 3.11` — 安装 Python
3. 解压内嵌 tar 归档
4. `uv venv` — 创建虚拟环境
5. `uv pip install psutil` — 安装依赖
6. 启动服务器

### Linux / macOS — `server-monitor.sh`

下载：https://github.com/2099742859-lgtm/server-monitor/releases/download/v2/server-monitor.sh

```bash
curl -fsSL -o server-monitor.sh https://github.com/2099742859-lgtm/server-monitor/releases/download/v2/server-monitor.sh
bash server-monitor.sh
```

自动完成同样的流程：安装 uv → 安装 Python → 解压 → 创建 venv → 安装依赖 → 启动。

### 从源码运行

```bash
git clone https://github.com/2099742859-lgtm/server-monitor.git
cd server-monitor
pip install psutil
python app.py
```

打开 `http://localhost:5000`

## 局域网访问

默认监听 `0.0.0.0:5000`，局域网设备通过 `http://本机IP:5000` 访问。

### Windows 防火墙

```powershell
netsh advfirewall firewall add rule name="Server Monitor 5000" dir=in action=allow protocol=TCP localport=5000
```

### Linux 防火墙

```bash
# Ubuntu / Debian
sudo ufw allow 5000/tcp

# CentOS / RHEL
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

## 热重载

服务启动后自动监控 `.py` 文件变化，保存后 2 秒内自动重启（通过 subprocess 拉起新进程），无需手动操作。修改前端 `index.html` 只需刷新浏览器。

## 使用 uv（推荐）

[uv](https://github.com/astral-sh/uv) 是高速 Python 包管理器，可自动安装 Python，不依赖系统 Python：

```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh            # Linux/macOS
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# 安装 Python + 依赖
uv python install 3.11
uv venv
uv pip install -r requirements.txt

# 启动
.venv/bin/python app.py          # Linux/macOS
.venv\Scripts\python.exe app.py   # Windows
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `app.py` | 后端主程序（ThreadedHTTPServer + psutil + 热重载 + IO 速率计算） |
| `hardware.py` | 跨平台硬件检测（CPU、主板、BIOS、内存条、硬盘、网卡） |
| `gpu.py` | 显卡检测（nvidia-smi + wmic/lspci 备用方案） |
| `utils.py` | 共享工具函数（run_cmd 等） |
| `static/index.html` | 前端页面（液态玻璃 UI + 中英文切换） |
| `requirements.txt` | Python 依赖（psutil） |
| `server-monitor.bat` | Windows 单文件自解压安装包（uv 自动安装） |
| `server-monitor.sh` | Linux/macOS 单文件自解压安装包（uv 自动安装） |

## API 接口

`GET /api/metrics` 返回 JSON：

```json
{
  "cpu": { "percent", "per_core", "physical_cores", "logical_cores", "model" },
  "memory": { "total", "used", "available", "percent", "modules" },
  "disk": { "total", "used", "percent", "partitions", "io": { "read_rate", "write_rate" } },
  "network": { "bytes_sent", "bytes_recv", "sent_rate", "recv_rate" },
  "gpu": { "gpus", "count" },
  "system": { "hostname", "platform", "boot_time", "uptime", "motherboard", "bios" },
  "processes": [...]
}
```

## 自定义

- **端口**：编辑 `app.py` 中的 `PORT = 5000`
- **壁纸**：编辑 `static/index.html` 中的 `loadWallpaper()` 函数
- **UI 透明度**：编辑 `static/index.html` 中的 `.glass` CSS 属性

## 注意事项

- NVIDIA 显卡需安装驱动才能检测 GPU
- 无显卡设备自动隐藏 GPU 板块
- Windows 下 `py` 启动器或 uv 管理的 Python 优先
- Linux 部分硬件信息（dmidecode）可能需要 root 权限
- `boot_time` 为 ISO 8601 格式（UTC 时区）

## License

MIT
