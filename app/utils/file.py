import os
import re
from typing import List, Optional


class FileUtils:
    """文件工具类，提供文件名和路径相关的操作"""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名，移除不合法字符

        Args:
            filename: 原始文件名

        Returns:
            清理后的文件名
        """
        # 替换Windows不允许的文件名字符
        invalid_chars = r'[\\/:*?"<>|]'
        sanitized = re.sub(invalid_chars, "_", filename)

        # 移除前后空白字符
        sanitized = sanitized.strip()

        # 如果文件名为空，使用默认名称
        if not sanitized:
            sanitized = "未命名"

        return sanitized

    @staticmethod
    def ensure_dir_exists(dir_path: str) -> None:
        """确保目录存在，如果不存在则创建

        Args:
            dir_path: 目录路径
        """
        os.makedirs(dir_path, exist_ok=True)

    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """获取文件扩展名

        Args:
            file_path: 文件路径

        Returns:
            文件扩展名（不包含点号）
        """
        return os.path.splitext(file_path)[1][1:].lower()

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """获取文件大小（字节）

        Args:
            file_path: 文件路径

        Returns:
            文件大小（字节）
        """
        return os.path.getsize(file_path)

    @staticmethod
    def get_file_size_human_readable(file_path: str) -> str:
        """获取人类可读的文件大小

        Args:
            file_path: 文件路径

        Returns:
            人类可读的文件大小（如：1.2 MB）
        """
        size = FileUtils.get_file_size(file_path)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0 or unit == "TB":
                break
            size /= 1024.0
        return f"{size:.2f} {unit}"

    @staticmethod
    def list_files(dir_path: str, extensions: List[str] = None) -> List[str]:
        """列出目录中的文件

        Args:
            dir_path: 目录路径
            extensions: 文件扩展名列表，如果为None则列出所有文件

        Returns:
            文件路径列表
        """
        files = []
        for file in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file)
            if os.path.isfile(file_path):
                if (
                    extensions is None
                    or FileUtils.get_file_extension(file_path) in extensions
                ):
                    files.append(file_path)
        return files

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """删除文件

        Args:
            file_path: 文件路径

        Returns:
            是否删除成功
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"<== 删除文件失败: {file_path}, 错误: {str(e)}")
            return False

    @staticmethod
    def read_text_file(file_path: str, encoding: str = "utf-8") -> Optional[str]:
        """读取文本文件

        Args:
            file_path: 文件路径
            encoding: 文件编码

        Returns:
            文件内容，失败返回None
        """
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except Exception as e:
            print(f"<== 读取文件失败: {file_path}, 错误: {str(e)}")
            return None

    @staticmethod
    def write_text_file(file_path: str, content: str, encoding: str = "utf-8") -> bool:
        """写入文本文件

        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 文件编码

        Returns:
            是否写入成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "w", encoding=encoding) as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"<== 写入文件失败: {file_path}, 错误: {str(e)}")
            return False

    @staticmethod
    def append_text_file(file_path: str, content: str, encoding: str = "utf-8") -> bool:
        """追加文本文件

        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 文件编码

        Returns:
            是否追加成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "a", encoding=encoding) as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"<== 追加文件失败: {file_path}, 错误: {str(e)}")
            return False
