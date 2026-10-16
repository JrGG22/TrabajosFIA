# agente_mcp.py — Cliente MCP + agente con tool calling

import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from mcp import Client, StdioServerParameters
from openai import OpenAI

load_dotenv()

# Proveedor del LLM: cualquiera compatible con el SDK de OpenAI y con soporte
# de tool calling.
#
# DeepSeek:
#   DEEPSEEK_API_KEY
#   base_url="https://api.deepseek.com"
#   MODEL="deepseek-flash"
#
# OpenRouter:
#   OPENROUTER_API_KEY
#   base_url="https://openrouter.ai/api/v1"
#   MODEL="anthropic/claude-sonnet-5"

llm = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

MODEL = "deepseek-flash"
MAX_PASOS = 8

SISTEMA = (
    "Eres el asistente interno de operaciones de TiendaNova. "
    "Usa las herramientas disponibles para consultar datos y hacer cálculos; "
    "no inventes cifras ni hagas aritmética de memoria. "
    "Responde en español, en máximo 3 oraciones."
)


def a_formato_openai(herramienta_mcp):
    """Traduce la descripción de una herramienta MCP al formato de tool calling de OpenAI."""
    return {
        "type": "function",
        "function": {
            "name": herramienta_mcp.name,
            "description": herramienta_mcp.description,
            "parameters": herramienta_mcp.input_schema,
        },
    }


async def ejecutar_agente(pregunta):
    servidor = StdioServerParameters(
        command=sys.executable,
        args=["servidor_tiendanova.py"],
    )

    async with Client(servidor) as mcp:
        herramientas = [
            a_formato_openai(h)
            for h in (await mcp.list_tools()).tools
        ]

        print(
            "Herramientas descubiertas:",
            [h["function"]["name"] for h in herramientas],
        )

        mensajes = [
            {"role": "system", "content": SISTEMA},
            {"role": "user", "content": pregunta},
        ]

        for paso in range(1, MAX_PASOS + 1):
            r = llm.chat.completions.create(
                model=MODEL,
                messages=mensajes,
                tools=herramientas,
                temperature=0,
            )

            msg = r.choices[0].message

            # El modelo ya no pide herramientas: respuesta final
            if not msg.tool_calls:
                return msg.content

            mensajes.append(msg.model_dump(exclude_none=True))

            for llamada in msg.tool_calls:
                args = json.loads(llamada.function.arguments)

                resultado = await mcp.call_tool(
                    llamada.function.name,
                    args,
                )

                texto = resultado.content[0].text

                print(
                    f"  [paso {paso}] "
                    f"{llamada.function.name}({args})"
                )
                print(
                    f"    -> "
                    f"{'ERROR: ' if resultado.is_error else ''}"
                    f"{texto[:200]}"
                )

                mensajes.append(
                    {
                        "role": "tool",
                        "tool_call_id": llamada.id,
                        "content": texto,
                    }
                )

    return (
        f"[Se alcanzó el límite de {MAX_PASOS} pasos "
        "sin una respuesta final]"
    )


if __name__ == "__main__":
    respuesta = asyncio.run(
        ejecutar_agente(sys.argv[1])
    )
    print("\nRESPUESTA:", respuesta)