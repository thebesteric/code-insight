import ast
import os
from abc import ABC, abstractmethod
from typing import Optional

from libs.core.code.code_models import ModuleInfo, FunctionInfo, ClassInfo
from libs.utils.log_helper import LogHelper

logger = LogHelper.get_logger()


class BaseCodeParser(ast.NodeVisitor, ABC):
    """
    抽象的代码解析器类，用于解析代码文件并构建模块信息模型。
    """

    @abstractmethod
    def __init__(self, file_suffixes: list[str], ignore_dirs: list[str]):
        """
        初始化解析器。

        :param file_suffixes: 支持的文件后缀列表
        :param ignore_dirs: 忽略的目录列表
        """
        self.file_suffixes = file_suffixes
        self.ignore_dirs = ignore_dirs
        self.module_info = ModuleInfo.model_construct()
        self.current_class: Optional[ClassInfo] = None
        self.current_function: Optional[FunctionInfo] = None

    @staticmethod
    @abstractmethod
    def parse_file(project_dir: str, file_path: str) -> ModuleInfo:
        """
        解析给定的文件路径。

        :param project_dir: 项目路径
        :param file_path: 文件路径
        :return: 解析结果
        """
        raise NotImplementedError()

    @staticmethod
    def read_file(file_path: str):
        """
        读取文件内容。

        :param file_path: 文件路径
        :return: 文件内容
        """
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()
        return source_code

    def parse_directory(self, dir_path: str) -> list[ModuleInfo]:
        """
        解析给定目录下的所有文件。

        :param dir_path: 目录路径
        :return: 解析结果列表
        """
        module_infos = []
        for root, dirs, files in os.walk(dir_path):
            # 忽略指定目录
            dirs[:] = [d for d in dirs if d not in self.ignore_dirs]

            for file in files:
                if any(file.endswith(suffix) for suffix in self.file_suffixes):
                    file_path = os.path.join(root, file)
                    logger.info(f"正在解析文件：{file_path}")
                    module_info = self.parse_file(dir_path, file_path)
                    module_infos.append(module_info)

        if not module_infos:
            logger.warning(f"未找到任何文件，请检查文件后缀 {self.file_suffixes} 是否正确，或忽略的目录 {self.ignore_dirs} 是否包含要解析的文件")

        return module_infos
