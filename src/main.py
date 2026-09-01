#!/usr/bin/env python3
"""
文件格式转换器 - 主程序入口
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gui.main_window import run_app

if __name__ == '__main__':
    run_app()