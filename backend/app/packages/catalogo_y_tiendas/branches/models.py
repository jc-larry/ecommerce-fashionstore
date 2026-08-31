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
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Coordenadas geográficas para localización multisucursal y cálculo de envíos
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 8))
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(11, 8))
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relación N:N con los usuarios empleados (encargados y cajeros)
    employees: Mapped[List[User]] = relationship(
        "User",
        secondary=branch_employees
    )
