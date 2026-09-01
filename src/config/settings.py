"""
配置管理模块 - 管理应用设置和目录记忆
"""
import json
import os
from pathlib import Path
from typing import Optional


class Settings:
    """应用配置管理器"""

    _instance = None
    _settings = {}
    _config_file = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化配置"""
        # 配置文件路径
        root_dir = Path(__file__).parent.parent.parent
        config_dir = root_dir / 'config'
        config_dir.mkdir(exist_ok=True)
        self._config_file = config_dir / 'settings.json'

        # 默认配置
        self._settings = {
            'input_dir': '',
            'output_dir': '',
            'last_input_format': 'pdf',
            'last_output_format': 'pdf',
            'compression_quality': '100%'
        }

        # 加载已有配置
        self.load()

    def load(self):
        """加载配置文件"""
        if self._config_file.exists():
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self._settings.update(loaded)
            except Exception as e:
                print(f"加载配置文件失败: {e}")

    def save(self):
        """保存配置文件"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False

    def get(self, key: str, default=None):
        """获取配置值"""
        return self._settings.get(key, default)

    def set(self, key: str, value):
        """设置配置值"""
        self._settings[key] = value
        self.save()

    @property
    def input_dir(self) -> str:
        return self.get('input_dir', '')

    @input_dir.setter
    def input_dir(self, value: str):
        self.set('input_dir', value)

    @property
    def output_dir(self) -> str:
        return self.get('output_dir', '')

    @output_dir.setter
    def output_dir(self, value: str):
        self.set('output_dir', value)

    @property
    def compression_quality(self) -> str:
        return self.get('compression_quality', '100%')

    @compression_quality.setter
    def compression_quality(self, value: str):
        self.set('compression_quality', value)


def get_settings():
    """获取配置实例"""
    return Settings()