import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from py2neo import Node
from pydantic import BaseModel, Field
from setuptools.command.install_egg_info import install_egg_info

from libs.core.code.code_models import FunctionType, VariableInfo


class GraphType(Enum):
    """
    图类型枚举类
    """
    NEO4J = "neo4j"
    NEBULA = "nebula"


class NodeLabel(Enum):
    """
    节点标签枚举类
    """
    MODULE = "Module"
    CLASS = "Class"
    METHOD = "Method"
    FUNCTION = "Function"


class NodeType(Enum):
    """
    节点类型枚举类
    """
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"


class GraphNode(BaseModel, ABC):
    """
    图节点模型抽象类
    """
    labels: list[NodeLabel] = Field(..., description="标签列表")
    name: str = Field(..., description="名称")
    docs: str = Field("", description="文档信息")

    @abstractmethod
    def to_graph_node(self, graph_type: GraphType) -> Any:
        """
        将当前节点转换为对应的图节点对象
        :param graph_type: 图类型
        :return: 图节点对象
        """
        raise NotImplementedError(f"未实现 {graph_type} 类型的节点转换")


class ModuleNode(GraphNode):
    """
    模块节点模型
    """
    file_path: str = Field(..., description="模块的文件路径")
    full_qualified_name: str = Field(..., description="模块的全限定名")
    constants: dict[str, str] = Field(default_factory=dict, description="模块级常量（全大写变量，如 {'MAX_COUNT': '100'}）")
    variables: list[VariableInfo] = Field(default_factory=list, description="模块级变量（非全大写，含类型注解）")

    def to_graph_node(self, graph_type: GraphType) -> Any:
        if graph_type == GraphType.NEO4J:
            return Node(
                *[label.value for label in self.labels],
                name=self.name,
                full_qualified_name=self.full_qualified_name,
                file_path=self.file_path,
                docs=self.docs,
                constants=json.dumps(self.constants, ensure_ascii=False),
                variables=json.dumps([var.model_dump() for var in self.variables], ensure_ascii=False),
            )
        raise NotImplementedError(f"未实现 {graph_type} 类型的节点转换")


class ClassNode(GraphNode):
    """
    类节点模型
    """
    bases: list[str] = Field(default_factory=list, description="父类列表（如 ['BaseClass']，无父类则为空列表）")
    class_constants: dict[str, str] = Field(default_factory=dict, description="类级常量（全大写变量，如 {'MAX_SIZE': '1024'}）")
    class_variables: list[VariableInfo] = Field(default_factory=list, description="类级变量（非全大写，含类型注解）")

    def to_graph_node(self, graph_type: GraphType) -> Any:
        if graph_type == GraphType.NEO4J:
            return Node(
                *[label.value for label in self.labels],
                name=self.name,
                docs=self.docs,
                bases=json.dumps(self.bases, ensure_ascii=False),
                class_constants=json.dumps(self.class_constants, ensure_ascii=False),
                class_variables=json.dumps([var.model_dump() for var in self.class_variables], ensure_ascii=False),
            )
        raise NotImplementedError(f"未实现 {graph_type} 类型的节点转换")


class FunctionNode(GraphNode):
    """
    函数节点模型
    """
    type: FunctionType = Field(FunctionType.INSTANCE_FUNC, description="函数类型")
    returns: Optional[str] = Field(None, description="函数的返回值类型注解（如 'Dict[str, int]'）")
    variables: list[VariableInfo] = Field(default_factory=list, description="函数内部定义的变量（含类型注解）")

    def to_graph_node(self, graph_type: GraphType) -> Any:
        if graph_type == GraphType.NEO4J:
            return Node(
                *[label.value for label in self.labels],
                name=self.name,
                docs=self.docs,
                type=self.type.value,
                returns=self.returns,
                variables=json.dumps([var.model_dump() for var in self.variables], ensure_ascii=False),
            )
        raise NotImplementedError(f"未实现 {graph_type} 类型的节点转换")

class MethodNode(FunctionNode):
    """
    方法节点模型
    """
    pass