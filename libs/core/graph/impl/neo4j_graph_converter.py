from py2neo import Graph, Node, Relationship

from libs.config.app_config import AppConfig
from libs.config.app_module import app_injector
from libs.core.code.code_models import ModuleInfo, ClassInfo, FunctionInfo, MethodInfo, ImportFrom, ImportName
from libs.core.graph.base_graph_converter import BaseGraphConverter
from libs.core.graph.graph_models import ModuleNode, FunctionNode, ClassNode, NodeLabel, GraphType, MethodNode

from libs.utils.log_helper import LogHelper

logger = LogHelper.get_logger()
app_config = app_injector.get(AppConfig)


class Neo4JGraphConverter(BaseGraphConverter):

    def __init__(self, rebuild: bool = False):
        super().__init__(rebuild)
        self.neo4j_db = app_config.NEO4J_DATABASE
        self.neo4j_client = Graph(
            name=self.neo4j_db,
            profile=app_config.NEO4J_URI,
            auth=(app_config.NEO4J_USER, app_config.NEO4J_PASSWORD),
        )
        logger.info(f"Connected to Neo4j database: {self.neo4j_db}")

    def create_module_node(self, module_info: ModuleInfo) -> Node:
        """
        创建模块节点
        :param module_info: 模块信息
        :return: 模块节点
        """
        full_qualified_name = module_info.full_qualified_name
        if full_qualified_name in self.module_nodes:
            return self.module_nodes[full_qualified_name]

        # 模块节点
        module_node = ModuleNode(
            labels=[NodeLabel.MODULE],
            name=module_info.module_name,
            full_qualified_name=module_info.full_qualified_name,
            file_path=module_info.file_path,
            docs=module_info.docs,
            constants=module_info.constants,
            variables=module_info.variables,
        )

        # 写入模块节点
        neo4j_module_node = module_node.to_graph_node(GraphType.NEO4J)
        self.neo4j_client.create(neo4j_module_node)

        # 缓存模块节点
        self.module_nodes[full_qualified_name] = neo4j_module_node
        return neo4j_module_node

    def create_class_node(self, full_qualified_name: str, cls_info: ClassInfo, parent_node: Node) -> Node:
        """
        创建类节点
        :param full_qualified_name: 模块全限定名
        :param cls_info: 类信息
        :param parent_node: 父节点
        :return: 类节点
        """
        key = (full_qualified_name, cls_info.name)
        if key in self.class_nodes:
            return self.class_nodes[key]

        # 类节点
        class_node = ClassNode(
            labels=[NodeLabel.CLASS],
            name=cls_info.name,
            docs=cls_info.docs,
            bases=cls_info.bases,
            class_constants=cls_info.class_constants,
            class_variables=cls_info.class_variables,
        )

        # 写入类节点
        neo4j_class_node = class_node.to_graph_node(GraphType.NEO4J)
        self.neo4j_client.create(neo4j_class_node)

        # 缓存类节点
        self.class_nodes[key] = neo4j_class_node

        # 建立包含关系（模块包含类 或 外层类包含嵌套类）
        rel_type = "HAS_CLASS"
        self.neo4j_client.create(Relationship(parent_node, rel_type, neo4j_class_node))

        # 处理嵌套类
        for nested_cls in cls_info.nested_classes:
            self.create_class_node(full_qualified_name, nested_cls, neo4j_class_node)

        return neo4j_class_node

    def create_method_node(self, full_qualified_name: str, class_name: str, method_info: MethodInfo, class_node: Node) -> Node:
        """
        创建类方法节点
        :param full_qualified_name: 模块全限定名
        :param class_name: 类名称
        :param method_info: 方法信息
        :param class_node: 类节点
        :return: 方法节点
        """
        key = (full_qualified_name, class_name, method_info.name)
        if key in self.method_nodes:
            return self.method_nodes[key]

        # 方法节点
        method_node = MethodNode(
            labels=[NodeLabel.METHOD],
            name=method_info.name,
            docs=method_info.docs,
            type=method_info.type,
            returns=method_info.returns,
            variables=method_info.variables,
        )

        # 写入方法节点
        neo4j_method_node = method_node.to_graph_node(GraphType.NEO4J)
        self.neo4j_client.create(neo4j_method_node)
        self.method_nodes[key] = neo4j_method_node

        # 建立包含关系（类包含方法）
        rel_type = f"HAS_{method_info.type.value.upper()}_METHOD"
        self.neo4j_client.create(Relationship(class_node, rel_type, neo4j_method_node))

        return neo4j_method_node

    def create_function_node(self, full_qualified_name: str, func_info: FunctionInfo, module_node: Node) -> Node:
        """
        创建函数节点
        :param full_qualified_name: 模块全限定名
        :param func_info: 函数信息
        :param module_node: 模块节点
        :return: 函数节点
        """
        key = (full_qualified_name, func_info.name)
        if key in self.function_nodes:
            return self.function_nodes[key]

        func_node = FunctionNode(
            labels=[NodeLabel.FUNCTION],
            name=func_info.name,
            docs=func_info.docs,
            type=func_info.type,
            returns=func_info.returns,
            variables=func_info.variables,
        )

        # 写入方法节点
        neo4j_func_node = func_node.to_graph_node(GraphType.NEO4J)
        self.neo4j_client.create(neo4j_func_node)
        self.function_nodes[key] = neo4j_func_node

        # 建立包含关系（模块包含方法）
        rel_type = f"HAS_FUNCTION"
        self.neo4j_client.create(Relationship(module_node, rel_type, neo4j_func_node))

        return neo4j_func_node

    def handle_class_inheritance(self, full_qualified_name: str, cls_info: ClassInfo):
        """
        处理类继承关系
        :param full_qualified_name: 模块全限定名
        :param cls_info: 类信息
        :return: None
        """
        class_key = (full_qualified_name, cls_info.name)
        if class_key not in self.class_nodes:
            return

        current_class_node = self.class_nodes[class_key]
        for base_class_name in cls_info.bases:
            # 查找父类节点（不处理跨模块继承）
            base_class_key = (full_qualified_name, base_class_name)
            if base_class_key in self.class_nodes:
                base_class_node = self.class_nodes[base_class_key]
                rel_type = "INHERITS_FROM"
                self.neo4j_client.create(Relationship(current_class_node, rel_type, base_class_node))

    def handle_import_relations(self, module: ModuleInfo, module_node: ModuleNode):
        """
        处理 from...import... 类型导入
        :param module: ModuleInfo
        :param module_node: ModuleNode
        :return: None
        """
        from_imports: list[ImportFrom] = module.imports.get("from", [])
        for import_from in from_imports:
            imported_module = import_from.module
            if not imported_module:
                continue
            # 查找被导入的模块节点
            matched_module = next(
                (m for m in self.module_nodes if imported_module in m),
                None
            )
            if matched_module:
                imported_node = self.module_nodes[matched_module]
                self.neo4j_client.create(Relationship(module_node, "IMPORTS", imported_node))

        # 处理直接 import 类型导入
        normal_imports: list[ImportName] = module.imports.get("normal", [])
        for normal_import in normal_imports:
            imported_name = normal_import.name or normal_import.as_name
            matched_module = next(
                (m for m in self.module_nodes if imported_name in m),
                None
            )
            if matched_module:
                imported_node = self.module_nodes[matched_module]
                self.neo4j_client.create(Relationship(module_node, "IMPORTS", imported_node))

    def clear_database(self):
        """
        清空数据库中的所有节点和关系
        :return:
        """
        self.neo4j_client.delete_all()
        logger.info(f"已清空 Neo4j: {self.neo4j_db} 数据库")


if __name__ == '__main__':
    parser = Neo4JGraphConverter()
    parser.clear_database()
