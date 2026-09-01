#!/usr/bin/env python3
"""文件格式转换器 - 启动脚本"""

import sys
import os

# 添加项目根目录到路径
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

# 导入并运行应用
from src.main import run_app

if __name__ == '__main__':
    run_app()