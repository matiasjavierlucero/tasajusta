"""
Endpoint del agente conversacional de TasaJusta.
Usa LangGraph create_react_agent (Groq openai/gpt-oss-120b) con tool use.

El grafo ReAct corre internamente:
  1. LLM decide si llamar una tool o responder directamente
  2. Si hay tool_calls → ToolNode las ejecuta y vuelve al LLM
  3. Si hay respuesta final → retorna

Observabilidad: GroqInstrumentor (en main.py) auto-traza las llamadas al LLM;
el span "tasajusta-agent" envuelve todo el ciclo ReAct.
"""

import json
import os
from contextlib import nullcontext

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from api.agent_tools import make_langchain_tools
from api.schemas import AgentRequest, AgentResponse

router = APIRouter()

GROQ_API_KEY      = os.getenv("GROQ_API_KEY")
_LANGFUSE_ENABLED = bool(os.getenv("LANGFUSE_PUBLIC_KEY"))
_MODEL            = "openai/gpt-oss-120b"

_SYSTEM_BASE = """Sos un asesor de compra de autos usados para TasaJusta, una plataforma argentina de inteligencia de precios.

Tenés acceso a una base de datos real de publicaciones de autos. Cuando el usuario busque un auto o pida recomendaciones:
1. Usá las tools disponibles para consultar datos reales — nunca inventes autos ni precios
2. Presentá los resultados de forma clara: marca, modelo, año, km, precio y link
3. Destacá las oportunidades (autos publicados por debajo del precio de mercado según nuestro modelo ML)
4. Si el usuario pregunta cuánto vale un auto, usá predecir_precio

IMPORTANTE sobre precios y unidades:
- Todos los precios en la base de datos están en PESOS ARGENTINOS (ARS)
- Si el usuario menciona dólares (u$s, USD, $), convertí al tipo de cambio dólar blue del día antes de usar precio_max
- Ejemplo: "10000 dólares" con blue a {dolar_blue} → precio_max = {precio_ars_equiv}
- El parámetro km_min filtra autos con MÍNIMO X km (para "más de X km")
- El parámetro km_max filtra autos con MÁXIMO X km (para "menos de X km")

Si el usuario pregunta algo que NO tenga relación con autos, compra de vehículos o el mercado automotriz argentino, respondé: "Solo puedo ayudarte con consultas sobre autos usados en Argentina."

Respondé siempre en español. Sé conciso y útil."""


def _build_system_prompt(app_state) -> str:
    dolar = getattr(app_state, "dolar_blue", None)
    if dolar:
        ejemplo = int(dolar * 10_000)
        return _SYSTEM_BASE.format(
            dolar_blue=f"${int(dolar):,}",
            precio_ars_equiv=f"${ejemplo:,}",
        )
    return _SYSTEM_BASE.format(
        dolar_blue="valor desconocido",
        precio_ars_equiv="precio_max en ARS",
    )


def _to_lc(messages: list[dict]) -> list[BaseMessage]:
    """Convierte mensajes del formato API ({role, content}) a objetos LangChain."""
    return [
        HumanMessage(content=m["content"]) if m["role"] == "user"
        else AIMessage(content=m["content"])
        for m in messages
    ]


def _make_graph(app_state):
    llm    = ChatGroq(model=_MODEL, api_key=GROQ_API_KEY, max_tokens=1024)
    tools  = make_langchain_tools(app_state)
    system = _build_system_prompt(app_state)
    return create_react_agent(llm, tools, state_modifier=system)


def _langfuse_ctxs(req: AgentRequest, user_input: str):
    if _LANGFUSE_ENABLED:
        from langfuse import get_client, propagate_attributes
        langfuse = get_client()
        return (
            langfuse.start_as_current_observation(
                as_type="agent", name="tasajusta-agent", input=user_input,
            ),
            propagate_attributes(session_id=req.session_id, tags=["agent", "tasajusta"]),
        )
    return nullcontext(), nullcontext()


@router.post("/agent", response_model=AgentResponse)
def agent(req: AgentRequest, request: Request):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY no configurada")

    user_input              = req.messages[-1]["content"] if req.messages else ""
    agent_ctx, attrs_ctx    = _langfuse_ctxs(req, user_input)

    try:
        with agent_ctx as agent_obs:
            with attrs_ctx:
                graph   = _make_graph(request.app.state)
                result  = graph.invoke({"messages": _to_lc(req.messages)})
                content = result["messages"][-1].content
                if agent_obs is not None:
                    agent_obs.update(output=content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error del agente: {e}")

    return AgentResponse(
        response=content,
        messages=[*req.messages, {"role": "assistant", "content": content}],
    )


@router.post("/agent/stream")
def agent_stream(req: AgentRequest, request: Request):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY no configurada")

    user_input = req.messages[-1]["content"] if req.messages else ""

    def generate():
        agent_ctx, attrs_ctx = _langfuse_ctxs(req, user_input)

        try:
            with agent_ctx as agent_obs:
                with attrs_ctx:
                    graph        = _make_graph(request.app.state)
                    full_content = ""

                    for chunk_msg, _ in graph.stream(
                        {"messages": _to_lc(req.messages)},
                        stream_mode="messages",
                    ):
                        # Filtrar: solo tokens del LLM en la respuesta final
                        # (excluye tool_call_chunks = chunks con argumentos de tools)
                        if (
                            isinstance(chunk_msg, AIMessageChunk)
                            and chunk_msg.content
                            and not chunk_msg.tool_call_chunks
                        ):
                            full_content += chunk_msg.content
                            yield f"data: {json.dumps({'token': chunk_msg.content})}\n\n"

                    if agent_obs is not None:
                        agent_obs.update(output=full_content)

                    final_msgs = [*req.messages, {"role": "assistant", "content": full_content}]
                    yield f"data: {json.dumps({'done': True, 'messages': final_msgs})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': f'Error del agente: {e}'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
