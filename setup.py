"""
应用打包配置
"""
import sys
from setuptools import setup, find_packages

# PyInstaller配置
if 'pyinstaller' in sys.argv:
    import PyInstaller

    # 添加资源文件
    from PyInstaller.utils.hooks import collect_data_files

    datas = []
    # 收集依赖库的数据文件
    datas += collect_data_files('pdf2image')

    # 设置PyInstaller参数
    sys.argv = [
        'pyinstaller',
        '--name=FileConverter',
        '--windowed',
        '--onefile',
        '--add-data', 'src:src',
        '--collect-data', 'pdf2image',
        '--hidden-import', 'PIL',
        'src/main.py'
    ]

setup(
    name="file-converter",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'PyQt6>=6.5.0',
        'Pillow>=10.0.0',
        'pdf2image>=1.16.0',
        'PyInstaller>=6.0.0',
    ],
    entry_points={
        'console_scripts': [
            'file-converter=src.main:run_app',
        ],
    },
    author="File Converter",
    description="跨平台桌面文件格式转换应用",
    license="MIT",
)