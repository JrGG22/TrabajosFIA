# explorar_servidor.py — Cliente MCP mínimo: descubrir y llamar herramientas
# sin ningún LLM

import asyncio
import sys

from mcp import Client, StdioServerParameters


async def main():
    servidor = StdioServerParameters(
        command=sys.executable,
        args=["servidor_tiendanova.py"],
    )

    async with Client(servidor) as mcp:
        for h in (await mcp.list_tools()).tools:
            print(f"- {h.name}: {h.description.splitlines()[0]}")
            print(f" parámetros: {h.input_schema['properties']}")
            print()

        for nombre, args in [
            ("calcular", {"expresion": "(98500 + 1349000) * 0.19"}),
            (
                "consultar_pedidos",
                {
                    "sql": "SELECT id, estado, total_cop FROM pedidos "
                    "WHERE cliente_id = 'C-102'"
                },
            ),
            (
                "consultar_pedidos",
                {
                    "sql": "DELETE FROM pedidos WHERE estado = 'Cancelado'"
                },
            ),
            (
                "calcular",
                {
                    "expresion": "__import__('os').remove('tiendanova.db')"
                },
            ),
        ]:
            r = await mcp.call_tool(nombre, args)

            print(
                f"{nombre}({args})\n"
                f" -> {'ERROR ' if r.is_error else ''}"
                f"{r.content[0].text}"
            )

asyncio.run(main())