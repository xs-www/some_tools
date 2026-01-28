Flask 后端框架骨架

说明
- 应用工厂：`create_app` 位于 `app.py`
- 配置：`config.py`
- 扩展：`extensions.py`（数据库、迁移、CORS）
- 控制器：`controller.py` 中提供 `api_bp` 和 UI 蓝图（`ui_bp`）

本项目包含一个小工具：上传 Word 文档并转换为 PDF（路由：`/convert`）。转换优先使用本机 Microsoft Word（Windows + `docx2pdf`），若不可用回退到 LibreOffice (`soffice`)。

快速开始

1) 在项目根创建并激活虚拟环境，然后安装依赖：

Windows (PowerShell)：

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Linux / macOS：

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

2) 启动应用：

- Windows（推荐使用本仓库提供的脚本）：

   - CMD: `run.bat`（会激活 venv 并使用 `SOFFICE_PATH` 环境变量）
   - PowerShell: `run.ps1`（如需同样逻辑可用脚本）

- 直接调用 venv 的 Python：

```powershell
.\venv\Scripts\python.exe app.py
```

或（Linux/macOS）
```bash
./venv/bin/python app.py
```

安装 LibreOffice（当没有 Microsoft Word 时必须）

推荐在服务器上使用 LibreOffice headless（稳定且支持 Linux）。安装示例：

Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y libreoffice libreoffice-headless fonts-noto-cjk
```

CentOS/Fedora:
```bash
sudo dnf install -y libreoffice libreoffice-headless
```

macOS (Homebrew):
```bash
brew install --cask libreoffice
```

Windows:
- 从 https://www.libreoffice.org/download/download/ 下载并安装（默认可执行：`C:\Program Files\LibreOffice\program\soffice.exe`）。

环境变量

- 临时（当前 PowerShell 会话）：
```powershell
#$env:SOFFICE_PATH = 'C:\Program Files\LibreOffice\program\soffice.exe'
$env:PATH += ';C:\Program Files\LibreOffice\program'
```

- 永久（Windows，命令行）：
```powershell
setx SOFFICE_PATH "C:\Program Files\LibreOffice\program\soffice.exe"
setx PATH "%PATH%;C:\Program Files\LibreOffice\program"
```

- Linux（bash，永久）：在 `~/.bashrc` 或 `/etc/profile.d/` 添加：
```bash
export SOFFICE_PATH=/usr/bin/soffice
export PATH="$PATH:$(dirname /usr/bin/soffice)"
```

验证 `soffice` 是否可用：
```bash
which soffice   # Linux / macOS
where.exe soffice  # Windows
```

一键服务器设置脚本

仓库已包含 `scripts/setup_server.sh`，用于在 Linux/macOS 上：安装 LibreOffice、字体、创建 Python venv 并安装依赖，及可选创建 systemd 单元。

示例（Ubuntu，root）：
```bash
sudo bash scripts/setup_server.sh --service enable
```

或仅创建 venv（非 root）：
```bash
bash scripts/setup_server.sh --user
```

关于多次转换失败（Word COM / WINWORD 进程残留）

- 问题原因：`docx2pdf` 在 Windows 上依赖 Microsoft Word COM；若 WINWORD 进程残留、并发调用或在非交互会话运行，会导致第二次调用失败。
- 本项目策略：
   - 优先使用 `docx2pdf`（Word）；若失败回退到 `soffice`（LibreOffice）。
   - 已把 `docx2pdf` 调用隔离到子進程，添加重试，并提供可选环境变量 `DOCX2PDF_CLEANUP_WINWORD=1`（开启后会在转换后尝试强制结束 WINWORD 进程，风险：会关闭所有 Word 窗口）。
   - 生产环境建议使用 LibreOffice headless 或将转换放入独立 worker（串行化）。

调试与排查

- 查看后端控制台日志：直接用 venv 的 Python 运行 `app.py`，控制台会打印转换的 traceback 与 soffice 路径：
```powershell
.\venv\Scripts\python.exe app.py
```

- 检查 `soffice`：
```bash
which soffice
soffice --version
```

- 在 Windows 上测试 docx2pdf：准备 `small.docx`，运行测试脚本 `test_debug.py`（打印输入路径存在性与转换 traceback）。

路由
- 上传/转换页面（UI）: `GET /convert` 显示上传表单，支持页面范围与预览；`POST /convert` 支持 `pages` 与 `action=preview|download`。

如需我把启动脚本（`run.ps1` / `run.bat`）进一步调整，或生成 `Dockerfile` / `systemd` 示例以便部署，请告诉我你的目标平台（Linux 发行版或 Docker）。

