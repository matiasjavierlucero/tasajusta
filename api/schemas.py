from pydantic import BaseModel, Field


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
