# servidor_tiendanova.py — Servidor MCP con las herramientas de TiendaNova

import ast
import json
import operator
import sqlite3
import urllib.request

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

servidor = MCPServer("tiendanova")

_OPERADORES = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _evaluar(nodo):
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, (int, float)):
        return nodo.value

    if isinstance(nodo, ast.BinOp) and type(nodo.op) in _OPERADORES:
        operacion = _OPERADORES[type(nodo.op)]
        return operacion(_evaluar(nodo.left), _evaluar(nodo.right))

    if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in _OPERADORES:
        operacion = _OPERADORES[type(nodo.op)]
        return operacion(_evaluar(nodo.operand))

    raise ToolError(
        "Expresión no permitida: solo números, paréntesis y + - * / **"
    )


@servidor.tool()
def calcular(expresion: str) -> str:
    """Evalúa una expresión aritmética (ej. '1349000 * 0.19').
    Solo admite números y + - * / ** y paréntesis.
    """
    try:
        arbol = ast.parse(expresion, mode="eval")
    except SyntaxError:
        raise ToolError(f"Expresión mal escrita: {expresion}")

    return str(_evaluar(arbol.body))


@servidor.tool()
def consultar_pedidos(sql: str) -> str:
    """Ejecuta una consulta SQL de solo lectura sobre la base de datos de TiendaNova.

    Tablas: clientes(id, nombre, ciudad) y
    pedidos(id, cliente_id, fecha, estado, total_cop, nota).

    Estados posibles:
    'En preparación', 'Enviado', 'Entregado', 'Cancelado'.
    """
    con = sqlite3.connect("file:tiendanova.db?mode=ro", uri=True)

    try:
        cursor = con.execute(sql)
        columnas = [c[0] for c in cursor.description]
        filas = [dict(zip(columnas, f)) for f in cursor.fetchall()]
        return json.dumps(filas, ensure_ascii=False)

    except sqlite3.Error as e:
        raise ToolError(f"Error de SQL: {e}")

    finally:
        con.close()


@servidor.tool()
def tasa_de_cambio(moneda: str) -> str:
    """Devuelve cuántos pesos colombianos (COP) equivalen a 1 unidad de la moneda indicada
    (código ISO, ej. 'USD', 'EUR').
    """
    with urllib.request.urlopen(
        f"https://open.er-api.com/v6/latest/{moneda.upper()}",
        timeout=10,
    ) as r:
        datos = json.load(r)

    return (
        f"1 {moneda.upper()} = {datos['rates']['COP']} COP "
        f"(actualizado: {datos['time_last_update_utc']})"
    )


if __name__ == "__main__":
    servidor.run()