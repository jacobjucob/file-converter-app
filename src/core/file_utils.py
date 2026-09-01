"""
文件工具模块 - 文件操作辅助函数
"""
import os
import shutil
import tempfile
import time
import gc
from pathlib import Path
from typing import Tuple, Optional

from ..utils.logger import get_logger

logger = get_logger()


class FileUtils:
    """文件操作工具类"""

    # 支持的输入格式
    INPUT_FORMATS = {
        'pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt',
        'txt', 'rtf', 'html', 'htm', 'md', 'csv', 'wps'
    }

    # 支持的输出格式
    OUTPUT_FORMATS = {
        'pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt',
        'txt', 'png', 'jpg', 'jpeg', 'bmp'
    }

    # 图片输出格式
    IMAGE_FORMATS = {'png', 'jpg', 'jpeg', 'bmp'}

    # 需要压缩质量的格式
    QUALITY_FORMATS = {'png', 'jpg', 'jpeg'}

    @staticmethod
    def get_file_size(file_path: str) -> str:
        """获取文件大小的人类可读表示"""
        size = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """获取文件扩展名（小写）"""
        return Path(file_path).suffix.lower().lstrip('.')

    @staticmethod
    def is_supported_input(file_path: str) -> bool:
        """检查是否为支持的输入格式"""
        ext = FileUtils.get_file_extension(file_path)
        return ext in FileUtils.INPUT_FORMATS

    @staticmethod
    def is_image_format(ext: str) -> bool:
        """检查是否为图片格式"""
        return ext in FileUtils.IMAGE_FORMATS

    @staticmethod
    def needs_quality(ext: str) -> bool:
        """检查是否需要压缩质量控制"""
        return ext in FileUtils.QUALITY_FORMATS

    @staticmethod
    def get_output_filename(input_path: str, output_ext: str) -> str:
        """生成输出文件名"""
        input_path = Path(input_path)
        return f"{input_path.stem}.{output_ext}"

    @staticmethod
    def copy_file(src: str, dst: str) -> bool:
        """复制文件"""
        try:
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            logger.error(f"复制文件失败: {e}")
            return False

    @staticmethod
    def atomic_replace(src: str, dst: str, max_retries: int = 10, retry_delay_ms: int = 300) -> bool:
        """
        原子替换文件
        先写入临时文件，再替换目标文件（跨驱动器安全，带重试机制）
        """
        dst_path = Path(dst)
        dst_dir = dst_path.parent

        try:
            dst_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"创建目标目录失败: {e}")
            return False

        # 清理可能残留的临时文件
        for existing_file in dst_dir.glob('.tmp_*'):
            try:
                if existing_file.is_file():
                    existing_file.unlink()
                    logger.debug(f"清理残留临时文件: {existing_file}")
            except Exception:
                pass

        # 创建临时文件
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode='wb',
                    dir=str(dst_dir),
                    prefix='.tmp_',
                    delete=False
            ) as tmp_file:
                with open(src, 'rb') as src_file:
                    shutil.copyfileobj(src_file, tmp_file)
                tmp_path = tmp_file.name
                logger.debug(f"创建临时文件: {tmp_path}")
        except Exception as e:
            logger.error(f"创建临时文件失败: {e}")
            return False

        for attempt in range(max_retries):
            try:
                # 如果目标文件存在，删除它
                if dst_path.exists():
                    dst_path.unlink()

                # 使用 shutil.move（更原子化）
                shutil.move(tmp_path, dst)
                logger.debug(f"替换成功: {dst}")
                return True

            except PermissionError as e:
                # 文件被占用，等待后重试
                logger.warning(f"文件被占用，第 {attempt + 1}/{max_retries} 次重试")
                time.sleep(retry_delay_ms / 1000.0)
                if attempt % 3 == 0:
                    gc.collect()

            except (OSError, shutil.Error) as e:
                # 可能是跨驱动器问题，尝试使用 copy2 + remove
                logger.warning(f"move 失败，尝试 copy2 方式: {e}")
                try:
                    if dst_path.exists():
                        dst_path.unlink()
                    shutil.copy2(tmp_path, dst)
                    os.remove(tmp_path)
                    logger.debug(f"copy2 替换成功: {dst}")
                    return True
                except PermissionError as pe:
                    logger.warning(f"copy2 方式也被占用，第 {attempt + 1}/{max_retries} 次重试: {pe}")
                    time.sleep(retry_delay_ms / 1000.0)
                except Exception as ce:
                    logger.error(f"copy2 方式失败: {ce}")
                    break

            except Exception as e:
                logger.error(f"原子替换失败: {e}")
                break

        # 所有重试都失败，清理临时文件
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                logger.debug(f"清理临时文件: {tmp_path}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")

        logger.error(f"原子替换失败: 重试 {max_retries} 次后仍然失败")
        return False

    @staticmethod
    def check_disk_space(path: str, required_bytes: int) -> bool:
        """
        检查磁盘空间是否充足（跨平台）
        """
        try:
            usage = shutil.disk_usage(path)
            free_space = usage.free
            return free_space >= required_bytes
        except Exception as e:
            logger.warning(f"检查磁盘空间失败: {e}")
            return True

    @staticmethod
    def is_empty_file(file_path: str) -> bool:
        """检查文件是否为空"""
        try:
            return os.path.getsize(file_path) == 0
        except Exception:
            return True

    @staticmethod
    def normalize_path(path: str) -> str:
        """标准化路径（处理Windows反斜杠）"""
        return str(Path(path).resolve())

    @staticmethod
    def create_temp_filename(prefix: str = '', suffix: str = '') -> str:
        """创建临时文件名"""
        return tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False).name


# 全局工具实例
file_utils = FileUtils()