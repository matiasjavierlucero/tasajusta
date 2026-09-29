"""
Endpoint del agente conversacional de TasaJusta.
Usa Groq (Llama 3.3 70B) con tool use para responder en lenguaje natural
consultando la base de datos real de autos.

Observabilidad: cada turno genera un trace en Langfuse con la estructura:
  tasajusta-agent (agent)
    ├── groq-call (generation, auto via GroqInstrumentor)   ← primera llamada, retorna tool_calls
    ├── <tool_name> (tool, manual)                          ← resultado de cada herramienta
    └── groq-call (generation, auto via GroqInstrumentor)   ← llamada final con respuesta
"""

import json
import os
from contextlib import nullcontext

from groq import Groq, BadRequestError, APIStatusError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.schemas import AgentRequest, AgentResponse
from api.agent_tools import TOOLS, execute_tool

router = APIRouter()

GROQ_API_KEY      = os.getenv("GROQ_API_KEY")
_LANGFUSE_ENABLED = bool(os.getenv("LANGFUSE_PUBLIC_KEY"))

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


@router.post("/agent", response_model=AgentResponse)
def agent(req: AgentRequest, request: Request):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY no configurada")

    client   = Groq(api_key=GROQ_API_KEY)
    system   = _build_system_prompt(request.app.state)
    messages = [{"role": "system", "content": system}, *req.messages]

    user_input = req.messages[-1]["content"] if req.messages else ""

    # Span raíz del agente — engloba todo el loop ReAct
    if _LANGFUSE_ENABLED:
        from langfuse import get_client, propagate_attributes
        langfuse  = get_client()
        agent_ctx = langfuse.start_as_current_observation(
            as_type="agent",
            name="tasajusta-agent",
            input=user_input,
        )
        attrs_ctx = propagate_attributes(
            session_id=req.session_id,
            tags=["agent", "tasajusta"],
        )
    else:
        agent_ctx = nullcontext()
        attrs_ctx = nullcontext()

    try:
        with agent_ctx as agent_obs:
            with attrs_ctx:
                for _ in range(5):
                    response = client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=messages,
                        tools=TOOLS,
                        tool_choice="auto",
                        max_tokens=1024,
                    )

                    message = response.choices[0].message

                    if not message.tool_calls:
                        final_response = message.content
                        if agent_obs is not None:
                            agent_obs.update(output=final_response)
                        return AgentResponse(
                            response=final_response,
                            messages=[*req.messages, {"role": "assistant", "content": final_response}],
                        )

                    messages.append(message)

                    for tool_call in message.tool_calls:
                        # Span por tool call: input = args, output = resultado
                        if _LANGFUSE_ENABLED:
                            tool_ctx = langfuse.start_as_current_observation(
                                as_type="tool",
                                name=tool_call.function.name,
                                input=json.loads(tool_call.function.arguments),
                            )
                        else:
                            tool_ctx = nullcontext()

                        with tool_ctx as tool_obs:
                            try:
                                result = execute_tool(
                                    name=tool_call.function.name,
                                    arguments=tool_call.function.arguments,
                                    app_state=request.app.state,
                                )
                            except Exception as e:
                                result = f"Error ejecutando {tool_call.function.name}: {e}"

                            if tool_obs is not None:
                                tool_obs.update(output=result)

                        messages.append({
                            "role":         "tool",
                            "tool_call_id": tool_call.id,
                            "content":      result,
                        })

    except BadRequestError as e:
        raise HTTPException(status_code=400, detail=f"Error en la solicitud al modelo: {e}")
    except APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"Error del servicio de IA: {e.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")

    raise HTTPException(status_code=500, detail="El agente no pudo completar la respuesta")


@router.post("/agent/stream")
def agent_stream(req: AgentRequest, request: Request):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY no configurada")

    client     = Groq(api_key=GROQ_API_KEY)
    system     = _build_system_prompt(request.app.state)
    messages   = [{"role": "system", "content": system}, *req.messages]
    user_input = req.messages[-1]["content"] if req.messages else ""

    def generate():
        if _LANGFUSE_ENABLED:
            from langfuse import get_client, propagate_attributes
            langfuse  = get_client()
            agent_ctx = langfuse.start_as_current_observation(
                as_type="agent", name="tasajusta-agent", input=user_input,
            )
            attrs_ctx = propagate_attributes(session_id=req.session_id, tags=["agent", "tasajusta"])
        else:
            agent_ctx = nullcontext()
            attrs_ctx = nullcontext()

        try:
            with agent_ctx as agent_obs:
                with attrs_ctx:
                    for _ in range(5):
                        stream = client.chat.completions.create(
                            model="openai/gpt-oss-120b",
                            messages=messages,
                            tools=TOOLS,
                            tool_choice="auto",
                            max_tokens=1024,
                            stream=True,
                        )

                        tool_calls_acc = {}
                        full_content   = ""
                        finish_reason  = None

                        for chunk in stream:
                            choice = chunk.choices[0]
                            delta  = choice.delta

                            if delta.tool_calls:
                                for tc in delta.tool_calls:
                                    idx = tc.index
                                    if idx not in tool_calls_acc:
                                        tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                                    if tc.id:
                                        tool_calls_acc[idx]["id"] = tc.id
                                    if tc.function:
                                        if tc.function.name:
                                            tool_calls_acc[idx]["name"] = tc.function.name
                                        if tc.function.arguments:
                                            tool_calls_acc[idx]["arguments"] += tc.function.arguments

                            if delta.content:
                                full_content += delta.content
                                yield f"data: {json.dumps({'token': delta.content})}\n\n"

                            if choice.finish_reason:
                                finish_reason = choice.finish_reason

                        if finish_reason == "tool_calls":
                            tool_calls = [
                                {
                                    "id":       tool_calls_acc[i]["id"],
                                    "type":     "function",
                                    "function": {
                                        "name":      tool_calls_acc[i]["name"],
                                        "arguments": tool_calls_acc[i]["arguments"],
                                    },
                                }
                                for i in sorted(tool_calls_acc)
                            ]

                            messages.append({
                                "role":       "assistant",
                                "content":    None,
                                "tool_calls": tool_calls,
                            })

                            for tc_dict in tool_calls:
                                name         = tc_dict["function"]["name"]
                                arguments    = tc_dict["function"]["arguments"]
                                tool_call_id = tc_dict["id"]

                                if _LANGFUSE_ENABLED:
                                    tool_ctx = langfuse.start_as_current_observation(
                                        as_type="tool",
                                        name=name,
                                        input=json.loads(arguments),
                                    )
                                else:
                                    tool_ctx = nullcontext()

                                with tool_ctx as tool_obs:
                                    try:
                                        result = execute_tool(
                                            name=name,
                                            arguments=arguments,
                                            app_state=request.app.state,
                                        )
                                    except Exception as e:
                                        result = f"Error ejecutando {name}: {e}"
                                    if tool_obs is not None:
                                        tool_obs.update(output=result)

                                messages.append({
                                    "role":         "tool",
                                    "tool_call_id": tool_call_id,
                                    "content":      result,
                                })

                        else:
                            if agent_obs is not None:
                                agent_obs.update(output=full_content)
                            final_messages = [*req.messages, {"role": "assistant", "content": full_content}]
                            yield f"data: {json.dumps({'done': True, 'messages': final_messages})}\n\n"
                            return

                    yield f"data: {json.dumps({'error': 'El agente no pudo completar la respuesta'})}\n\n"

        except BadRequestError as e:
            yield f"data: {json.dumps({'error': f'Error en la solicitud al modelo: {e}'})}\n\n"
        except APIStatusError as e:
            yield f"data: {json.dumps({'error': f'Error del servicio de IA: {e.status_code}'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Error inesperado: {e}'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
