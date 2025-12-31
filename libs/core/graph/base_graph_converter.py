from abc import ABC, abstractmethod

from py2neo import Node

from libs.core.code.code_models import ModuleInfo, ClassInfo, FunctionInfo, MethodInfo
from libs.utils.log_helper import LogHelper

logger = LogHelper.get_logger()

class BaseGraphConverter(ABC):
    """
    抽象的图解析器类，用于解析模块信息并构建图结构。
    """

    @abstractmethod
    def __init__(self, rebuild: bool = False):
        """
        初始化图解析器
        """
        self.rebuild = rebuild
        self.module_nodes: dict[str, Node] = {}
        self.class_nodes: dict[tuple[str, str], Node] = {}
        self.method_nodes: dict[tuple[str, str, str], Node] = {}
        self.function_nodes: dict[tuple[str, str], Node] = {}

    @abstractmethod
    def create_module_node(self, module_info: ModuleInfo) -> Node:
        """
        创建模块节点
        :param module_info: 模块信息
        :return: 模块节点
        """
        raise NotImplementedError()

    @abstractmethod
    def create_class_node(self, module_name: str, cls_info: ClassInfo, parent_node: Node) -> Node:
        """
        创建类节点
        :param module_name: 模块名称
        :param cls_info: 类信息
        :param parent_node: 父节点
        :return: 类节点
        """
        raise NotImplementedError()

    @abstractmethod
    def create_method_node(self, module_name: str, class_name: str, method_info: MethodInfo, class_node: Node) -> Node:
        """
        创建类方法节点
        :param module_name: 模块名称
        :param class_name: 类名称
        :param method_info: 方法信息
        :param class_node: 类节点
        :return: 方法节点
        """
        raise NotImplementedError()

    @abstractmethod
    def create_function_node(self, module_name: str, func_info: FunctionInfo, module_node: Node) -> Node:
        """
        创建函数节点
        :param module_name: 模块名称
        :param func_info: 函数信息
        :param module_node: 模块节点
        :return: 函数节点
        """
        raise NotImplementedError()

    @abstractmethod
    def handle_class_inheritance(self, module_name: str, cls_info: ClassInfo):
        """
        处理类继承关系
        :param module_name: 模块名称
        :param cls_info: 类信息
        """
        raise NotImplementedError()

    @abstractmethod
    def handle_import_relations(self, module: ModuleInfo, module_node: Node):
        """
        处理模块导入关系
        :param module: 模块信息
        :param module_node: 模块节点
        """
        raise NotImplementedError()

    @abstractmethod
    def clear_database(self):
        """
        清空数据库中的所有节点和关系
        :return:
        """
        raise NotImplementedError()

    def convert(self, module_infos: list[ModuleInfo]) -> None:
        """
        解析模块信息并构建图结构。
        :param module_infos: 模块信息列表
        """
        num_modules = len(module_infos)
        if num_modules == 0:
            logger.warning("没有需要解析的模块")
            return

        if not self.rebuild:
            logger.info("非重建模式，跳过图谱构建")
            return

        # 清空数据库
        self.clear_database()

        # 解析模块信息
        for idx, module_info in enumerate(module_infos, 1):
            module_name = module_info.module_name
            logger.info(f"正在解析 [模块] 第 {idx}/{num_modules} 个：{module_name}")
            # 1. 创建模块节点
            module_node = self.create_module_node(module_info)

            # 2. 创建类节点及嵌套类
            for cls_info in module_info.classes:
                class_node = self.create_class_node(module_name, cls_info, module_node)
                # 处理类中的方法（普通方法、静态方法、类方法）
                methods = cls_info.instance_methods + cls_info.class_methods + cls_info.static_methods
                for method in methods:
                    self.create_method_node(module_name, cls_info.name, method, class_node)
                # 处理类继承关系
                self.handle_class_inheritance(module_name, cls_info)

            # 3. 创建模块级函数节点
            for func in module_info.functions:
                self.create_function_node(module_name, func, module_node)

            # 4. 处理模块导入关系
            self.handle_import_relations(module_info, module_node)
