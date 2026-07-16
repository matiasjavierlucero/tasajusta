from pydantic import BaseModel, Field
from typing import Any


class PredictRequest(BaseModel):
    marca:     str = Field(..., example="Toyota")
    modelo:    str = Field(..., example="Corolla")
    anio:      int = Field(..., ge=1990, le=2026, example=2018)
    km:        int = Field(..., ge=0, example=80000)
    provincia: str = Field(..., example="Mendoza")


class PredictResponse(BaseModel):
    precio_estimado_ars: int
    modelo_usado:        str
    dolar_blue_venta:    float | None
    advertencia:         str | None


class AgentRequest(BaseModel):
    messages: list[dict[str, Any]] = Field(
        ...,
        example=[{"role": "user", "content": "Busco un Toyota Corolla en Córdoba, máximo 80k km"}],
    )


class AgentResponse(BaseModel):
    response: str
    messages: list[dict[str, Any]]  # historial completo para la próxima llamada
