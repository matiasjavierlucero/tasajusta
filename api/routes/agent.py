"""
Endpoint del agente conversacional de TasaJusta.
Usa Groq (Llama 3.3 70B) con tool use para responder en lenguaje natural
consultando la base de datos real de autos.
"""

import os

from groq import Groq
from fastapi import APIRouter, HTTPException, Request

from api.schemas import AgentRequest, AgentResponse
from api.agent_tools import TOOLS, execute_tool

router = APIRouter()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

SYSTEM_PROMPT = """Sos un asesor de compra de autos usados para TasaJusta, una plataforma argentina de inteligencia de precios.

Tenés acceso a una base de datos real de publicaciones de autos. Cuando el usuario busque un auto o pida recomendaciones:
1. Usá las tools disponibles para consultar datos reales — nunca inventes autos ni precios
2. Presentá los resultados de forma clara: marca, modelo, año, km, precio y link
3. Destacá las oportunidades (autos publicados por debajo del precio de mercado según nuestro modelo ML)
4. Si el usuario pregunta cuánto vale un auto, usá predecir_precio

Respondé siempre en español. Sé conciso y útil."""


@router.post("/agent", response_model=AgentResponse)
def agent(req: AgentRequest, request: Request):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY no configurada")

    client = Groq(api_key=GROQ_API_KEY)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *req.messages]

    # Agentic loop: el modelo puede llamar tools múltiples veces antes de responder
    for _ in range(5):  # máximo 5 iteraciones para evitar loops infinitos
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=1024,
        )

        message = response.choices[0].message

        if not message.tool_calls:
            # El modelo decidió responder — salimos del loop
            return AgentResponse(
                response=message.content,
                messages=[*req.messages, {"role": "assistant", "content": message.content}],
            )

        # Ejecutar cada tool call y agregar los resultados al historial
        messages.append(message)
        for tool_call in message.tool_calls:
            result = execute_tool(
                name=tool_call.function.name,
                arguments=tool_call.function.arguments,
                app_state=request.app.state,
            )
            messages.append({
                "role":         "tool",
                "tool_call_id": tool_call.id,
                "content":      result,
            })

    raise HTTPException(status_code=500, detail="El agente no pudo completar la respuesta")
