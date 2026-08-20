"""Implementación manual de JSON-RPC 2.0 y del ciclo de vida de MCP."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


VERSION_PROTOCOLO = "2025-06-18"


@dataclass
class ErrorRPC(Exception):
    """Error que se puede representar mediante el objeto error de JSON-RPC."""

    codigo: int
    mensaje: str
    datos: Any | None = None


Manejador = Callable[[dict[str, Any]], dict[str, Any]]


class ServidorJSONRPC:
    """Procesa mensajes MCP sin depender de un SDK del protocolo."""

    def __init__(self) -> None:
        self._inicio_respondido = False
        self._inicializado = False
        self._metodos: dict[str, Manejador] = {
            "initialize": self._inicializar,
            "ping": lambda _parametros: {},
        }

    def registrar(self, metodo: str, manejador: Manejador) -> None:
        """Registra un método disponible durante la fase de operación."""
        self._metodos[metodo] = manejador

    def procesar_linea(self, linea: str) -> dict[str, Any] | None:
        """Convierte una línea JSON en una respuesta o procesa su notificación."""
        try:
            mensaje = json.loads(linea)
        except json.JSONDecodeError as error:
            return self._respuesta_error(None, ErrorRPC(-32700, "Error de análisis JSON", str(error)))

        identificador = mensaje.get("id") if isinstance(mensaje, dict) else None
        try:
            self._validar_mensaje(mensaje)
            metodo = mensaje["method"]
            parametros = mensaje.get("params", {})

            if "id" not in mensaje:
                self._procesar_notificacion(metodo)
                return None

            if metodo != "initialize" and metodo != "ping" and not self._inicializado:
                raise ErrorRPC(-32002, "El servidor MCP todavía no ha sido inicializado")

            manejador = self._metodos.get(metodo)
            if manejador is None:
                raise ErrorRPC(-32601, f"Método no encontrado: {metodo}")

            return {
                "jsonrpc": "2.0",
                "id": identificador,
                "result": manejador(parametros),
            }
        except ErrorRPC as error:
            # Las notificaciones no reciben respuesta, incluso si contienen un error.
            if isinstance(mensaje, dict) and "id" not in mensaje:
                return None
            return self._respuesta_error(identificador, error)
        except Exception:
            return self._respuesta_error(
                identificador,
                ErrorRPC(-32603, "Error interno del servidor"),
            )

    @staticmethod
    def _validar_mensaje(mensaje: Any) -> None:
        if not isinstance(mensaje, dict):
            raise ErrorRPC(-32600, "Solicitud JSON-RPC inválida")
        if mensaje.get("jsonrpc") != "2.0" or not isinstance(mensaje.get("method"), str):
            raise ErrorRPC(-32600, "Solicitud JSON-RPC inválida")
        identificador = mensaje.get("id")
        if "id" in mensaje and (
            isinstance(identificador, bool)
            or not isinstance(identificador, (str, int, float, type(None)))
        ):
            raise ErrorRPC(-32600, "El identificador JSON-RPC no es válido")
        if "params" in mensaje and not isinstance(mensaje["params"], (dict, list)):
            raise ErrorRPC(-32602, "Los parámetros deben ser un objeto o un arreglo")

    def _procesar_notificacion(self, metodo: str) -> None:
        if metodo == "notifications/initialized" and self._inicio_respondido:
            self._inicializado = True

    def _inicializar(self, parametros: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(parametros, dict):
            raise ErrorRPC(-32602, "Los parámetros de initialize deben ser un objeto")

        campos_requeridos = ("protocolVersion", "capabilities", "clientInfo")
        if any(campo not in parametros for campo in campos_requeridos):
            raise ErrorRPC(-32602, "Faltan parámetros requeridos de initialize")
        if not isinstance(parametros["protocolVersion"], str):
            raise ErrorRPC(-32602, "protocolVersion debe ser un texto")
        if not isinstance(parametros["capabilities"], dict):
            raise ErrorRPC(-32602, "capabilities debe ser un objeto")
        if not isinstance(parametros["clientInfo"], dict):
            raise ErrorRPC(-32602, "clientInfo debe ser un objeto")

        self._inicio_respondido = True
        return {
            "protocolVersion": VERSION_PROTOCOLO,
            "capabilities": {},
            "serverInfo": {
                "name": "asistente-bi-mcp",
                "title": "Asistente de Modelado de Datos y Dashboards",
                "version": "0.1.0",
            },
            "instructions": (
                "Servidor local de apoyo para analizar modelos de datos y planificar dashboards."
            ),
        }

    @staticmethod
    def _respuesta_error(identificador: Any, error: ErrorRPC) -> dict[str, Any]:
        detalle: dict[str, Any] = {
            "code": error.codigo,
            "message": error.mensaje,
        }
        if error.datos is not None:
            detalle["data"] = error.datos
        return {"jsonrpc": "2.0", "id": identificador, "error": detalle}
