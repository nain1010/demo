from litestar.plugins import InitPluginProtocol
from litestar.config.app import AppConfig
from src.idp.application.controllers import AuthController

class IdpPlugin(InitPluginProtocol):
    """Plugin de Litestar para registrar el módulo IdP de forma modular."""
    
    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        # Registrar el controlador de autenticación del IdP
        app_config.route_handlers.append(AuthController)
        return app_config
