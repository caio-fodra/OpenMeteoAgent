import json
import logging
import os
from typing import Any

from openai import OpenAI

from tool import get_daily_forecast

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

ERROR_MESSAGE = (
    "Não consegui processar sua solicitação. Informe latitude, longitude e um período, "
    "por exemplo: lat -23.55 lon -46.63 próximos 3 dias."
)

SYSTEM_PROMPT = """
Você é um assistente de previsão do tempo.

Workflow obrigatório:
1. Entenda o pedido do usuário.
2. Se houver latitude, longitude e período suficientes, chame a tool get_daily_forecast.
3. Depois de receber a resposta da tool, responda em português do Brasil.

Formato obrigatório da resposta final após a tool:
- Para cada dia, mostre explicitamente os campos:
  - temperature_2m_max
  - temperature_2m_min
  - precipitation_sum
- Em cada campo, inclua o valor e a unidade correspondente.
- Inclua também a data de cada previsão.
- Não resuma, não renomeie e não omita esses rótulos.

Regras:
- O parâmetro days_ahead deve ser um inteiro entre 1 e 16.
- Chame a tool usando apenas JSON válido com as chaves: lat, lon, days_ahead.
- Não exponha JSON, tool_calls nem detalhes internos ao usuário final.
- Se faltarem dados para chamar a tool, peça os campos ausentes de forma objetiva.
""".strip()

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_daily_forecast",
            "description": "Busca previsão diária para uma latitude e longitude.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude entre -90 e 90."},
                    "lon": {"type": "number", "description": "Longitude entre -180 e 180."},
                    "days_ahead": {
                        "type": "integer",
                        "description": "Quantidade de dias de previsão, entre 1 e 16.",
                    },
                },
                "required": ["lat", "lon", "days_ahead"],
                "additionalProperties": False,
            },
        },
    }
]

CLIENT = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
)
MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")


def _normalize_arguments(arguments: Any) -> str:
    if isinstance(arguments, str):
        return arguments
    if isinstance(arguments, dict):
        return json.dumps(arguments, ensure_ascii=False)
    raise TypeError("Os argumentos da tool call precisam ser string JSON ou dict.")


def _normalize_tool_calls(message: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for index, tool_call in enumerate(getattr(message, "tool_calls", None) or [], start=1):
        function = getattr(tool_call, "function", None)
        if function is None:
            continue

        normalized.append(
            {
                "id": getattr(tool_call, "id", None) or f"call_{index}",
                "type": "function",
                "function": {
                    "name": getattr(function, "name", ""),
                    "arguments": _normalize_arguments(getattr(function, "arguments", "{}")),
                },
            }
        )

    return normalized


def _assistant_tool_message(message: Any, tool_calls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    assistant_message: dict[str, Any] = {
        "role": "assistant",
        "tool_calls": tool_calls if tool_calls is not None else _normalize_tool_calls(message),
    }

    content = getattr(message, "content", None)
    if content is not None:
        assistant_message["content"] = content

    return assistant_message


def _execute_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tool_messages: list[dict[str, Any]] = []

    for tool_call in tool_calls:
        function = tool_call.get("function") or {}
        if function.get("name") != "get_daily_forecast":
            continue

        try:
            arguments = json.loads(function.get("arguments", "{}"))
            result = {
                "ok": True,
                "data": get_daily_forecast(
                    lat=arguments["lat"],
                    lon=arguments["lon"],
                    days_ahead=arguments["days_ahead"],
                ),
            }
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Falha ao executar tool call: %s", exc)
            result = {"ok": False, "error": str(exc)}
        except Exception as exc:
            logger.exception("Falha inesperada ao consultar a tool: %s", exc)
            result = {"ok": False, "error": "Não foi possível consultar a previsão do tempo."}

        tool_messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "content": json.dumps(result, ensure_ascii=False),
            }
        )

    return tool_messages


def run_weather_chat(message: str, history: list[tuple[str, str]] | None = None) -> str:
    base_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]

    try:
        first_response = CLIENT.chat.completions.create(
            model=MODEL,
            messages=base_messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0,
        )
        first_message = first_response.choices[0].message
    except Exception as exc:
        logger.exception("Falha na primeira chamada ao modelo: %s", exc)
        return "Não foi possível processar sua solicitação no momento. Tente novamente em instantes."

    if not getattr(first_message, "tool_calls", None):
        return (first_message.content or "").strip() or ERROR_MESSAGE

    normalized_tool_calls = _normalize_tool_calls(first_message)
    if not normalized_tool_calls:
        logger.warning("O modelo retornou tool_calls, mas não foi possível normalizá-los.")
        return ERROR_MESSAGE

    tool_messages = _execute_tool_calls(normalized_tool_calls)
    if not tool_messages:
        return ERROR_MESSAGE

    try:
        final_response = CLIENT.chat.completions.create(
            model=MODEL,
            messages=base_messages + [_assistant_tool_message(first_message, normalized_tool_calls), *tool_messages],
            tools=TOOLS,
            tool_choice="none",
            temperature=0,
        )
    except Exception as exc:
        logger.exception("Falha na segunda chamada ao modelo: %s", exc)
        return "Não foi possível concluir a resposta no momento. Tente novamente em instantes."

    return (final_response.choices[0].message.content or "").strip() or ERROR_MESSAGE
