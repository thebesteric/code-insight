from injector import Injector, Module, Binder, singleton

from libs.config.app_config import AppConfig
from libs.config.app_initializer import AppInitializer
from libs.utils.log_helper import LogHelper

logger = LogHelper.get_logger()


class AppModule(Module):
    def configure(self, binder: Binder):
        app_config = AppConfig()
        binder.bind(AppConfig, to=app_config, scope=singleton)
        logger.info(f"App is running in {app_config.APP_ENV.name} environment.")

        app_initializer = AppInitializer()
        binder.bind(AppInitializer, to=app_initializer, scope=singleton)
        logger.info(f"App initializer is set up.")


app_injector = Injector([AppModule()])