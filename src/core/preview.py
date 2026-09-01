"""
预览模块 - 使用 PyMuPDF 直接渲染 QImage（纯内存操作，无临时文件）
"""
import os
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple

from PIL import Image
from PyQt6.QtGui import QImage, QPixmap

from ..utils.logger import get_logger
from .file_utils import file_utils

logger = get_logger()


class PreviewGenerator:
    """预览缩略图生成器 - 使用 PyMuPDF 直接渲染 QImage"""

    # 预览参数
    PREVIEW_WIDTH = 400
    PREVIEW_MAX_HEIGHT = 600
    MAX_PREVIEW_PAGES = 5

    def __init__(self):
        self._converter = None
        self._fitz_available = self._check_fitz()

    def _check_fitz(self) -> bool:
        """检查 PyMuPDF 是否可用"""
        try:
            import fitz
            return True
        except ImportError:
            logger.warning("PyMuPDF (fitz) 未安装，预览功能将受限")
            return False

    def _get_converter(self):
        """延迟加载转换器"""
        if self._converter is None:
            from .converter import get_converter
            self._converter = get_converter()
        return self._converter

    def generate_preview_qpixmaps(self, file_path: str) -> List[QPixmap]:
        """
        生成文件预览 QPixmap 列表（纯内存操作）

        Args:
            file_path: 文件路径

        Returns:
            QPixmap 列表，失败返回空列表
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"文件不存在: {file_path}")
                return []

            ext = file_utils.get_file_extension(file_path)

            # 如果是图片，直接生成 QPixmap
            if file_utils.is_image_format(ext):
                result = self._preview_image_qpixmap(file_path)
                return [result] if result else []

            # 检查文件大小
            try:
                file_size = os.path.getsize(file_path)
                if file_size > 50 * 1024 * 1024:  # 50MB
                    logger.warning(f"文件过大 ({file_size / 1024 / 1024:.1f}MB)，跳过预览生成")
                    return []
            except Exception:
                pass

            # 使用 PyMuPDF 直接渲染
            return self._preview_document_qpixmaps(file_path)

        except Exception as e:
            logger.error(f"生成预览失败: {e}")
            return []

    def _preview_image_qpixmap(self, file_path: str) -> Optional[QPixmap]:
        """生成图片预览 QPixmap"""
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                ratio = self.PREVIEW_WIDTH / width
                new_height = int(height * ratio)

                if new_height > self.PREVIEW_MAX_HEIGHT:
                    ratio = self.PREVIEW_MAX_HEIGHT / height
                    new_width = int(width * ratio)
                    new_height = self.PREVIEW_MAX_HEIGHT
                else:
                    new_width = self.PREVIEW_WIDTH

                img.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)

                # 转换为 QImage
                if img.mode == 'RGB':
                    data = img.tobytes('raw', 'RGB')
                    qimage = QImage(data, img.width, img.height, QImage.Format.Format_RGB888)
                elif img.mode == 'RGBA':
                    data = img.tobytes('raw', 'RGBA')
                    qimage = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
                else:
                    img = img.convert('RGB')
                    data = img.tobytes('raw', 'RGB')
                    qimage = QImage(data, img.width, img.height, QImage.Format.Format_RGB888)

                return QPixmap.fromImage(qimage)

        except Exception as e:
            logger.error(f"生成图片预览失败: {e}")
            return None

    def _preview_document_qpixmaps(self, file_path: str) -> List[QPixmap]:
        """
        使用 PyMuPDF 直接渲染文档为 QPixmap
        先转换为 PDF，再用 PyMuPDF 渲染
        """
        try:
            if not self._fitz_available:
                logger.error("PyMuPDF 不可用，无法生成预览")
                return []

            import fitz

            # 先转换为 PDF
            converter = self._get_converter()
            pdf_path = converter.convert(file_path, 'pdf')

            if not pdf_path or not os.path.exists(pdf_path):
                logger.error("转换为 PDF 失败")
                return []

            try:
                # 使用 PyMuPDF 打开 PDF
                doc = fitz.open(pdf_path)
                total_pages = len(doc)

                if total_pages == 0:
                    logger.warning("PDF 文件为空")
                    return []

                # 限制预览页数
                pages_to_render = min(total_pages, self.MAX_PREVIEW_PAGES)
                if total_pages > self.MAX_PREVIEW_PAGES:
                    logger.info(f"文档共 {total_pages} 页，仅显示前 {self.MAX_PREVIEW_PAGES} 页预览")

                pixmaps = []

                for page_num in range(pages_to_render):
                    page = doc[page_num]

                    # 计算缩放比例
                    rect = page.rect
                    page_width = rect.width
                    page_height = rect.height

                    # 按宽度缩放
                    scale_x = self.PREVIEW_WIDTH / page_width
                    scale_y = self.PREVIEW_MAX_HEIGHT / page_height
                    scale = min(scale_x, scale_y, 2.0)  # 最大 2x 缩放

                    if scale < 0.1:
                        scale = 0.1

                    mat = fitz.Matrix(scale, scale)
                    pix = page.get_pixmap(matrix=mat)

                    # 转换为 QImage
                    if pix.n == 4:  # RGBA
                        qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGBA8888)
                    elif pix.n == 3:  # RGB
                        qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                    else:
                        # 其他格式，转换为 RGB
                        rgb_pix = fitz.Pixmap(fitz.csRGB, pix)
                        qimage = QImage(rgb_pix.samples, rgb_pix.width, rgb_pix.height, rgb_pix.stride, QImage.Format.Format_RGB888)
                        rgb_pix = None

                    qpixmap = QPixmap.fromImage(qimage)
                    if not qpixmap.isNull():
                        pixmaps.append(qpixmap)

                doc.close()

                if pixmaps:
                    logger.info(f"生成文档预览成功，共 {len(pixmaps)} 页")
                else:
                    logger.warning("生成文档预览失败（无有效页面）")

                # 清理临时 PDF
                try:
                    os.remove(pdf_path)
                    pdf_dir = os.path.dirname(pdf_path)
                    if pdf_dir and 'converter_' in pdf_dir:
                        import shutil
                        shutil.rmtree(pdf_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {e}")

                return pixmaps

            except Exception as e:
                logger.error(f"PyMuPDF 渲染失败: {e}")
                # 清理临时 PDF
                try:
                    if pdf_path and os.path.exists(pdf_path):
                        os.remove(pdf_path)
                except Exception:
                    pass
                return []

        except Exception as e:
            logger.error(f"生成文档预览失败: {e}")
            return []

    # 保留旧接口兼容性
    def generate_all_previews(self, file_path: str) -> List[Path]:
        """兼容旧接口，返回空列表（新接口使用 generate_preview_qpixmaps）"""
        logger.warning("generate_all_previews 已废弃，请使用 generate_preview_qpixmaps")
        return []


def get_preview_generator():
    """获取预览生成器实例"""
    return PreviewGenerator()