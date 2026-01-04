import os
import subprocess
from pathlib import Path

import dotenv
import pyrootutils

from libs.config.app_config import AppConfig
from libs.config.app_module import app_injector
from libs.core.code.code_models import ProjectInfo
from libs.core.code.impl.python_code_parser import PythonCodeParser
from libs.core.graph.impl.neo4j_graph_converter import Neo4JGraphConverter
from libs.core.persistent.impl.mysql_persistent_saver import MySQLPersistentSaver
from libs.utils.log_helper import LogHelper

_ = dotenv.load_dotenv()

logger = LogHelper.get_logger()
app_config = app_injector.get(AppConfig)

class ProjectLoader:
    """
    项目加载器
    """

    def __init__(self, project_url_or_path: str, *, branch: str = None):
        # 获取绝对路径，保证在项目根目录下
        self.project_cache_dir = Path(pyrootutils.find_root()) / app_config.PROJECT_CACHE_DIR
        # 项目地址
        self.project_url_or_path = project_url_or_path
        # 项目类型
        self.project_type = "git" if self.project_url_or_path.startswith("git@") or self.project_url_or_path.startswith("https://") else "local"
        # 项目名称
        self.project_name = Path(self.project_url_or_path).name.split(".")[0]
        # 项目存储路径
        self.project_storage_path = self.project_cache_dir / self.project_name if self.project_type == "git" else self.project_url_or_path
        # 项目分支
        self.branch = branch

    def load(self, *, rebuild: bool = False):
        """
        加载项目
        :param rebuild: 是否重建项目，默认 False
        :return:
        """
        logger.info(f"Ready to load project from {self.project_type} repository: {self.project_url_or_path}")
        # 加载项目
        if self.project_type == "git":
            self._load_from_git()

        # 解析项目代码
        module_infos = PythonCodeParser().parse_directory(self.project_storage_path)

        # 保存项目信息和模块信息
        MySQLPersistentSaver(rebuild).persistence(
            ProjectInfo(
                name=self.project_name,
                storage_path=self.project_storage_path,
                repo_url=self.project_url_or_path if self.project_type == "git" else None
            ),
            module_infos
        )

        # 创建图谱
        Neo4JGraphConverter(rebuild).convert(module_infos)

    def _load_from_git(self):
        """
        从 Git 仓库加载项目
        :return:
        """
        os.makedirs(self.project_cache_dir, exist_ok=True)

        # 如果目录已存在，先删除
        if self.project_storage_path.exists():
            logger.warning(f"Project path {self.project_storage_path} already exists, skip cloning")
            return

        if self.branch:
            cmd = ["git", "clone", "--progress", "-b", self.branch, self.project_url_or_path, self.project_storage_path]
        else:
            cmd = ["git", "clone", "--progress", self.project_url_or_path, self.project_storage_path]

        try:
            # 启动子进程，捕获 stdout 和 stderr
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 将 stderr 合并到 stdout 一起处理
                text=True,  # 以文本模式读取输出（避免二进制处理）
                bufsize=0,  # 无缓冲，立即输出
                universal_newlines=True,
                encoding="utf-8",
            )

            # 实时读取并打印输出
            for line in process.stdout:
                stripped_line_output = line.strip()
                if stripped_line_output:
                    logger.info(stripped_line_output)

            # 等待进程结束并获取返回码
            return_code = process.wait()
            if return_code == 0:
                logger.info(f"Successfully cloned repository to {self.project_storage_path}")

            # 返回非零状态码时，抛出异常
            raise Exception(f"Error: git clone failed with return code {return_code}")

        except Exception as e:
            # 捕获异常并重新抛出
            raise Exception(f"Error during git clone: {str(e)}")


if __name__ == '__main__':
    loader = ProjectLoader("/Users/wangweijun/PycharmProjects/iotcoderv2")
    loader.load(rebuild=False)
