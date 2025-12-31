from urllib.parse import urlencode

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from libs.config.app_configuration import app_configuration
from libs.core.code.code_models import ClassInfo, FunctionInfo, ModuleInfo, ProjectInfo
from libs.core.persistent.base_persistent_saver import BasePersistentSaver
from libs.core.persistent.persistent_models import ProjectInfoEntity, ModuleInfoEntity, ClassInfoEntity, FunctionInfoEntity
from libs.utils.log_helper import LogHelper

logger = LogHelper.get_logger()


class MySQLPersistentSaver(BasePersistentSaver):

    def __init__(self, rebuild: bool = False, **kwargs):
        super().__init__(rebuild, **kwargs)
        user = app_configuration.MYSQL_USER
        password = app_configuration.MYSQL_PASSWORD
        host = app_configuration.MYSQL_HOST
        port = app_configuration.MYSQL_PORT
        database = app_configuration.MYSQL_DATABASE
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?{urlencode(kwargs)}"
        self.engine = create_engine(url)
        self.session = Session(self.engine)

    def save_project_info(self, project_info: ProjectInfo) -> ProjectInfoEntity:
        """
        保存项目信息
        :param project_info: 项目信息
        :return: 项目信息实体
        """
        project_info_entity = ProjectInfoEntity.from_project_info(project_info)
        self.session.add(project_info_entity)
        self.session.commit()
        return project_info_entity

    def save_module_info(self, module_info: ModuleInfo, project_id: int) -> ModuleInfoEntity:
        """
        保存模块信息
        :param module_info: 模块信息
        :param project_id: 项目 ID
        """
        module_info_entity = ModuleInfoEntity.from_module_info(module_info, project_id=project_id)
        self.session.add(module_info_entity)
        self.session.commit()
        return module_info_entity

    def save_class_info(self, class_info: ClassInfo, module_id: int, parent_class_id: int = None) -> ClassInfoEntity:
        """
        保存类信息
        :param class_info: 类信息
        :param module_id: 模块 ID
        :param parent_class_id: 父类 ID
        """
        class_info_entity = ClassInfoEntity.from_class_info(class_info, module_id=module_id, parent_class_id=parent_class_id)
        self.session.add(class_info_entity)
        self.session.commit()

        # 遍历类中的类方法信息（含实例方法、静态方法、类方法）
        methods = class_info.instance_methods + class_info.class_methods + class_info.static_methods
        for method in methods:
            # 保存类方法信息
            self.save_function_info(method, module_id=module_id, class_id=class_info_entity.id)

        for nested_class in class_info.nested_classes:
            # 递归：保存嵌套类信息
            self.save_class_info(nested_class, module_id=module_id, parent_class_id=class_info_entity.id)

        return class_info_entity

    def save_function_info(self, function_info: FunctionInfo, module_id: int = None, class_id: int = None) -> FunctionInfoEntity:
        """
        保存函数信息
        :param function_info: 函数信息
        :param module_id: 模块 ID
        :param class_id: 类 ID
        """
        function_info_entity = FunctionInfoEntity.from_function_info(function_info, module_id=module_id, class_id=class_id)
        self.session.add(function_info_entity)
        self.session.commit()
        return function_info_entity

    def clear_database(self):
        """
        清理数据库
        :return:
        """

        table_names = [
            ProjectInfoEntity.__tablename__,
            ModuleInfoEntity.__tablename__,
            ClassInfoEntity.__tablename__,
            FunctionInfoEntity.__tablename__
        ]

        # 禁用外键检查
        self.session.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        # 清空各表数据
        for table_name in table_names:
            self.session.execute(text(f"TRUNCATE TABLE {table_name};"))
        # 启用外键检查
        self.session.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

        self.session.commit()

        db_name = self.session.bind.url.database
        logger.info(f"已清空 MySQL: {db_name} 数据库")
