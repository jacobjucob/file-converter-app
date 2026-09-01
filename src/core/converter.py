"""
转换核心模块 - 调用LibreOffice进行文档转换
"""
import os
import subprocess
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Optional, Callable, List

from PIL import Image

from ..utils.logger import get_logger
from .file_utils import file_utils

logger = get_logger()


class ConversionError(Exception):
    """转换异常"""
    pass


class ConversionTimeoutError(Exception):
    """转换超时异常"""
    pass


class Converter:
    """文档转换器"""

    # 格式映射（LibreOffice输出格式参数）
    FORMAT_MAP = {
        'pdf': 'pdf',
        'docx': 'docx',
        'doc': 'doc',
        'xlsx': 'xlsx',
        'xls': 'xls',
        'pptx': 'pptx',
        'ppt': 'ppt',
        'txt': 'txt',
        'rtf': 'rtf',
        'html': 'html',
        'png': 'png',
        'jpg': 'jpg',
        'jpeg': 'jpg',
        'bmp': 'bmp',
        'csv': 'csv',
        'md': 'md',
        'wps': 'wps',
    }

    # 图片格式质量参数映射
    QUALITY_MAP = {
        '100%': {'png': 0, 'jpg': 100},
        '90%': {'png': 1, 'jpg': 90},
        '80%': {'png': 2, 'jpg': 80},
        '60%': {'png': 4, 'jpg': 60},
        '40%': {'png': 6, 'jpg': 40},
        '20%': {'png': 9, 'jpg': 20},
    }

    # 定义各输入格式支持的输出格式
    SUPPORTED_CONVERSIONS = {
        'pdf': {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'docx'},
        'docx': {'docx', 'doc', 'pdf', 'txt', 'rtf', 'html', 'png', 'jpg', 'jpeg', 'bmp'},
        'doc': {'doc', 'docx', 'pdf', 'txt', 'rtf', 'html', 'png', 'jpg', 'jpeg', 'bmp'},
        'xlsx': {'xlsx', 'xls', 'pdf', 'csv', 'html', 'png', 'jpg', 'jpeg', 'bmp'},
        'xls': {'xls', 'xlsx', 'pdf', 'csv', 'html', 'png', 'jpg', 'jpeg', 'bmp'},
        'pptx': {'pptx', 'ppt', 'pdf', 'png', 'jpg', 'jpeg', 'bmp'},
        'ppt': {'ppt', 'pptx', 'pdf', 'png', 'jpg', 'jpeg', 'bmp'},
        'txt': {'txt', 'pdf', 'html', 'docx', 'doc'},
        'rtf': {'rtf', 'docx', 'doc', 'pdf', 'html', 'txt'},
        'html': {'html', 'pdf', 'docx', 'doc', 'txt'},
        'htm': {'htm', 'html', 'pdf', 'docx', 'doc', 'txt'},
        'md': {'md', 'html', 'pdf', 'docx', 'doc', 'txt'},
        'csv': {'csv', 'xlsx', 'xls', 'pdf', 'html'},
        'wps': {'wps', 'docx', 'doc', 'pdf', 'txt'},
    }

    def __init__(self, timeout: int = 180):
        self.timeout = timeout
        self._libreoffice_path = None
        self._find_libreoffice()

    def _find_libreoffice(self):
        """查找LibreOffice可执行文件"""
        import sys
        platform = sys.platform

        if platform == 'win32':
            possible_paths = [
                'C:/Program Files/LibreOffice/program/soffice.exe',
                'C:/Program Files (x86)/LibreOffice/program/soffice.exe',
                'C:/Program Files/LibreOffice/program/soffice.bin',
                'C:/Program Files (x86)/LibreOffice/program/soffice.bin',
            ]

            for program_dir in ['Program Files', 'Program Files (x86)']:
                base_path = f'C:/{program_dir}/LibreOffice'
                if os.path.exists(base_path):
                    try:
                        for item in os.listdir(base_path):
                            if item.startswith('LibreOffice'):
                                exe_path = os.path.join(base_path, item, 'program', 'soffice.exe')
                                if os.path.exists(exe_path):
                                    possible_paths.append(exe_path)
                    except Exception:
                        pass

            for path in possible_paths:
                if os.path.exists(path):
                    self._libreoffice_path = path
                    logger.info(f"找到LibreOffice: {path}")
                    return

            libreoffice = shutil.which('libreoffice') or shutil.which('soffice')
            if libreoffice:
                self._libreoffice_path = libreoffice
                logger.info(f"从PATH找到LibreOffice: {libreoffice}")
                return

            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                   r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\soffice.exe")
                path = winreg.QueryValue(key, None)
                if path and os.path.exists(path):
                    self._libreoffice_path = path
                    logger.info(f"从注册表找到LibreOffice: {path}")
                    return
            except Exception:
                pass

        elif platform == 'darwin':
            paths = [
                '/Applications/LibreOffice.app/Contents/MacOS/soffice',
                '/Applications/LibreOffice.app/Contents/MacOS/soffice.bin',
            ]
            for path in paths:
                if os.path.exists(path):
                    self._libreoffice_path = path
                    logger.info(f"找到LibreOffice: {path}")
                    return

        else:
            paths = [
                '/usr/bin/libreoffice',
                '/usr/bin/soffice',
            ]
            for path in paths:
                if os.path.exists(path):
                    self._libreoffice_path = path
                    logger.info(f"找到LibreOffice: {path}")
                    return

        logger.error("未找到LibreOffice")
        raise ConversionError(
            "未找到LibreOffice，请安装LibreOffice\n"
            "下载地址: https://www.libreoffice.org/download/download/"
        )

    def _is_conversion_supported(self, input_format: str, output_format: str) -> bool:
        if input_format == output_format:
            return True
        supported = self.SUPPORTED_CONVERSIONS.get(input_format, set())
        return output_format in supported

    def _get_ascii_temp_path(self, input_path: str) -> tuple:
        temp_dir = tempfile.mkdtemp(prefix='lo_convert_')
        ext = file_utils.get_file_extension(input_path)
        ascii_filename = f"input_{int(time.time())}.{ext}"
        ascii_path = os.path.join(temp_dir, ascii_filename)
        shutil.copy2(input_path, ascii_path)
        logger.debug(f"复制文件到 ASCII 临时路径: {ascii_path}")
        return ascii_path, temp_dir

    def _convert_pdf_to_docx(self, input_path: str, output_path: str) -> bool:
        try:
            from pdf2docx import Converter
            logger.info(f"使用 pdf2docx 转换 PDF -> DOCX: {input_path}")
            cv = Converter(input_path)
            cv.convert(output_path, start=0, end=None)
            cv.close()
            logger.info(f"pdf2docx 转换成功: {output_path}")
            return True
        except ImportError:
            raise ConversionError(
                "pdf2docx 库未安装，请运行以下命令安装：\n"
                "pip install pdf2docx"
            )
        except Exception as e:
            logger.error(f"pdf2docx 转换失败: {e}")
            raise ConversionError(f"PDF转DOCX失败: {str(e)}")

    def _apply_image_quality(self, image_path: str, output_format: str, quality: str) -> None:
        try:
            with Image.open(image_path) as img:
                if output_format in ['jpg', 'jpeg'] and img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                quality_value = self.QUALITY_MAP.get(quality, {})
                save_kwargs = {}
                if output_format in ['jpg', 'jpeg']:
                    save_kwargs['quality'] = quality_value.get('jpg', 100)
                    save_kwargs['optimize'] = True
                    temp_path = image_path + '.tmp'
                    img.save(temp_path, 'JPEG', **save_kwargs)
                    shutil.move(temp_path, image_path)
                    logger.debug(f"应用 JPEG 质量: {save_kwargs['quality']}")
                elif output_format == 'png':
                    compression = quality_value.get('png', 0)
                    save_kwargs['compress_level'] = compression
                    temp_path = image_path + '.tmp'
                    img.save(temp_path, 'PNG', **save_kwargs)
                    shutil.move(temp_path, image_path)
                    logger.debug(f"应用 PNG 压缩级别: {compression}")
        except Exception as e:
            logger.warning(f"应用图片质量失败: {e}")

    def _convert_pdf_to_images_with_fitz(
        self,
        input_path: str,
        output_format: str,
        output_dir: str,
        quality: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """
        使用 PyMuPDF (fitz) 将 PDF 的每一页转换为图片，直接输出到指定目录
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ConversionError(
                "PyMuPDF (fitz) 库未安装，请运行以下命令安装：\n"
                "pip install PyMuPDF"
            )

        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)

            # 打开 PDF 文档
            doc = fitz.open(input_path)
            total_pages = len(doc)

            if total_pages == 0:
                raise ConversionError("PDF 文件为空（没有页面）")

            logger.info(f"PDF 共有 {total_pages} 页，开始转换为 {output_format}")

            # 确定输出扩展名
            ext_map = {
                'png': 'png',
                'jpg': 'jpg',
                'jpeg': 'jpg',
                'bmp': 'bmp',
            }
            actual_ext = ext_map.get(output_format.lower(), 'png')

            # 获取质量参数
            quality_value = self.QUALITY_MAP.get(quality, {})
            jpg_quality = quality_value.get('jpg', 100)

            # 获取输出文件名（不含扩展名）
            base_name = os.path.splitext(os.path.basename(input_path))[0]

            for page_num in range(total_pages):
                if progress_callback:
                    progress = ((page_num + 1) / total_pages) * 100
                    progress_callback(progress)

                page = doc[page_num]
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)

                if actual_ext == 'png':
                    img_path = os.path.join(output_dir, f"{base_name}_{page_num + 1}.png")
                    pix.save(img_path, 'png')
                elif actual_ext == 'jpg':
                    img_path = os.path.join(output_dir, f"{base_name}_{page_num + 1}.jpg")
                    pix.save(img_path, 'jpeg', jpg_quality=jpg_quality)
                elif actual_ext == 'bmp':
                    img_path = os.path.join(output_dir, f"{base_name}_{page_num + 1}.bmp")
                    pix.save(img_path, 'bmp')
                else:
                    img_path = os.path.join(output_dir, f"{base_name}_{page_num + 1}.png")
                    pix.save(img_path, 'png')

            doc.close()

            # 如果只有一张图片，返回单张图片路径
            if total_pages == 1:
                return os.path.join(output_dir, f"{base_name}_1.{actual_ext}")

            # 多张图片：打包为 ZIP
            zip_path = os.path.join(output_dir, f"{base_name}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for idx in range(1, total_pages + 1):
                    img_path = os.path.join(output_dir, f"{base_name}_{idx}.{actual_ext}")
                    if os.path.exists(img_path):
                        # 在 ZIP 中重命名为 页码.扩展名
                        arcname = f"{idx}.{actual_ext}"
                        zf.write(img_path, arcname)
                        # 删除原始图片文件
                        os.remove(img_path)

            logger.info(f"转换成功（多页，共 {total_pages} 张图片，已打包为ZIP）: {zip_path}")
            return zip_path

        except Exception as e:
            logger.error(f"PyMuPDF 转换失败: {e}")
            raise ConversionError(f"PDF转图片失败: {str(e)}")

    def convert(
        self,
        input_path: str,
        output_format: str,
        output_dir: str,
        quality: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """
        转换文件，直接输出到指定目录

        Args:
            input_path: 输入文件路径
            output_format: 输出格式
            output_dir: 输出目录
            quality: 压缩质量（仅图片格式）
            progress_callback: 进度回调函数

        Returns:
            输出文件路径

        Raises:
            ConversionError: 转换失败
            ConversionTimeoutError: 转换超时
        """
        if not os.path.exists(input_path):
            raise ConversionError("文件不存在")

        if file_utils.is_empty_file(input_path):
            raise ConversionError("文件为空，无法转换")

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        input_ext = file_utils.get_file_extension(input_path)
        output_ext = output_format.lower()

        logger.info(f"开始转换: {input_path} -> {output_format}")

        if not self._is_conversion_supported(input_ext, output_ext):
            if input_ext == 'wps':
                raise ConversionError("暂不支持此格式转换")
            raise ConversionError(
                f"暂不支持将 {input_ext.upper()} 转换为 {output_ext.upper()}\n"
                f"支持的方向：{', '.join(sorted(self.SUPPORTED_CONVERSIONS.get(input_ext, set())))}"
            )

        if input_ext == output_ext:
            logger.info("同格式转换，执行文件复制")
            return self._copy_file(input_path, output_format, output_dir)

        # 特殊处理 PDF -> DOCX
        if input_ext == 'pdf' and output_ext == 'docx':
            output_filename = file_utils.get_output_filename(input_path, output_format)
            output_path = os.path.join(output_dir, output_filename)
            if progress_callback:
                progress_callback(10.0)
            self._convert_pdf_to_docx(input_path, output_path)
            if progress_callback:
                progress_callback(100.0)
            logger.info(f"转换成功: {output_path}")
            return output_path

        # 图片格式输出 - PDF直接使用PyMuPDF
        if output_ext in ['png', 'jpg', 'jpeg', 'bmp']:
            if input_ext == 'pdf':
                return self._convert_pdf_to_images_with_fitz(
                    input_path, output_format, output_dir, quality, progress_callback
                )
            else:
                # 非PDF文档转图片：先转PDF再转图片
                return self._convert_document_to_images_with_libreoffice(
                    input_path, output_format, output_dir, quality, progress_callback
                )

        # 其他格式：使用 LibreOffice 转换
        return self._convert_with_libreoffice(
            input_path, output_format, output_dir, progress_callback
        )

    def _copy_file(self, input_path: str, output_format: str, output_dir: str) -> str:
        """复制文件（同格式转换）"""
        output_filename = file_utils.get_output_filename(input_path, output_format)
        output_path = os.path.join(output_dir, output_filename)
        if file_utils.copy_file(input_path, output_path):
            logger.info(f"文件复制成功: {output_path}")
            return output_path
        raise ConversionError("文件复制失败")

    def _convert_document_to_images_with_libreoffice(
        self,
        input_path: str,
        output_format: str,
        output_dir: str,
        quality: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """
        使用 LibreOffice 将非 PDF 文档先转换为 PDF，再使用 PyMuPDF 转换为图片
        """
        # 创建临时目录存放中间PDF
        temp_dir = tempfile.mkdtemp(prefix='convert_temp_')

        try:
            # 第一步：使用 LibreOffice 将文档转换为 PDF
            logger.info(f"步骤1: 使用 LibreOffice 将文档转换为 PDF")
            pdf_path = self._convert_with_libreoffice(input_path, 'pdf', temp_dir, progress_callback)

            if not pdf_path or not os.path.exists(pdf_path):
                raise ConversionError("转换为 PDF 失败")

            logger.info(f"步骤1完成: PDF 生成成功")

            # 第二步：使用 PyMuPDF 将 PDF 转换为多张图片
            logger.info(f"步骤2: 使用 PyMuPDF 将 PDF 转换为图片")
            result = self._convert_pdf_to_images_with_fitz(
                pdf_path, output_format, output_dir, quality, progress_callback
            )

            return result

        finally:
            # 清理临时目录
            try:
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")

    def _convert_with_libreoffice(
        self,
        input_path: str,
        output_format: str,
        output_dir: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """使用LibreOffice转换文件"""
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 处理中文路径问题：复制输入文件到 ASCII 临时路径
        ascii_input_path, ascii_temp_dir = self._get_ascii_temp_path(input_path)

        try:
            cmd = [
                self._libreoffice_path,
                '--headless',
                '--convert-to',
                self._get_libreoffice_format(output_format),
                '--outdir',
                output_dir,
                ascii_input_path
            ]

            logger.debug(f"执行命令: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            start_time = time.time()
            while process.poll() is None:
                elapsed = time.time() - start_time
                if elapsed > self.timeout:
                    process.kill()
                    process.wait()
                    raise ConversionTimeoutError(f"转换超时（{self.timeout}秒）")
                if progress_callback:
                    progress = min(100.0, (elapsed / self.timeout) * 100)
                    progress_callback(progress)
                time.sleep(0.5)

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                logger.error(f"LibreOffice转换失败: {stderr}")
                raise ConversionError(f"转换失败: {self._parse_error(stderr)}")

            output_ext = output_format.lower()
            output_filename = file_utils.get_output_filename(input_path, output_format)
            output_path = os.path.join(output_dir, output_filename)

            if not os.path.exists(output_path):
                ascii_basename = os.path.splitext(os.path.basename(ascii_input_path))[0]
                ascii_output_filename = f"{ascii_basename}.{output_ext}"
                ascii_output_path = os.path.join(output_dir, ascii_output_filename)
                if os.path.exists(ascii_output_path):
                    shutil.move(ascii_output_path, output_path)
                else:
                    for file in os.listdir(output_dir):
                        if file.lower().endswith(f'.{output_ext}'):
                            found_path = os.path.join(output_dir, file)
                            if found_path != output_path:
                                shutil.move(found_path, output_path)
                            break
                    else:
                        raise ConversionError("未找到转换后的文件")

            logger.info(f"LibreOffice转换成功: {output_path}")
            return output_path

        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise ConversionTimeoutError(f"转换超时（{self.timeout}秒）")
        except Exception as e:
            logger.error(f"转换异常: {e}")
            raise ConversionError(f"转换失败: {str(e)}")
        finally:
            try:
                if ascii_temp_dir and os.path.exists(ascii_temp_dir):
                    shutil.rmtree(ascii_temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"清理 ASCII 临时目录失败: {e}")

    def _get_libreoffice_format(self, output_format: str) -> str:
        format_map = {
            'pdf': 'pdf',
            'docx': 'docx',
            'doc': 'doc',
            'xlsx': 'xlsx',
            'xls': 'xls',
            'pptx': 'pptx',
            'ppt': 'ppt',
            'txt': 'txt',
            'rtf': 'rtf',
            'html': 'html',
            'png': 'png',
            'jpg': 'jpg',
            'jpeg': 'jpg',
            'bmp': 'bmp',
            'csv': 'csv',
            'md': 'md',
            'wps': 'wps',
        }
        return format_map.get(output_format.lower(), output_format.lower())

    def _parse_error(self, error_output: str) -> str:
        error_lower = error_output.lower()
        if 'filter' in error_lower or 'no export filter' in error_lower:
            return "格式不兼容，请检查文件格式"
        elif 'corrupt' in error_lower or 'damaged' in error_lower:
            return "文件已损坏，无法读取"
        elif 'permission' in error_lower:
            return "文件权限不足"
        else:
            return "转换失败，请检查文件是否有效"


def get_converter():
    return Converter()