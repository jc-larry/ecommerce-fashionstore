from typing import List, Optional
from sqlalchemy import Table, Column, ForeignKey, String, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.packages.seguridad_y_usuarios.models import User

# [CU06 / CU09] Tabla asociativa intermedia N:N para empleados y sucursales
branch_employees = Table(
    "branch_employees",
    Base.metadata,
    Column("branch_id", ForeignKey("branches.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(20))
    city: Mapped[Optional[str]] = mapped_column(String(50), default="Santa Cruz")
    zone: Mapped[Optional[str]] = mapped_column(String(80))
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    whatsapp: Mapped[Optional[str]] = mapped_column(String(20))

    # Horarios y días de atención comercial
    opening_time: Mapped[Optional[str]] = mapped_column(String(10), default="09:00")
    closing_time: Mapped[Optional[str]] = mapped_column(String(10), default="21:00")
    days_open: Mapped[Optional[str]] = mapped_column(String(100), default="Lunes a Sábado")

    # Capacidades y servicios de la sucursal
    has_fitting_room: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    pickup_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Coordenadas geográficas para localización multisucursal y cálculo de envíos
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 8))
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(11, 8))
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # [Control en tiempo real] Estado de atención diaria (Abierta vs Cerrada por refacciones/arreglos/feriado)
    is_temporarily_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    closure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relación N:N con los usuarios empleados (encargados y cajeros)
    employees: Mapped[List[User]] = relationship(
        "User",
        secondary=branch_employees
    )
