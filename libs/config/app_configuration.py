import os
from enum import Enum

import dotenv

from libs.utils.log_helper import LogHelper

logger = LogHelper.get_logger()

class AppEnvironment(str, Enum):
    DEVELOPMENT = "dev"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "prod"


class AppConfiguration:
    def __init__(self, env_file_path: str = ".env"):
        """
        初始化应用配置，从环境变量加载配置。
        :param env_file_path: 环境变量文件路径，默认值为 ".env"
        """
        # 加载环境变量文件
        dotenv.load_dotenv(dotenv_path=env_file_path)

        # 项目环境
        self.APP_ENV = AppEnvironment(os.getenv("APP_ENV", AppEnvironment.DEVELOPMENT.value))

        # 项目目录
        self.PROJECT_CACHE_DIR = os.getenv("PROJECT_CACHE_DIR", "./project_cache")

        # Neo4j 配置
        self.NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
        self.NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "P@ssw0rd")
        self.NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

        # MySQL 配置
        self.MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
        self.MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
        self.MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "code_insight")
        self.MYSQL_USER = os.getenv("MYSQL_USER", "root")
        self.MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")


# 项目应用配置实例
app_configuration = AppConfiguration(env_file_path=".env")

logger.info(f"App is running in {app_configuration.APP_ENV.name} environment.")
