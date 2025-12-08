import os
from enum import Enum
from typing import Optional, Any

import pyrootutils
from pydantic import BaseModel, Field, field_validator, model_validator


class ImportName(BaseModel):
    """
    导入项信息（如 import xx as yy 中的 xx 和 yy）
    """
    name: str = Field(..., description="导入的原始名称")
    as_name: Optional[str] = Field(None, description="导入的别名")


class ImportFrom(BaseModel):
    """
    `from ... import ...` 类型的导入信息
    """
    module: Optional[str] = Field(None, description="模块名（如 'typing'，相对导入时可能为 None）")
    names: list[ImportName] = Field(..., description="导入的名称列表（含别名）")
    level: int = Field(0, ge=0, description="相对导入层级（0 表示绝对导入，1 表示 `from .`）")


class Argument(BaseModel):
    """
    函数参数的详细信息（含类型注解和默认值）
    """
    name: str = Field(..., description="参数名称（如 'x'）")
    annotation: Optional[str] = Field(None, description="参数的类型注解（如 'int' 或 'List[str]'）")
    default: Optional[str] = Field(None, description="参数的默认值（仅限关键字参数，如 '0.5'）")


class FunctionArgsInfo(BaseModel):
    """
    函数的所有参数集合（区分不同类型的参数）
    """
    pos_only_args: list[Argument] = Field(
        default_factory=list,
        description="仅限位置参数（/ 前的参数，如 `def func(a, /, b):` 中的 `a`）"
    )
    args: list[Argument] = Field(
        default_factory=list,
        description="普通参数（如 `def func(a, b):` 中的 `a` 和 `b`）"
    )
    var_args: Optional[Argument] = Field(
        None,
        description="可变位置参数（*args，如 `def func(*args):` 中的 `args`）"
    )
    kw_only_args: list[Argument] = Field(
        default_factory=list,
        description="仅限关键字参数（* 后的参数，如 `def func(*, a):` 中的 `a`）"
    )
    kw_args: Optional[Argument] = Field(
        None,
        description="可变关键字参数（**kwargs，如 `def func(** kwargs):` 中的 `kwargs`）"
    )


class VariableInfo(BaseModel):
    """
    变量的详细信息（含类型注解和赋值）
    """
    name: str = Field(..., description="变量名称（如 'count'）")
    annotation: Optional[str] = Field(None, description="变量的类型注解（如 'int'）")
    value: Optional[str] = Field(None, description="变量的赋值内容（如 '100' 或 '\"hello\"'）")


class FunctionType(Enum):
    """
    函数类型枚举
    """
    INSTANCE_FUNC = "INSTANCE_FUNC"
    STATIC_FUNC = "STATIC_FUNC"
    CLASS_FUNC = "CLASS_FUNC"


class FunctionInfo(BaseModel):
    """
    函数的完整信息
    """
    name: str = Field(..., description="函数/方法名称（如 'process_data'）")
    args: FunctionArgsInfo = Field(..., description="函数的参数信息（包含各类参数的详细描述）")
    is_async: bool = Field(False, description="函数是否为异步函数")
    type: FunctionType = Field(FunctionType.INSTANCE_FUNC, description="函数类型")
    decorators: list[str] = Field(
        default_factory=list,
        description="函数的装饰器列表（如 ['@classmethod', '@staticmethod']）"
    )
    body: str = Field("", description="函数的实现内容")
    returns: Optional[str] = Field(None, description="函数的返回值类型注解（如 'Dict[str, int]'）")
    docs: str = Field("", description="函数的文档信息")
    variables: list[VariableInfo] = Field(
        default_factory=list,
        description="函数内部定义的变量（含类型注解）"
    )


class MethodInfo(FunctionInfo):
    """
    方法的完整信息
    """
    pass


class ClassInfo(BaseModel):
    """
    类的完整信息（支持嵌套类）
    """
    name: str = Field(..., description="类名称（如 'OuterClass'）")
    docs: str = Field("", description="类的文档信息")
    bases: list[str] = Field(
        default_factory=list,
        description="父类列表（如 ['BaseClass']，无父类则为空列表）"
    )
    instance_methods: list[MethodInfo | FunctionInfo] = Field(
        default_factory=list,
        description="类的实例方法（不含类方法和静态方法）"
    )
    class_methods: list[MethodInfo | FunctionInfo] = Field(
        default_factory=list,
        description="类的类方法（带 @classmethod 装饰器）"
    )
    static_methods: list[MethodInfo | FunctionInfo] = Field(
        default_factory=list,
        description="类的静态方法（带 @staticmethod 装饰器）"
    )
    class_constants: dict[str, str] = Field(
        default_factory=dict,
        description="类级常量（全大写变量，如 {'MAX_SIZE': '1024'}）"
    )
    class_variables: list[VariableInfo] = Field(
        default_factory=list,
        description="类级变量（非全大写，含类型注解）"
    )
    nested_classes: list["ClassInfo"] = Field(
        default_factory=list,
        description="嵌套在当前类中的类（支持多层嵌套）"
    )

    @field_validator('class_constants')
    @classmethod
    def validate_constant_names(cls, v):
        """
        验证类常量的键是否为全大写（符合 Python 常量命名规范）
        :param v: 常量
        :return:
        """
        for name in v:
            if not name.isupper():
                raise ValueError(f"类常量 '{name}' 不符合命名规范（应为全大写）")
        return v


# 解决嵌套类的向前引用
ClassInfo.model_rebuild()


class ModuleInfo(BaseModel):
    """
    Python 模块的整体信息
    """
    file_path: str = Field(..., description="模块的文件路径")
    module_name: str = Field(..., description="模块的名称")
    docs: Optional[str] = Field(None, description="模块的文档信息")
    imports: dict[str, list[Any]] = Field(
        default_factory=lambda: {"normal": [], "from": []},
        description="模块的导入信息: 'normal' 为普通导入（import ...），'from' 为 from...import 导入"
    )
    classes: list[ClassInfo] = Field(
        default_factory=list,
        description="模块中定义的类（含嵌套类）"
    )
    functions: list[FunctionInfo] = Field(
        default_factory=list,
        description="模块级别的函数（不在类内部定义的函数）"
    )
    constants: dict[str, str] = Field(
        default_factory=dict,
        description="模块级常量（全大写变量，如 {'MAX_COUNT': '100'}）"
    )
    variables: list[VariableInfo] = Field(
        default_factory=list,
        description="模块级变量（非全大写，含类型注解）"
    )

    @classmethod
    def model_construct(cls, **kwargs):
        # 1. 调用父类的 model_construct() 构造实例
        instance = super().model_construct(**kwargs)
        # 2. 手动计算并赋值 model_name
        if hasattr(instance, "file_path") and not hasattr(instance, "module_name"):
            instance.module_name = cls._get_module_name(instance.file_path)
        return instance

    @field_validator('constants')
    @classmethod
    def validate_module_constant_names(cls, v):
        """验证模块常量的键是否为全大写"""
        for name in v:
            if not name.isupper():
                raise ValueError(f"模块常量 '{name}' 不符合命名规范（应为全大写）")
        return v

    @model_validator(mode='before')
    @classmethod
    def auto_set_module_name(cls, values):
        """
        自动根据 file_path 计算 module_name 并赋值
        :param values:
        :return:
        """
        file_path = values.get('file_path')
        if not file_path:
            raise ValueError("file_path 为必填字段，无法生成 model_name")

        # 从 values 中获取 module_name（若用户传入则直接使用），否则通过 _get_module_name 计算模块名
        module_name = values.get('module_name') or cls._get_module_name(file_path)

        # 将计算结果存入 values，覆盖原 module_name
        values['module_name'] = module_name
        return values

    @staticmethod
    def _get_module_name(file_path: str) -> str:
        """
        获取模块名
        :return: 模块名
        """
        project_root = pyrootutils.find_root().as_posix()
        return file_path.replace(project_root, "").lstrip("/").replace("/", ".").replace(".py", "")

    def to_json(self, *, indent: int = 2, ensure_ascii: bool = False) -> str:
        """
        将解析结果转换为 JSON 格式。
        :param indent: JSON 缩进空格数
        :param ensure_ascii: 是否确保 ASCII 编码
        :return: JSON 格式字符串
        """
        return self.model_dump_json(indent=indent, ensure_ascii=ensure_ascii)


class ProjectInfo(BaseModel):
    """
    项目整体信息
    """
    name: str = Field(..., description="项目名称")
    storage_path: str = Field(..., description="项目存储路径")
    repo_url: Optional[str] = Field(None, description="仓库地址")
