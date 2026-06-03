from sqlalchemy import Column, String, Boolean, DateTime, JSON
from src.idp.infrastructure.database import Base

class UserModel(Base):
    __tablename__ = "usuarios"
    
    id = Column(String, primary_key=True)
    nombre_completo = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    rol_global = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)


class SessionModel(Base):
    __tablename__ = "sesiones"
    
    token = Column(String, primary_key=True)
    usuario_id = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)


class OutboxEventModel(Base):
    __tablename__ = "eventos_outbox"
    
    event_id = Column(String, primary_key=True)
    event_name = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    occurred_on = Column(DateTime, nullable=False)
    processed = Column(Boolean, default=False)
