from sqlalchemy import Column, String, Date, Integer, ForeignKey, JSON
from src.scrum.infrastructure.database import Base

class ProyectoMembershipModel(Base):
    __tablename__ = "proyecto_memberships"
    
    proyecto_id = Column(String, ForeignKey("proyectos.id", ondelete="CASCADE"), primary_key=True)
    usuario_id = Column(String, primary_key=True)
    rol = Column(String, nullable=False)


class ProyectoModel(Base):
    __tablename__ = "proyectos"
    
    id = Column(String, primary_key=True)
    nombre = Column(String, nullable=False)
    descripcion = Column(String, default="")
    fecha_inicio = Column(Date, nullable=False)


class SprintModel(Base):
    __tablename__ = "sprints"
    
    id = Column(String, primary_key=True)
    proyecto_id = Column(String, ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    estado = Column(String, nullable=False)
    velocidad_comprometida = Column(Integer, default=0)
    velocidad_realizada = Column(Integer, default=0)
    objetivo = Column(String, default="")


class HistoriaUsuarioModel(Base):
    __tablename__ = "historias_usuario"
    
    id = Column(String, primary_key=True)
    proyecto_id = Column(String, ForeignKey("proyectos.id", ondelete="CASCADE"), nullable=False)
    sprint_id = Column(String, ForeignKey("sprints.id", ondelete="SET NULL"), nullable=True)
    correlativo = Column(String, nullable=False)
    titulo = Column(String, nullable=False)
    narrativa = Column(String, nullable=False)
    criterios_aceptacion = Column(JSON, nullable=False)  # Lista de criterios
    esfuerzo_estimado = Column(Integer, default=0)
    estado = Column(String, nullable=False)


class TareaModel(Base):
    __tablename__ = "tareas"
    
    id = Column(String, primary_key=True)
    historia_id = Column(String, ForeignKey("historias_usuario.id", ondelete="CASCADE"), nullable=False)
    titulo = Column(String, nullable=False)
    descripcion = Column(String, nullable=False)
    estado = Column(String, nullable=False)
    asignado_a = Column(String, nullable=True)


class UsuarioScrumModel(Base):
    __tablename__ = "usuarios_scrum"
    
    id = Column(String, primary_key=True)
    nombre_completo = Column(String, nullable=False)
    email = Column(String, nullable=False)
    rol_global = Column(String, nullable=False)
