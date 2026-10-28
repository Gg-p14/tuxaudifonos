from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

EstadoPedido = Literal["Comprada", "En preparación", "Enviado", "Entregado", "Cancelada"]
MetodoPago = Literal["Efectivo", "Transferencia", "Tarjeta"]


class AudifonoIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    id_marca: int = Field(gt=0)
    id_categoria: int = Field(gt=0)
    precio: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    precio_anterior: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    existencias: int = Field(ge=0, le=100000)
    imagen: HttpUrl | None = None
    descripcion: str = Field(default="", max_length=1000)
    bateria_horas: int | None = Field(default=None, gt=0, le=200)
    cancelacion_ruido: bool = False
    destacado: bool = False

    @field_validator("imagen", mode="before")
    @classmethod
    def vacio_a_nulo(cls, v):
        return v or None

    def a_dict(self) -> dict:
        datos = self.model_dump()
        datos["imagen"] = str(self.imagen) if self.imagen else None
        datos["precio"] = float(self.precio)
        datos["precio_anterior"] = float(self.precio_anterior) if self.precio_anterior else None
        return datos


class AudifonoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    id_marca: int | None = Field(default=None, gt=0)
    id_categoria: int | None = Field(default=None, gt=0)
    precio: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    precio_anterior: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    existencias: int | None = Field(default=None, ge=0, le=100000)
    imagen: HttpUrl | None = None
    descripcion: str | None = Field(default=None, max_length=1000)
    bateria_horas: int | None = Field(default=None, gt=0, le=200)
    cancelacion_ruido: bool | None = None
    destacado: bool | None = None

    def a_dict(self) -> dict:
        datos = self.model_dump(exclude_unset=True)
        for k in ("precio", "precio_anterior"):
            if datos.get(k) is not None:
                datos[k] = float(datos[k])
        if "imagen" in datos:
            datos["imagen"] = str(self.imagen) if self.imagen else None
        return datos


class ResenaIn(BaseModel):
    calificacion: int = Field(ge=1, le=5)
    comentario: str = Field(default="", max_length=500)


class RegistroSchema(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    apellidos: str = Field(min_length=2, max_length=120)
    correo: EmailStr
    telefono: str = Field(min_length=8, max_length=20, pattern=r"^[0-9+\-\s()]+$")
    password: str = Field(min_length=8, max_length=100)


class LoginSchema(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=1, max_length=100)


class PerfilSchema(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    apellidos: str = Field(min_length=2, max_length=120)
    telefono: str = Field(min_length=8, max_length=20, pattern=r"^[0-9+\-\s()]+$")


class DireccionIn(BaseModel):
    alias: str = Field(default="Casa", min_length=2, max_length=50)
    nombre_recibe: str = Field(min_length=2, max_length=150)
    telefono: str = Field(min_length=8, max_length=20, pattern=r"^[0-9+\-\s()]+$")
    direccion: str = Field(min_length=5, max_length=250)
    ciudad: str = Field(min_length=2, max_length=100)
    estado: str = Field(min_length=2, max_length=100)
    codigo_postal: str = Field(min_length=5, max_length=10, pattern=r"^[0-9]{5}$")
    referencia: str = Field(default="", max_length=250)
    predeterminada: bool = False


class DireccionUpdate(BaseModel):
    alias: str | None = Field(default=None, min_length=2, max_length=50)
    nombre_recibe: str | None = Field(default=None, min_length=2, max_length=150)
    telefono: str | None = Field(default=None, min_length=8, max_length=20)
    direccion: str | None = Field(default=None, min_length=5, max_length=250)
    ciudad: str | None = Field(default=None, min_length=2, max_length=100)
    estado: str | None = Field(default=None, min_length=2, max_length=100)
    codigo_postal: str | None = Field(default=None, pattern=r"^[0-9]{5}$")
    referencia: str | None = Field(default=None, max_length=250)
    predeterminada: bool | None = None


class ItemCompra(BaseModel):
    id_audifono: int = Field(gt=0)
    cantidad: int = Field(ge=1, le=20)


class CompraIn(BaseModel):
    items: list[ItemCompra] = Field(min_length=1, max_length=50)
    id_direccion: int | None = Field(default=None, gt=0)
    nueva_direccion: DireccionIn | None = None
    guardar_direccion: bool = False
    metodo_pago: MetodoPago = "Efectivo"


class EstadoIn(BaseModel):
    estado: EstadoPedido
    nota: str = Field(default="", max_length=250)
    codigo_seguimiento: str | None = Field(default=None, max_length=30)
