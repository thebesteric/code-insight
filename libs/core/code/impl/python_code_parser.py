import ast
from typing import Optional

from libs.core.code.base_code_parser import BaseCodeParser
from libs.core.code.code_models import FunctionInfo, ClassInfo, ModuleInfo, ImportName, ImportFrom, FunctionArgsInfo, Argument, VariableInfo, FunctionType
from libs.utils.log_helper import LogHelper

logger = LogHelper.get_logger()


class PythonCodeParser(BaseCodeParser):
    """
    Python 代码解析器。
    """

    def __init__(self):
        """
        初始化 Python 解析器
        """
        super().__init__(
            file_suffixes=['.py'],
            ignore_dirs=['__pycache__', '.venv', 'tests']
        )

    # 处理模块
    def visit_Module(self, node: ast.Module) -> None:
        self.module_info.docs = ast.get_docstring(node) or ""
        self.generic_visit(node)

    # 处理导入语句
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.module_info.imports["normal"].append(
                ImportName(name=alias.name, as_name=alias.asname if alias.asname else None)
            )
        self.generic_visit(node)

    # 处理 from 导入语句
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.module_info.imports["from"].append(
            ImportFrom(
                module=node.module,
                names=[
                    ImportName(name=alias.name, as_name=alias.asname if alias.asname else None)
                    for alias in node.names
                ],
                level=node.level
            )
        )
        self.generic_visit(node)

    # 处理类定义（支持嵌套）
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_info = ClassInfo(
            name=node.name,
            bases=[self._unparse_node(base) for base in node.bases],
            docs=ast.get_docstring(node) or ""
        )

        # 处理嵌套类（记录父类上下文）
        parent_class = self.current_class
        self.current_class = class_info

        self.generic_visit(node)  # 遍历类内节点

        # 恢复父类上下文
        if parent_class:
            parent_class.nested_classes.append(class_info)
        else:
            self.module_info.classes.append(class_info)
        self.current_class = parent_class

    # 处理函数/方法定义
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    # 处理异步函数/方法定义
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        # 解析参数信息
        args_info = self._parse_args(node.args)
        # 解析返回值类型
        returns = self._unparse_node(node.returns) if node.returns else None
        # 解析装饰器
        decorators = [self._unparse_node(decorator) for decorator in node.decorator_list]

        func_info = FunctionInfo(
            name=node.name,
            args=args_info,
            returns=returns,
            docs=ast.get_docstring(node) or "",
            is_async=isinstance(node, ast.AsyncFunctionDef),
            type=FunctionType.INSTANCE_FUNC,
            decorators=decorators,
            body=self._get_function_body(node)
        )

        # 记录当前函数上下文
        self.current_function = func_info
        self.generic_visit(node)  # 遍历函数内节点

        # 区分模块级函数和类内方法
        if self.current_class:
            is_class_method = any(self._is_decorator(d, "classmethod") for d in node.decorator_list)
            is_static_method = any(self._is_decorator(d, "staticmethod") for d in node.decorator_list)
            # 类方法
            if is_class_method:
                func_info.type = FunctionType.CLASS_FUNC
                self.current_class.class_methods.append(func_info)
            # 静态方法
            elif is_static_method:
                func_info.type = FunctionType.STATIC_FUNC
                self.current_class.static_methods.append(func_info)
            # 实例方法
            else:
                func_info.type = FunctionType.INSTANCE_FUNC
                self.current_class.instance_methods.append(func_info)
        # 模块级函数
        else:
            self.module_info.functions.append(func_info)

        self.current_function = None

    # 处理变量赋值
    def visit_Assign(self, node: ast.Assign) -> None:
        self._parse_assignment(node, is_annotated=False)
        self.generic_visit(node)

    # 处理变量声明（带类型注解）
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._parse_assignment(node, is_annotated=True)
        self.generic_visit(node)

    # 获取函数体内容
    def _get_function_body(self, node: ast.FunctionDef) -> str:
        """
        获取函数体内容
        :param node: 函数定义节点
        :return: 函数体内容字符串
        """
        if not node.body:
            return ""

        # 获取函数体所有节点的起始和结束行号
        start_lineno = node.body[0].lineno
        end_lineno = node.body[-1].end_lineno

        # 读取源代码并截取函数体部分
        with open(self.module_info.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 注意：行号从 1 开始，列表索引从 0 开始
        body_lines = lines[start_lineno - 1:end_lineno]
        return ''.join(body_lines)

    # 解析函数参数
    def _parse_args(self, args_node: ast.arguments) -> FunctionArgsInfo:
        """
        解析函数参数为 FunctionArgInfo 模型
        :param args_node: 函数参数节点
        :return: FunctionArgInfo 模型
        """
        args_info = FunctionArgsInfo.model_construct()

        # 默认参数的数量
        num_defaults = len(args_node.defaults)

        # 位置参数数量
        num_posonlyargs = len(args_node.posonlyargs)
        # 普通参数数量
        num_normal_args = len(args_node.args)
        # 位置与普通参数数量 = 位置参数 + 普通参数
        num_args = num_normal_args + num_posonlyargs

        # 解析位置参数
        for i, arg in enumerate(args_node.posonlyargs):
            default_value_index = i if num_args == num_defaults else num_defaults - (num_args - i)
            default = self._unparse_node(args_node.defaults[default_value_index]) if default_value_index >= 0 else None
            args_info.pos_only_args.append(
                Argument(
                    name=arg.arg,
                    annotation=self._unparse_node(arg.annotation),
                    default=default
                )
            )

        # 解析普通参数
        for i, arg in enumerate(args_node.args):
            default_value_index = i - (num_normal_args - num_defaults)
            default = self._unparse_node(args_node.defaults[default_value_index]) if default_value_index >= 0 else None
            args_info.args.append(
                Argument(
                    name=arg.arg,
                    annotation=self._unparse_node(arg.annotation),
                    default=default
                )
            )

        # 解析 *args
        if args_node.vararg:
            args_info.var_args = Argument(
                name=args_node.vararg.arg,
                annotation=self._unparse_node(args_node.vararg.annotation),
                default=None
            )

        # 解析关键字参数
        kw_defaults = args_node.kw_defaults or []
        num_kw_defaults = len(kw_defaults)
        num_kw_only_args = len(args_node.kwonlyargs)
        for i, arg in enumerate(args_node.kwonlyargs):
            default_value_index = i if num_kw_only_args == num_kw_defaults else num_kw_defaults - (num_kw_only_args - i)
            default = self._unparse_node(kw_defaults[default_value_index]) if i < len(kw_defaults) else None
            args_info.kw_only_args.append(
                Argument(
                    name=arg.arg,
                    annotation=self._unparse_node(arg.annotation),
                    default=default
                )
            )

        # 解析 **kwargs
        if args_node.kwarg:
            args_info.kw_args = Argument(
                name=args_node.kwarg.arg,
                annotation=self._unparse_node(args_node.kwarg.annotation),
                default=None
            )

        return args_info

    def _parse_assignment(self, node: ast.Assign | ast.AnnAssign, is_annotated: bool) -> None:
        """
        解析赋值语句为 VariableInfo 或常量
        :param node: 赋值语句节点
        :param is_annotated: 是否为带注解的赋值语句
        :return: None
        """
        # 提取变量名、注解和值
        if is_annotated:
            if not isinstance(node.target, ast.Name):
                return
            var_name = node.target.id
            annotation = self._unparse_node(node.annotation) if node.annotation else None
            value = self._unparse_node(node.value) if node.value else None
        else:
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                return
            # 判断是否有 ID
            var_name = getattr(node.targets[0], "id")
            annotation = None
            value = self._unparse_node(node.value)

        # 区分常量和变量
        if var_name.isupper():
            # 常量：存入对应层级的常量字典
            if self.current_class:
                self.current_class.class_constants[var_name] = value
            else:
                self.module_info.constants[var_name] = value
        else:
            # 变量：创建 VariableInfo 模型
            var_info = VariableInfo(name=var_name, annotation=annotation, value=value)
            # 根据上下文添加到对应层级
            if self.current_function:
                self.current_function.variables.append(var_info)
            elif self.current_class:
                self.current_class.class_variables.append(var_info)
            else:
                self.module_info.variables.append(var_info)

    @staticmethod
    def _is_decorator(decorator: ast.AST | ast.expr, name: str) -> bool:
        """
        判断装饰器类型是否匹配
        :param decorator: 装饰器节点
        :param name: 装饰器名称
        :return: 是否匹配
        """
        if isinstance(decorator, ast.Name):
            return decorator.id == name
        if isinstance(decorator, ast.Attribute):
            return decorator.attr == name
        return False

    @staticmethod
    def _unparse_node(node: ast.AST | ast.expr) -> Optional[str]:
        """
        将 AST 节点转为字符串表示
        :param node: AST 节点
        :return: 节点的字符串表示
        """
        if node is None:
            return None
        try:
            return ast.unparse(node)
        except Exception as e:
            return f"<unparseable: {type(node).__name__} ({e})>"

    def parse_file(self, file_path: str) -> ModuleInfo:
        try:
            # 初始化 ModuleInfo 模型
            self.module_info = ModuleInfo.model_construct(file_path=file_path)
            # 读取文件内容
            source_code = self.read_file(file_path)
            # 解析为 AST
            tree = ast.parse(source_code, filename=file_path)
            # 遍历 AST 节点
            self.visit(tree)
            # 返回结果
            return self.module_info
        except SyntaxError as e:
            logger.error(f"解析失败：{e}")
            exit()
