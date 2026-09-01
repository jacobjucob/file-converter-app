"""验证所有组件是否正确安装"""

import os
import sys
import subprocess


def verify_libreoffice():
    print("\n1. 验证 LibreOffice...")

    paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    for path in paths:
        if os.path.exists(path):
            print(f"   ✓ 找到: {path}")
            return True

    # 尝试从PATH查找
    try:
        result = subprocess.run(['libreoffice', '--version'],
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"   ✓ LibreOffice 版本: {result.stdout.strip()}")
            return True
    except:
        pass

    print("   ✗ 未找到 LibreOffice")
    print("   请安装: https://www.libreoffice.org/download/download/")
    return False


def verify_poppler():
    print("\n2. 验证 Poppler...")

    # 检查项目目录
    project_dir = os.path.dirname(os.path.abspath(__file__))
    poppler_bin = os.path.join(project_dir, 'poppler', 'bin')

    if os.path.exists(poppler_bin):
        print(f"   ✓ 找到: {poppler_bin}")
        # 检查 pdftoppm.exe
        pdftoppm = os.path.join(poppler_bin, 'pdftoppm.exe')
        if os.path.exists(pdftoppm):
            print(f"   ✓ 找到 pdftoppm.exe")
        return True

    # 检查系统 PATH
    for path in os.environ.get('PATH', '').split(os.pathsep):
        if 'poppler' in path.lower() and os.path.exists(path):
            print(f"   ✓ 从PATH找到: {path}")
            return True

    print("   ✗ 未找到 Poppler")
    print("   预览功能将不可用")
    print("   下载: https://github.com/oschwartz10612/poppler-windows/releases/")
    return False


def verify_python_packages():
    print("\n3. 验证 Python 包...")

    packages = {
        'PyQt6': 'PyQt6',
        'PIL': 'Pillow',
        'pdf2image': 'pdf2image'
    }
    all_ok = True

    for pkg_name, display_name in packages.items():
        try:
            __import__(pkg_name)
            print(f"   ✓ {display_name}")
        except ImportError:
            print(f"   ✗ {display_name} 未安装")
            all_ok = False

    return all_ok


def main():
    print("=" * 50)
    print("文件格式转换器 - 环境验证")
    print("=" * 50)

    results = []
    results.append(verify_libreoffice())
    results.append(verify_poppler())
    results.append(verify_python_packages())

    print("\n" + "=" * 50)
    if all(results):
        print("✓ 所有组件验证通过！可以运行应用。")
        print("\n运行命令: python run.py")
    else:
        print("✗ 部分组件未就绪，请根据上述提示进行配置。")
        if not results[0]:
            print("\n请先安装 LibreOffice")
        if not results[1]:
            print("\n预览功能需要 Poppler，可跳过安装（不影响转换功能）")
    print("=" * 50)
    return all(results)


if __name__ == '__main__':
    sys.exit(0 if main() else 1)