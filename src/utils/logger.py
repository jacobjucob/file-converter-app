"""
日志模块 - 记录转换过程中的关键步骤
"""
import os
import logging
from datetime import datetime
from pathlib import Path


class AppLogger:
    """应用程序日志管理器"""

    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化日志配置"""
        # 获取项目根目录
        root_dir = Path(__file__).parent.parent.parent
        log_dir = root_dir / 'logs'
        log_dir.mkdir(exist_ok=True)

        # 按日期命名日志文件
        log_file = log_dir / f'app_{datetime.now().strftime("%Y%m%d")}.log'

        self._logger = logging.getLogger('FileConverter')
        self._logger.setLevel(logging.DEBUG)

        # 文件处理器 - 记录所有级别
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # 控制台处理器 - 记录INFO及以上
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

    def get_logger(self):
        """获取日志实例"""
        return self._logger


def get_logger():
    """获取日志记录器"""
    return AppLogger().get_logger()