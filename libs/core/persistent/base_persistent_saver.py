from abc import ABC, abstractmethod

from libs.core.code.code_models import ModuleInfo, ClassInfo, FunctionInfo, ProjectInfo
from libs.core.persistent.persistent_models import ProjectInfoEntity, ModuleInfoEntity, ClassInfoEntity, FunctionInfoEntity, FunctionType
from libs.utils.log_helper import LogHelper

logger = LogHelper.get_logger()


class BasePersistentSaver(ABC):

    @abstractmethod
    def __init__(self, rebuild: bool = False, **kwargs):
        self.rebuild = rebuild

    @abstractmethod
    def save_project_info(self, project_info: ProjectInfo) -> ProjectInfoEntity:
        """
        保存项目信息
        :param project_info: 项目信息
        :return:
        """
        raise NotImplementedError()

    @abstractmethod
    def save_module_info(self, module_info: ModuleInfo, project_id: int) -> ModuleInfoEntity:
        """
        保存模块信息
        :param module_info: 模块信息
        :param project_id: 项目 ID
        :return: 模块信息实体
        """
        raise NotImplementedError()

    @abstractmethod
    def save_class_info(self, class_info: ClassInfo, module_id: int, parent_class_id: int = None) -> ClassInfoEntity:
        """
        保存类信息
        :param class_info: 类信息
        :param module_id: 模块 ID
        :param parent_class_id: 父类 ID
        :return: 类信息实体
        """
        raise NotImplementedError()

    @abstractmethod
    def save_function_info(self, function_info: FunctionInfo, module_id: int = None, class_id: int = None) -> FunctionInfoEntity:
        """
        保存函数信息
        :param function_info: 函数信息
        :param module_id: 模块 ID
        :param class_id: 类 ID
        :return: 函数信息实体
        """
        raise NotImplementedError()

    @abstractmethod
    def clear_database(self):
        """
        清理数据库
        :return:
        """
        raise NotImplementedError()

    def persistence(self, project_info: ProjectInfo, module_infos: list[ModuleInfo]):
        """
        保存项目信息和模块信息
        :param project_info: 项目信息
        :param module_infos: 模块信息列表
        :return:
        """
        if not self.rebuild:
            logger.info("非重建模式，跳过数据库构建")
            return

        self.clear_database()

        # 保存项目信息
        project_info_entity = self.save_project_info(project_info)
        # 遍历模块信息
        for module_info in module_infos:
            # 保存模块信息
            module_infos_entity = self.save_module_info(module_info, project_id=project_info_entity.id)
            # 遍历模块中的类信息
            for class_info in module_info.classes:
                # 保存类信息
                self.save_class_info(class_info, module_id=module_infos_entity.id, parent_class_id=None)
            # 遍历模块中的函数信息
            for func_info in module_info.functions:
                # 保存函数信息
                self.save_function_info(func_info, module_id=module_infos_entity.id, class_id=None)
