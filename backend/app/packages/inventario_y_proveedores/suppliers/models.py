from typing import List, Optional
from sqlalchemy import String, Table, Column, ForeignKey, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.packages.seguridad_y_usuarios.models import User

# [Rol PROVEEDOR] Tabla asociativa N:N entre usuarios con rol PROVEEDOR y su ficha de proveedor
supplier_employees = Table(
    "supplier_employees",
    Base.metadata,
    Column("supplier_id", ForeignKey("suppliers.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    nit: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), default="Telas y Textiles", nullable=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[str] = mapped_column(String(50), default="Santa Cruz", nullable=False)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=5.0, nullable=False)
    delivery_time_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    specialty: Mapped[Optional[str]] = mapped_column(String(100), default="Confección y Textiles", nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Usuario(s) con rol PROVEEDOR vinculados a esta ficha (portal de autoservicio)
    users: Mapped[List[User]] = relationship("User", secondary=supplier_employees)

