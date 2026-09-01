"""
主窗口模块 - 应用主界面（现代专业工具 · 冷色系 · Windows 风格）
"""
import os
import sys
import shutil
import time
from pathlib import Path
from typing import Optional, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QProgressBar,
    QFileDialog, QMessageBox, QGroupBox, QApplication,
    QDialog, QFrame, QSizePolicy, QScrollArea,
    QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QPixmap, QColor, QTextCursor

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..core.converter import get_converter, ConversionError, ConversionTimeoutError
from ..core.file_utils import file_utils
from ..config.settings import get_settings
from ..utils.logger import get_logger

logger = get_logger()
settings = get_settings()


class ConversionWorker(QThread):
    """转换工作线程"""

    progress = pyqtSignal(float)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    timeout = pyqtSignal()

    def __init__(self, input_path: str, output_format: str, output_dir: str, quality: Optional[str] = None):
        super().__init__()
        self.input_path = input_path
        self.output_format = output_format
        self.output_dir = output_dir
        self.quality = quality
        self._is_cancelled = False

    def run(self):
        try:
            converter = get_converter()
            output_path = converter.convert(
                self.input_path,
                self.output_format,
                self.output_dir,
                self.quality,
                self.progress.emit
            )
            if not self._is_cancelled:
                self.finished.emit(output_path)
        except ConversionTimeoutError:
            self.timeout.emit()
        except ConversionError as e:
            self.error.emit(str(e))
        except Exception as e:
            logger.error(f"转换异常: {e}")
            self.error.emit(f"转换失败: {str(e)}")

    def cancel(self):
        self._is_cancelled = True


class MainWindow(QMainWindow):
    """主窗口 - 现代专业工具 · 冷色系 · Windows 风格"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件转换器")
        self.setMinimumSize(960, 680)

        # 状态变量
        self.input_file_path = None
        self.output_dir_path = settings.get('output_dir', '')
        self.output_file_path = None
        self.conversion_worker = None
        self.progress_timer = None
        self.last_progress_time = 0
        self.is_converting = False
        self.start_time = None

        # 设置UI
        self._setup_ui()
        self._load_settings()
        self._update_controls()

    def _setup_ui(self):
        """设置用户界面"""

        # 主窗口样式 - 冷色系
        self.setStyleSheet("""
            QMainWindow {
                background: rgba(255, 255, 255, 0.85);
                backdrop-filter: blur(16px);
            }
        """)

        # 中央容器
        central_widget = QWidget()
        central_widget.setStyleSheet("background: transparent;")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 标题栏
        title_bar = self._create_title_bar()
        main_layout.addWidget(title_bar)

        # 主体内容
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(24)
        content_layout.setContentsMargins(24, 20, 24, 16)

        left_panel = self._create_left_panel()
        content_layout.addWidget(left_panel, 1)

        right_panel = self._create_right_panel()
        content_layout.addWidget(right_panel, 1)

        main_layout.addWidget(content_widget, 1)

        # 底部状态栏
        status_bar = self._create_status_bar()
        main_layout.addWidget(status_bar)

    def _create_title_bar(self) -> QWidget:
        """创建标题栏"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(230, 240, 250, 0.70);
                border-bottom: 1px solid rgba(0, 0, 0, 0.06);
            }
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(16, 8, 16, 8)

        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        icon_label = QLabel("📄")
        icon_label.setStyleSheet("font-size: 16px; background: transparent; opacity: 0.7;")
        left_layout.addWidget(icon_label)

        name_label = QLabel("文件转换器")
        name_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 500;
            color: #1a2a3a;
            background: transparent;
            letter-spacing: 0.1px;
        """)
        left_layout.addWidget(name_label)
        left_layout.addStretch()

        layout.addWidget(left_widget, 1)

        return widget

    def _create_left_panel(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._create_file_section())
        layout.addWidget(self._create_settings_section())
        layout.addWidget(self._create_action_section())
        layout.addStretch()

        return widget

    def _create_section(self, title: str, emoji: str) -> QGroupBox:
        group = QGroupBox()
        group.setStyleSheet("""
            QGroupBox {
                background: rgba(255, 255, 255, 0.50);
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.60);
                padding: 14px 16px 16px;
                margin-top: 0px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 0px;
                padding: 0px 0px 10px 0px;
                font-size: 11px;
                font-weight: 600;
                color: #4a5a6a;
                letter-spacing: 0.4px;
                text-transform: uppercase;
                background: transparent;
            }
            QGroupBox:hover {
                border-color: rgba(255, 255, 255, 0.60);
            }
        """)
        group.setTitle(f"{emoji} {title}")
        return group

    def _create_file_section(self) -> QWidget:
        section = self._create_section("选择文件", "📂")
        layout = QVBoxLayout(section)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 4, 0, 0)

        self.file_card = QWidget()
        self.file_card.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.70);
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.80);
                padding: 10px 12px;
                outline: none;
            }
            QWidget:hover {
                border-color: rgba(42, 109, 244, 0.15);
            }
            QWidget:focus {
                outline: none;
            }
        """)
        card_layout = QHBoxLayout(self.file_card)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(0, 0, 0, 0)

        self.file_icon_label = QLabel("📄")
        self.file_icon_label.setFixedSize(36, 36)
        self.file_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_icon_label.setStyleSheet("""
            font-size: 20px;
            background: rgba(42, 109, 244, 0.06);
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.40);
        """)
        card_layout.addWidget(self.file_icon_label)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(0)
        info_layout.setContentsMargins(0, 0, 0, 0)

        self.file_name_label = QLabel("未选择文件")
        self.file_name_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #1a2a3a;
            background: transparent;
        """)
        info_layout.addWidget(self.file_name_label)

        self.file_meta_label = QLabel("点击「浏览」选择文件")
        self.file_meta_label.setStyleSheet("""
            font-size: 11px;
            color: #6a7a8a;
            background: transparent;
        """)
        info_layout.addWidget(self.file_meta_label)

        card_layout.addWidget(info_widget, 1)

        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setSpacing(4)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background: rgba(42, 109, 244, 0.20);
                color: rgba(20, 60, 160, 0.90);
                border: none;
                padding: 4px 14px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                outline: none;
            }
            QPushButton:hover {
                background: rgba(42, 109, 244, 0.35);
                color: rgba(10, 40, 130, 1.00);
            }
            QPushButton:pressed {
                background: rgba(42, 109, 244, 0.08);
                color: rgba(20, 60, 160, 0.40);
            }
            QPushButton:disabled {
                background: rgba(42, 109, 244, 0.06);
                color: rgba(20, 60, 160, 0.30);
            }
            QPushButton:focus {
                outline: none;
            }
        """)
        self.browse_btn.clicked.connect(self.on_select_file)
        btn_layout.addWidget(self.browse_btn)

        self.clear_btn = QPushButton("✕")
        self.clear_btn.setFixedSize(26, 26)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                color: #aabac8;
                outline: none;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 0.04);
                color: #4a5a6a;
            }
            QPushButton:pressed {
                color: #c0d0de;
                background: transparent;
            }
            QPushButton:focus {
                outline: none;
            }
        """)
        self.clear_btn.clicked.connect(self._clear_file)
        btn_layout.addWidget(self.clear_btn)

        card_layout.addWidget(btn_widget)

        layout.addWidget(self.file_card)

        return section

    def _create_settings_section(self) -> QWidget:
        section = self._create_section("转换设置", "⚙️")
        layout = QVBoxLayout(section)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 4, 0, 0)

        # 输出目录行
        row0 = QWidget()
        row0_layout = QHBoxLayout(row0)
        row0_layout.setSpacing(8)
        row0_layout.setContentsMargins(0, 0, 0, 0)

        label0 = QLabel("输出目录")
        label0.setStyleSheet("""
            font-size: 12px;
            font-weight: 500;
            color: #3d4e5e;
            background: transparent;
            min-width: 36px;
        """)
        row0_layout.addWidget(label0)

        self.output_dir_label = QLabel("未选择")
        self.output_dir_label.setStyleSheet("""
            font-size: 12px;
            color: #6a7a8a;
            background: rgba(255, 255, 255, 0.50);
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 4px;
            padding: 4px 10px;
        """)
        self.output_dir_label.setWordWrap(True)
        row0_layout.addWidget(self.output_dir_label, 1)

        self.output_dir_btn = QPushButton("选择")
        self.output_dir_btn.setStyleSheet("""
            QPushButton {
                background: rgba(42, 109, 244, 0.20);
                color: rgba(20, 60, 160, 0.90);
                border: none;
                padding: 4px 14px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                outline: none;
            }
            QPushButton:hover {
                background: rgba(42, 109, 244, 0.35);
                color: rgba(10, 40, 130, 1.00);
            }
            QPushButton:pressed {
                background: rgba(42, 109, 244, 0.08);
                color: rgba(20, 60, 160, 0.40);
            }
            QPushButton:focus {
                outline: none;
            }
        """)
        self.output_dir_btn.clicked.connect(self.on_select_output_dir)
        row0_layout.addWidget(self.output_dir_btn)

        layout.addWidget(row0)

        # 转为行
        row1 = QWidget()
        row1_layout = QHBoxLayout(row1)
        row1_layout.setSpacing(8)
        row1_layout.setContentsMargins(0, 0, 0, 0)

        label1 = QLabel("转为")
        label1.setStyleSheet("""
            font-size: 12px;
            font-weight: 500;
            color: #3d4e5e;
            background: transparent;
            min-width: 36px;
        """)
        row1_layout.addWidget(label1)

        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(sorted(file_utils.OUTPUT_FORMATS))
        self.output_format_combo.currentTextChanged.connect(self.on_format_changed)
        self.output_format_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.70);
                border: 1px solid rgba(0, 0, 0, 0.06);
                border-radius: 4px;
                padding: 4px 12px 4px 10px;
                font-size: 12px;
                font-weight: 500;
                color: #1a2a3a;
                min-width: 100px;
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #6a7a8a;
                margin-right: 2px;
            }
            QComboBox:hover {
                border-color: rgba(42, 109, 244, 0.15);
            }
            QComboBox:focus {
                border-color: rgba(42, 109, 244, 0.30);
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                border: 1px solid rgba(0, 0, 0, 0.06);
                border-radius: 4px;
                padding: 4px;
                selection-background-color: rgba(42, 109, 244, 0.08);
                selection-color: #1a2a3a;
            }
        """)
        row1_layout.addWidget(self.output_format_combo)
        row1_layout.addStretch()

        layout.addWidget(row1)

        # 质量行
        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)
        row2_layout.setSpacing(8)
        row2_layout.setContentsMargins(0, 0, 0, 0)

        self.quality_label = QLabel("质量")
        self.quality_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 500;
            color: #3d4e5e;
            background: transparent;
            min-width: 36px;
        """)
        self.quality_label.setVisible(False)
        row2_layout.addWidget(self.quality_label)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(['100%', '90%', '80%', '60%', '40%', '20%'])
        self.quality_combo.setCurrentText(settings.compression_quality)
        self.quality_combo.setVisible(False)
        self.quality_combo.setStyleSheet(self.output_format_combo.styleSheet())
        row2_layout.addWidget(self.quality_combo)

        self.quality_hint = QLabel("仅图片格式")
        self.quality_hint.setStyleSheet("""
            font-size: 11px;
            color: #8a9aa8;
            background: transparent;
            opacity: 0.7;
        """)
        self.quality_hint.setVisible(False)
        row2_layout.addWidget(self.quality_hint)
        row2_layout.addStretch()

        layout.addWidget(row2)

        return section

    def _create_action_section(self) -> QWidget:
        section = self._create_section("操作", "▶")
        layout = QVBoxLayout(section)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 4, 0, 0)

        self.convert_btn = QPushButton("▶ 开始转换")
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background: rgba(42, 109, 244, 0.20);
                color: rgba(20, 60, 160, 0.90);
                border: none;
                padding: 9px 20px;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 600;
                outline: none;
            }
            QPushButton:hover {
                background: rgba(42, 109, 244, 0.35);
                color: rgba(10, 40, 130, 1.00);
            }
            QPushButton:pressed {
                background: rgba(42, 109, 244, 0.08);
                color: rgba(20, 60, 160, 0.35);
            }
            QPushButton:disabled {
                background: rgba(42, 109, 244, 0.06);
                color: rgba(20, 60, 160, 0.30);
            }
            QPushButton:focus {
                outline: none;
            }
        """)
        self.convert_btn.clicked.connect(self.on_convert)
        layout.addWidget(self.convert_btn)

        progress_widget = QWidget()
        progress_layout = QHBoxLayout(progress_widget)
        progress_layout.setSpacing(8)
        progress_layout.setContentsMargins(0, 0, 0, 0)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(0, 0, 0, 0.06);
                border-radius: 4px;
                height: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background: rgba(42, 109, 244, 0.50);
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("0%")
        self.progress_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 500;
            color: rgba(42, 109, 244, 0.60);
            background: transparent;
            min-width: 32px;
            text-align: right;
        """)
        progress_layout.addWidget(self.progress_label)

        layout.addWidget(progress_widget)

        return section

    def _create_right_panel(self) -> QWidget:
        """创建右侧日志面板"""
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # 日志区域
        log_section = QGroupBox()
        log_section.setStyleSheet("""
            QGroupBox {
                background: rgba(255, 255, 255, 0.50);
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.60);
                padding: 14px 16px 16px;
                margin-top: 0px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 0px;
                padding: 0px 0px 10px 0px;
                font-size: 11px;
                font-weight: 600;
                color: #4a5a6a;
                letter-spacing: 0.4px;
                text-transform: uppercase;
                background: transparent;
            }
            QGroupBox:hover {
                border-color: rgba(255, 255, 255, 0.60);
            }
        """)
        log_section.setTitle("📋 日志")
        log_section.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        log_layout = QVBoxLayout(log_section)
        log_layout.setSpacing(0)
        log_layout.setContentsMargins(0, 4, 0, 0)

        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background: rgba(255, 255, 255, 0.30);
                border: 1px solid rgba(255, 255, 255, 0.40);
                border-radius: 6px;
                padding: 12px;
                font-family: "Consolas", "Microsoft YaHei", monospace;
                font-size: 12px;
                color: #1a2a3a;
                line-height: 1.6;
            }
            QTextEdit:focus {
                border-color: rgba(42, 109, 244, 0.30);
            }
            QScrollBar:vertical {
                background: rgba(0, 0, 0, 0.04);
                border-radius: 3px;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 0, 0, 0.15);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0, 0, 0, 0.25);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        log_layout.addWidget(self.log_text)

        # 初始日志
        self._append_log("📌 等待转换...", "#7a8a9a")

        layout.addWidget(log_section, 1)

        return widget

    def _append_log(self, text: str, color: str = "#1a2a3a"):
        """添加日志"""
        self.log_text.append(f'<span style="color:{color};">{text}</span>')
        # 滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def _clear_log(self):
        """清空日志"""
        self.log_text.clear()

    def _create_status_bar(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.20);
                border-top: 1px solid rgba(0, 0, 0, 0.04);
                padding: 10px 24px 12px;
            }
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setSpacing(6)
        status_layout.setContentsMargins(0, 0, 0, 0)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("""
            font-size: 8px;
            color: #8a9aa8;
            background: transparent;
        """)
        status_layout.addWidget(self.status_dot)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("""
            font-size: 11px;
            color: #6a7a8a;
            background: transparent;
        """)
        status_layout.addWidget(self.status_label)

        layout.addWidget(status_widget)

        self.log_link = QPushButton("📋 查看日志")
        self.log_link.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 11px;
                color: #6a7a8a;
                outline: none;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 0.04);
                color: #2a3a4a;
            }
            QPushButton:focus {
                outline: none;
            }
        """)
        self.log_link.clicked.connect(self._open_log_folder)
        layout.addWidget(self.log_link)

        return widget

    def _load_settings(self):
        default_output = settings.get('last_output_format', 'pdf')
        index = self.output_format_combo.findText(default_output)
        if index >= 0:
            self.output_format_combo.setCurrentIndex(index)

        # 加载记忆的输出目录
        saved_output_dir = settings.get('output_dir', '')
        if saved_output_dir and os.path.exists(saved_output_dir):
            self.output_dir_path = saved_output_dir
            self.output_dir_label.setText(saved_output_dir)
            self.output_dir_label.setToolTip(saved_output_dir)
        else:
            self.output_dir_path = ''
            self.output_dir_label.setText("未选择")

    def _update_controls(self):
        has_file = self.input_file_path is not None
        has_output_dir = bool(self.output_dir_path) and os.path.exists(self.output_dir_path)
        is_converting = self.is_converting

        self.browse_btn.setEnabled(not is_converting)
        self.output_dir_btn.setEnabled(not is_converting)
        self.convert_btn.setEnabled(has_file and has_output_dir and not is_converting)
        self.output_format_combo.setEnabled(not is_converting)
        self.quality_combo.setEnabled(not is_converting)

    def _clear_file(self):
        self.input_file_path = None
        self.file_name_label.setText("未选择文件")
        self.file_meta_label.setText("点击「浏览」选择文件")
        self.file_icon_label.setText("📄")
        self._clear_log()
        self._append_log("📌 等待转换...", "#7a8a9a")
        self._update_controls()

    def on_select_file(self):
        last_dir = settings.input_dir or os.path.expanduser('~')

        dialog = QFileDialog(self)
        dialog.setWindowTitle("选择待转换文件")
        dialog.setDirectory(last_dir)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        input_formats = sorted(file_utils.INPUT_FORMATS)
        supported_filter = f"支持的格式 (*.{', *.'.join(input_formats)})"
        all_files_filter = "所有文件 (*.*)"
        dialog.setNameFilter(f"{supported_filter};;{all_files_filter}")
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.selectNameFilter(all_files_filter)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            file_path = dialog.selectedFiles()[0]
            if not file_path:
                return

            ext = file_utils.get_file_extension(file_path)
            if ext not in file_utils.INPUT_FORMATS:
                QMessageBox.warning(
                    self,
                    "不支持的格式",
                    f"不支持的文件格式：.{ext}\n请选择以下格式之一：\n{', '.join(sorted(file_utils.INPUT_FORMATS))}"
                )
                return

            self.input_file_path = file_path
            settings.input_dir = os.path.dirname(file_path)

            file_name = os.path.basename(file_path)
            file_size = file_utils.get_file_size(file_path)
            self.file_name_label.setText(file_name)
            self.file_meta_label.setText(f"{file_size} · {time.strftime('%Y/%m/%d', time.localtime(os.path.getmtime(file_path)))}")

            icon_map = {
                'pdf': '📄', 'docx': '📝', 'doc': '📝',
                'xlsx': '📊', 'xls': '📊',
                'pptx': '📽️', 'ppt': '📽️',
                'txt': '📃', 'rtf': '📃',
                'html': '🌐', 'htm': '🌐',
                'md': '📃', 'csv': '📊',
                'wps': '📝', 'png': '🖼️',
                'jpg': '🖼️', 'jpeg': '🖼️',
                'bmp': '🖼️'
            }
            self.file_icon_label.setText(icon_map.get(ext, '📄'))

            if ext in file_utils.OUTPUT_FORMATS:
                index = self.output_format_combo.findText(ext)
                if index >= 0:
                    self.output_format_combo.setCurrentIndex(index)

            self._clear_log()
            self._append_log(f"📂 已选择文件: {file_name}", "#3d4e5e")
            self._append_log(f"📏 文件大小: {file_size}", "#3d4e5e")
            self._append_log("📌 等待转换...", "#7a8a9a")

            self._update_controls()

    def on_select_output_dir(self):
        """选择输出目录"""
        last_dir = settings.get('output_dir', '') or os.path.expanduser('~')

        output_dir = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            last_dir
        )

        if output_dir:
            self.output_dir_path = output_dir
            self.output_dir_label.setText(output_dir)
            self.output_dir_label.setToolTip(output_dir)
            settings.set('output_dir', output_dir)
            self._append_log(f"📁 输出目录: {output_dir}", "#3d4e5e")
            self._update_controls()

    def on_format_changed(self, format_text: str):
        settings.set('last_output_format', format_text)

        show_quality = file_utils.needs_quality(format_text.lower())
        self.quality_label.setVisible(show_quality)
        self.quality_combo.setVisible(show_quality)
        self.quality_hint.setVisible(show_quality)

        self._update_controls()

    def on_convert(self):
        if not self.input_file_path:
            QMessageBox.warning(self, "警告", "请先选择待转换文件")
            return

        if not self.output_dir_path or not os.path.exists(self.output_dir_path):
            QMessageBox.warning(self, "警告", "请先选择有效的输出目录")
            return

        if file_utils.is_empty_file(self.input_file_path):
            QMessageBox.warning(self, "警告", "文件为空，无法转换")
            return

        # 检查目标文件是否已存在
        output_format = self.output_format_combo.currentText().lower()
        output_filename = file_utils.get_output_filename(self.input_file_path, output_format)
        target_path = os.path.join(self.output_dir_path, output_filename)

        if os.path.exists(target_path):
            reply = QMessageBox.question(
                self,
                "文件已存在",
                f"输出目录已存在同名文件：{output_filename}\n是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        quality = None
        if file_utils.needs_quality(output_format):
            quality = self.quality_combo.currentText()
            settings.compression_quality = quality

        self.is_converting = True
        self.start_time = time.time()
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("⏳ 转换中...")
        self.browse_btn.setEnabled(False)
        self.output_dir_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")
        self.status_label.setText("转换中...")
        self.status_dot.setStyleSheet("font-size: 8px; color: rgba(42, 109, 244, 0.60); background: transparent;")

        self._clear_log()
        self._append_log(f"🚀 开始转换...", "#2a6df4")
        self._append_log(f"📂 输入: {os.path.basename(self.input_file_path)}", "#3d4e5e")
        self._append_log(f"📁 输出目录: {self.output_dir_path}", "#3d4e5e")
        self._append_log(f"📄 目标格式: {output_format.upper()}", "#3d4e5e")
        if quality:
            self._append_log(f"⚙️ 压缩质量: {quality}", "#3d4e5e")

        self._update_controls()

        self.conversion_worker = ConversionWorker(
            self.input_file_path,
            output_format,
            self.output_dir_path,
            quality
        )
        self.conversion_worker.progress.connect(self.on_conversion_progress)
        self.conversion_worker.finished.connect(self.on_conversion_finished)
        self.conversion_worker.error.connect(self.on_conversion_error)
        self.conversion_worker.timeout.connect(self.on_conversion_timeout)
        self.conversion_worker.start()

        self.last_progress_time = time.time()
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._check_progress)
        self.progress_timer.start(1000)

    def _check_progress(self):
        if self.conversion_worker and not self.conversion_worker.isRunning():
            self.progress_timer.stop()
            return
        if time.time() - self.last_progress_time > 2:
            logger.warning("进度更新超时，继续等待")

    def on_conversion_progress(self, value: float):
        self.progress_bar.setValue(int(value))
        self.progress_label.setText(f"{int(value)}%")
        self.last_progress_time = time.time()
        self.status_label.setText(f"转换中... {int(value)}%")

    def on_conversion_finished(self, output_path: str):
        elapsed = time.time() - self.start_time
        elapsed_str = f"{elapsed:.1f}s"

        self.progress_bar.setValue(100)
        self.progress_label.setText("100%")
        self.status_label.setText("转换完成")
        self.status_dot.setStyleSheet("font-size: 8px; color: rgba(42, 154, 74, 0.60); background: transparent;")

        self.output_file_path = output_path
        self._update_controls()

        self._restore_controls()

        logger.info(f"转换完成: {output_path}")

        # 日志输出
        self._append_log("", "")
        self._append_log("✅ 转换成功！", "#2a9a4a")
        self._append_log(f"⏱️ 耗时: {elapsed_str}", "#3d4e5e")
        self._append_log(f"📁 文件路径: {output_path}", "#1a2a3a")

        # 显示 Toast 通知
        self._show_toast(f"✅ 文件格式转换完成！\n{os.path.basename(output_path)}")

    def _show_toast(self, message: str):
        """显示 Toast 通知"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("提示")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setStyleSheet("""
            QMessageBox {
                background: #ffffff;
                border-radius: 6px;
            }
            QMessageBox QLabel {
                font-size: 13px;
                color: #1a2a3a;
                padding: 8px 0;
            }
            QMessageBox QPushButton {
                background: rgba(42, 109, 244, 0.20);
                color: rgba(20, 60, 160, 0.90);
                border: none;
                border-radius: 4px;
                padding: 6px 24px;
                font-weight: 500;
                min-width: 80px;
                outline: none;
            }
            QMessageBox QPushButton:hover {
                background: rgba(42, 109, 244, 0.35);
                color: rgba(10, 40, 130, 1.00);
            }
            QMessageBox QPushButton:pressed {
                background: rgba(42, 109, 244, 0.08);
                color: rgba(20, 60, 160, 0.35);
            }
            QMessageBox QPushButton:focus {
                outline: none;
            }
        """)
        msg_box.exec()

    def on_conversion_error(self, error_msg: str):
        self.status_label.setText("转换失败")
        self.status_dot.setStyleSheet("font-size: 8px; color: rgba(220, 38, 38, 0.60); background: transparent;")
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")

        self._restore_controls()

        # 日志输出
        self._append_log("", "")
        self._append_log("❌ 转换失败", "#dc2626")
        self._append_log(f"错误信息: {error_msg}", "#dc2626")

        QMessageBox.critical(self, "转换错误", error_msg)
        logger.error(f"转换错误: {error_msg}")

    def on_conversion_timeout(self):
        self.status_label.setText("转换超时")
        self.status_dot.setStyleSheet("font-size: 8px; color: rgba(220, 38, 38, 0.60); background: transparent;")
        self.progress_bar.setValue(0)
        self.progress_label.setText("0%")

        self._restore_controls()

        # 日志输出
        self._append_log("", "")
        self._append_log("⏰ 转换超时（180秒）", "#dc2626")
        self._append_log("请重试或检查文件是否有效", "#dc2626")

        QMessageBox.warning(self, "转换超时", "转换超时（180秒），请重试或检查文件是否有效")
        logger.warning("转换超时")

    def _restore_controls(self):
        self.is_converting = False
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("▶ 开始转换")
        self.browse_btn.setEnabled(True)
        self.output_dir_btn.setEnabled(True)

        if self.progress_timer:
            self.progress_timer.stop()

        self._update_controls()

    def _open_log_folder(self):
        import subprocess
        import platform

        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        system = platform.system()
        try:
            if system == 'Windows':
                os.startfile(log_dir)
            elif system == 'Darwin':
                subprocess.run(['open', log_dir])
            else:
                subprocess.run(['xdg-open', log_dir])
        except Exception as e:
            logger.warning(f"打开日志文件夹失败: {e}")
            QMessageBox.information(self, "日志文件夹", f"日志文件位于：\n{log_dir}")

    def closeEvent(self, event):
        if self.output_file_path and os.path.exists(self.output_file_path):
            pass
        event.accept()


def run_app():
    """运行应用程序"""
    app = QApplication(sys.argv)
    app.setApplicationName("文件转换器")
    app.setApplicationDisplayName("文件转换器")

    app.setStyleSheet("""
        QToolTip {
            background: #ffffff;
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 4px;
            padding: 4px 8px;
            color: #1a2a3a;
            font-size: 11px;
        }
        QMessageBox {
            background: #ffffff;
        }
        QMessageBox QPushButton {
            background: rgba(42, 109, 244, 0.20);
            color: rgba(20, 60, 160, 0.90);
            border: none;
            border-radius: 4px;
            padding: 6px 20px;
            font-weight: 500;
            min-width: 80px;
            outline: none;
        }
        QMessageBox QPushButton:hover {
            background: rgba(42, 109, 244, 0.35);
            color: rgba(10, 40, 130, 1.00);
        }
        QMessageBox QPushButton:pressed {
            background: rgba(42, 109, 244, 0.08);
            color: rgba(20, 60, 160, 0.35);
        }
        QMessageBox QPushButton:focus {
            outline: none;
        }
    """)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())