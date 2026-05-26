from litestar.plugins import InitPluginProtocol
from litestar.config.app import AppConfig
from src.scrum.application.controllers import ProjectController

class ScrumPlugin(InitPluginProtocol):
    """Plugin de Litestar para registrar el módulo Scrum de forma modular."""
    
    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        # Registrar el controlador de proyectos Scrum
        app_config.route_handlers.append(ProjectController)
        return app_config
