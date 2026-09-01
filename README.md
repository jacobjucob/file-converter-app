# 文件格式转换器

一款跨平台桌面文件格式转换工具，支持多种文档和图片格式的相互转换。所有转换操作均在本地完成，不上传任何用户数据。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey.svg)

---

## 📋 功能特点

- **多格式支持**：支持 PDF、Word、Excel、PPT、图片等十余种格式互转
- **多页文档转图片**：支持将多页 PDF/Word 转换为多张图片并打包为 ZIP
- **压缩质量控制**：JPEG/PNG 输出支持质量调节
- **批量预览**：转换后自动显示前 5 页预览
- **本地转换**：所有操作在本地完成，不上传任何数据
- **跨平台支持**：Windows 10+ 和 macOS 10.15+
- **直观界面**：采用毛玻璃设计风格，操作简单

---

## 📦 支持的格式

### 输入格式
`pdf`, `docx`, `doc`, `xlsx`, `xls`, `pptx`, `ppt`, `txt`, `rtf`, `html`, `htm`, `md`, `csv`, `wps`

### 输出格式
`pdf`, `docx`, `doc`, `xlsx`, `xls`, `pptx`, `ppt`, `txt`, `png`, `jpg`, `jpeg`, `bmp`

### 转换方向限制

| 输入格式 | 支持的输出格式 |
|---------|---------------|
| PDF | PDF, DOCX, PNG, JPG, JPEG, BMP |
| DOCX/DOC | DOCX, DOC, PDF, TXT, RTF, HTML, PNG, JPG, JPEG, BMP |
| XLSX/XLS | XLSX, XLS, PDF, CSV, HTML, PNG, JPG, JPEG, BMP |
| PPTX/PPT | PPTX, PPT, PDF, PNG, JPG, JPEG, BMP |
| TXT | TXT, PDF, HTML, DOCX, DOC |
| RTF | RTF, DOCX, DOC, PDF, HTML, TXT |
| HTML/HTM | HTML, HTM, PDF, DOCX, DOC, TXT |
| CSV | CSV, XLSX, XLS, PDF, HTML |
| WPS | WPS, DOCX, DOC, PDF, TXT |

---

## 🖥️ 系统要求

| 操作系统 | 版本要求 |
|---------|---------|
| Windows | Windows 10 及以上（64位） |
| macOS | macOS 10.15 (Catalina) 及以上 |
| Python | 3.8 及以上 |

---

## 🔧 安装指南

### 1. 克隆项目

```bash
git clone <repository-url>
cd file-converter-app
2. 创建虚拟环境（推荐）
bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
3. 安装 Python 依赖
bash
pip install -r requirements.txt
4. 安装 LibreOffice
Windows:

访问 LibreOffice 官网

下载并安装 LibreOffice（最新版本）

记住安装路径（默认：C:\Program Files\LibreOffice\program\soffice.exe）

macOS:

bash
brew install libreoffice
或从官网下载安装包。

5. 安装 Poppler（用于预览功能）
Windows:

访问 poppler-windows releases

下载最新 Release-*.zip

解压到项目根目录下的 poppler/ 文件夹

确保 poppler/bin/ 目录存在

macOS:

bash
brew install poppler
🚀 运行应用
开发模式
bash
python run.py
使用虚拟环境
bash
# Windows
.venv\Scripts\python run.py
# macOS/Linux
source .venv/bin/activate && python run.py
📦 打包为可执行文件
Windows
bash
pyinstaller --name=FileConverter --windowed --onefile --add-data "src;src" --hidden-import fitz --hidden-import pdf2docx src/main.py
macOS
bash
pyinstaller --name=FileConverter --windowed --onefile --add-data "src:src" --hidden-import fitz --hidden-import pdf2docx src/main.py
打包后的可执行文件位于 dist/ 目录。

📁 项目结构
text
file-converter-app/
├── src/
│   ├── main.py                 # 程序入口
│   ├── gui/
│   │   └── main_window.py      # 主窗口（UI 逻辑）
│   ├── core/
│   │   ├── converter.py        # 转换引擎（LibreOffice 封装）
│   │   └── file_utils.py       # 文件工具类
│   ├── config/
│   │   └── settings.py         # 配置管理
│   └── utils/
│       └── logger.py           # 日志模块
├── config/                     # 配置文件目录
├── logs/                       # 日志文件目录
├── poppler/                    # Poppler 工具（Windows）
├── test_resource/              # 测试资源
├── requirements.txt            # Python 依赖
├── run.py                      # 启动脚本
└── README.md                   # 项目说明
🎯 使用说明
基本操作
选择输入文件：点击「浏览」选择待转换文件

选择输出目录：点击「选择」指定输出位置

选择输出格式：从下拉框选择目标格式

设置压缩质量（仅图片格式）：选择 20%~100%

开始转换：点击「开始转换」按钮

查看日志：右侧面板显示转换状态和文件路径

转换流程示例
text
1. 选择文件: 炉石科技-企业介绍.pdf
2. 输出目录: D:/output/
3. 输出格式: jpeg
4. 压缩质量: 80%
5. 点击「开始转换」
6. 等待转换完成 → 日志显示 ✅ 转换成功！
7. 文件路径: D:/output/炉石科技-企业介绍.zip
⚙️ 配置文件
配置文件位于 config/settings.json：

json
{
  "input_dir": "",
  "output_dir": "",
  "last_input_format": "pdf",
  "last_output_format": "pdf",
  "compression_quality": "100%"
}
📝 日志
日志文件位于 logs/ 目录，按日期命名：

text
logs/
├── app_20260101.log
├── app_20260102.log
└── ...
❓ 常见问题
Q: 转换失败，提示"未找到LibreOffice"
A: 确保 LibreOffice 已安装且 soffice.exe 在系统 PATH 中，或在代码中指定完整路径。

Q: 预览功能不可用
A: 确保 Poppler 已正确安装并配置到 poppler/bin/ 目录。

Q: 转换超时
A: 大文件转换可能需要更长时间，默认超时 180 秒。可在 converter.py 中调整 timeout 参数。

Q: 导出的 ZIP 包中图片顺序错乱
A: 图片按页码命名（1.jpg, 2.jpg, ...），排序后顺序正确。

Q: PDF 转 DOCX 时进度长时间不动
A: pdf2docx 库解析大文件时进度回调间隔较长，属于正常现象，请耐心等待。

🛠️ 技术架构
组件	技术选型
GUI 框架	PyQt6
转换引擎	LibreOffice (headless)
PDF 渲染	PyMuPDF (fitz)
图片处理	Pillow
PDF→DOCX	pdf2docx
打包工具	PyInstaller
日志模块	Python logging
📄 许可证
MIT License

🤝 贡献
欢迎提交 Issue 和 Pull Request。

📧 联系方式
如有问题，请提交 Issue 或联系项目维护者。

版本: 1.0.0
更新日期: 2026-08-31