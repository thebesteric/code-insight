from injector import Injector, Module, Binder, singleton

from libs.config.app_config import AppConfig
from libs.utils.log_helper import LogHelper

logger = LogHelper.get_logger()


class AppModule(Module):
    def configure(self, binder: Binder):
        app_config = AppConfig()
        logger.info(f"App is running in {app_config.APP_ENV.name} environment.")
        binder.bind(AppConfig, to=app_config, scope=singleton)


app_injector = Injector([AppModule()])
