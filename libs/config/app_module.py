from injector import Injector, Module, Binder, singleton

from libs.config.app_config import AppConfig
from libs.utils.log_helper import LogHelper
from libs.utils.task_initializer import TaskInitializer

logger = LogHelper.get_logger()


class AppModule(Module):
    def configure(self, binder: Binder):
        # 绑定应用配置
        app_config = AppConfig()
        binder.bind(AppConfig, to=app_config, scope=singleton)
        logger.info(f"App is running in {app_config.APP_ENV.name} environment.")

        # 绑定任务初始化器
        task_initializer = TaskInitializer()
        binder.bind(TaskInitializer, to=task_initializer, scope=singleton)
        logger.info(f"Task initializer is set up.")


app_injector = Injector([AppModule()])
