import sys


import pyrootutils

project_root = str(pyrootutils.find_root())
sys.path.insert(0, project_root)

from libs.core.code.impl.python_code_parser import PythonCodeParser

# class TestPythonParser(unittest.TestCase):
#
#     def setUp(self):
#         self.parser = PythonCodeParser()
#         self.test_file_path = os.path.abspath(
#             os.path.join(project_root, "libs/utils/log_helper.py")
#         )
#         self.test_file_path = os.path.abspath(self.test_file_path)
#
#     def test_parse_log_helper(self):
#         self.assertTrue(
#             os.path.exists(self.test_file_path),
#             f"测试文件不存在: {self.test_file_path}"
#         )
#
#         # 执行解析
#         module_info = self.parser.parse(self.test_file_path)
#
#         # 增加断言验证解析结果（关键！否则测试无法判断是否正确）
#         self.assertIsNotNone(module_info, "解析结果不能为空")
#         self.assertTrue(hasattr(module_info, "to_json"), "module_info 必须有 to_json 方法")
#
#         # 可选：验证JSON结果的基本结构（根据实际返回调整）
#         json_result = module_info.to_json()
#         self.assertIsInstance(json_result, str, "to_json() 必须返回字符串")


if __name__ == '__main__':
    # unittest.main(verbosity=2)
    module_info = PythonCodeParser().parse_file("../libs/utils/log_helper.py")
    print(module_info.to_json())
