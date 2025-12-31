import json
from enum import Enum

from sqlalchemy import Column, Integer, String, Text, func, ForeignKey, DateTime, JSON, Enum as SQLEnum, create_engine, text, Boolean
from sqlalchemy.orm.decl_api import declarative_base

from libs.config.app_config import AppConfig
from libs.config.app_initializer import AppInitializer
from libs.config.app_module import app_injector
from libs.core.code.code_models import ModuleInfo, ClassInfo, FunctionInfo, ProjectInfo
from libs.utils.log_helper import LogHelper

logger = LogHelper.get_logger()

app_config = app_injector.get(AppConfig)
app_initializer = app_injector.get(AppInitializer)

Base = declarative_base()


class BaseEntityModel(Base):
    """
    基础模型类
    """

    # 标记为抽象类，不会生成实际数据库表
    __abstract__ = True

    # 属性
    created_at = Column(DateTime, default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")


class FunctionType(str, Enum):
    NORMAL_FUNC = "normal"
    STATIC_FUNC = "static"
    CLASS_FUNC = "class"


class ProjectInfoEntity(BaseEntityModel):
    __tablename__ = "project_info"

    # 属性
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    name = Column(String(64), nullable=False, unique=True, comment="项目名")
    storage_path = Column(String(256), nullable=False, comment="项目存储路径")
    repo_url = Column(String(256), nullable=True, comment="仓库地址")

    @staticmethod
    def from_project_info(project_info: ProjectInfo) -> "ProjectInfoEntity":
        """
        从 ProjectInfo 对象初始化
        :param project_info: ProjectInfo 对象
        :return:
        """
        project_info_entity = ProjectInfoEntity()
        project_info_entity.name = project_info.name
        project_info_entity.storage_path = project_info.storage_path
        project_info_entity.repo_url = project_info.repo_url
        return project_info_entity


class ModuleInfoEntity(BaseEntityModel):
    __tablename__ = "module_info"

    # 属性
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    file_path = Column(String(256), nullable=False, comment="模块文件路径")
    module_name = Column(String(128), nullable=False, comment="模块名称")
    docs = Column(Text, nullable=True, comment="模块文档")
    constants = Column(JSON, nullable=True, comment="模块级常量")
    variables = Column(JSON, nullable=True, comment="模块级变量")
    normal_imports = Column(JSON, nullable=True, comment="普通导入")
    from_imports = Column(JSON, nullable=True, comment="from...import 导入")

    # 外键
    project_id = Column(Integer, ForeignKey("project_info.id", ondelete="CASCADE"), comment="项目 ID")

    @staticmethod
    def from_module_info(module_info: ModuleInfo, *, project_id: int) -> "ModuleInfoEntity":
        """
        从 ModuleInfo 对象初始化
        :param module_info: ModuleInfo 对象
        :param project_id: 项目 ID
        :return:
        """
        module_info_entity = ModuleInfoEntity()
        module_info_entity.file_path = module_info.file_path
        module_info_entity.module_name = module_info.module_name
        module_info_entity.docs = module_info.docs
        module_info_entity.constants = json.dumps(module_info.constants, ensure_ascii=False)
        module_info_entity.variables = json.dumps([variable.model_dump() for variable in module_info.variables], ensure_ascii=False)
        module_info_entity.normal_imports = json.dumps([import_name.model_dump() for import_name in module_info.imports.get("normal",  [])], ensure_ascii=False)
        module_info_entity.from_imports = json.dumps([import_from.model_dump() for import_from in module_info.imports.get("from",  [])], ensure_ascii=False)
        module_info_entity.project_id = project_id
        return module_info_entity


class ClassInfoEntity(BaseEntityModel):
    __tablename__ = "class_info"

    # 属性
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    name = Column(String(256), nullable=False, comment="类名")
    docs = Column(Text, nullable=True, comment="类文档")
    bases = Column(JSON, nullable=True, comment="基类列表")
    constants = Column(JSON, nullable=True, comment="类常量")
    variables = Column(JSON, nullable=True, comment="类变量")

    # 外键
    module_id = Column(Integer, ForeignKey("module_info.id", ondelete="CASCADE"), comment="模块 ID")
    parent_class_id = Column(Integer, ForeignKey("class_info.id", ondelete="CASCADE"), nullable=True, comment="类 ID")

    @staticmethod
    def from_class_info(class_info: ClassInfo, *, module_id: int = None, parent_class_id: int = None) -> "ClassInfoEntity":
        """
        从 ClassInfo 创建 ClassInfoEntity 对象
        :param class_info: ClassInfo 对象
        :param parent_class_id: 所属父类 ID
        :param module_id: 所属模块 ID
        :return: ClassInfoEntity 对象
        """
        class_info_entity = ClassInfoEntity()
        class_info_entity.name = class_info.name
        class_info_entity.docs = class_info.docs
        class_info_entity.bases = json.dumps(class_info.bases, ensure_ascii=False)
        class_info_entity.constants = json.dumps(class_info.class_constants, ensure_ascii=False)
        class_info_entity.variables = json.dumps([variable.model_dump() for variable in class_info.class_variables], ensure_ascii=False)
        class_info_entity.parent_class_id = parent_class_id
        class_info_entity.module_id = module_id
        return class_info_entity


class FunctionInfoEntity(BaseEntityModel):
    __tablename__ = "function_info"

    # 属性
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    name = Column(String(256), nullable=False, comment="函数名")
    is_async = Column(Boolean, default=False, nullable=False, comment="是否异步函数")
    func_type = Column(String(32), default=FunctionType.NORMAL_FUNC.value, nullable=False, comment="函数类型")
    variables = Column(JSON, nullable=True, comment="函数参数")
    args = Column(JSON, nullable=True, comment="函数参数")
    decorators = Column(JSON, nullable=True, comment="函数装饰器列表")
    body = Column(Text, nullable=False, comment="函数体")
    returns = Column(String(256), nullable=True, comment="返回值类型")
    docs = Column(Text, nullable=True, comment="函数文档")

    # 外键
    module_id = Column(Integer, ForeignKey("module_info.id", ondelete="CASCADE"), nullable=True, comment="模块 ID")
    class_id = Column(Integer, ForeignKey("class_info.id", ondelete="CASCADE"), nullable=True, comment="类 ID")

    @staticmethod
    def from_function_info(func_info: FunctionInfo, *, class_id: int = None, module_id: int = None) -> "FunctionInfoEntity":
        """
        从 FunctionInfo 创建 FunctionInfoEntity 对象
        :param func_info: FunctionInfo 对象
        :param class_id: 所属类 ID
        :param module_id: 所属模块 ID
        :return: FunctionInfoEntity 对象
        """
        function_info_entity = FunctionInfoEntity()
        function_info_entity.name = func_info.name
        function_info_entity.variables = json.dumps([variable.model_dump() for variable in func_info.variables], ensure_ascii=False)
        function_info_entity.args = func_info.args.model_dump()
        function_info_entity.is_async = func_info.is_async
        function_info_entity.func_type = func_info.type.value
        function_info_entity.decorators = json.dumps(func_info.decorators, ensure_ascii=False)
        function_info_entity.body = func_info.body
        function_info_entity.returns = func_info.returns
        function_info_entity.docs = func_info.docs
        function_info_entity.class_id = class_id
        function_info_entity.module_id = module_id
        return function_info_entity


@app_initializer.task
def _init_db():
    """
    初始化数据库，创建数据库和表。
    :return:
    """
    user = app_config.MYSQL_USER
    password = app_config.MYSQL_PASSWORD
    host = app_config.MYSQL_HOST
    port = app_config.MYSQL_PORT
    database = app_config.MYSQL_DATABASE

    # 连接字符串
    connect_uri = f"mysql+pymysql://{user}:{password}@{host}:{port}"

    # 检查数据库是否存在，不存在则创建
    with create_engine(connect_uri).connect() as conn:
        # 创建数据库（如果不存在）
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {database} CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"))

    # 创建表
    engine = create_engine(f"{connect_uri}/{database}")
    Base.metadata.create_all(engine)
    logger.info(f"Database {database} initialized successfully.")
