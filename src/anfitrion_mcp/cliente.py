"""Cliente MCP manual para comunicación JSON-RPC con un subproceso local."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from servidor_mcp.protocolo import VERSION_PROTOCOLO


class ErrorClienteMCP(Exception):
    """Error de transporte o protocolo detectado por el anfitrión."""


class ClienteMCP:
    """Administra una sesión MCP secuencial sobre stdin y stdout."""

    def __init__(
        self,
        comando: list[str],
        directorio: Path | None = None,
        version_protocolo: str = VERSION_PROTOCOLO,
        entorno: dict[str, str] | None = None,
    ) -> None:
        if not comando:
            raise ValueError("El comando del servidor no puede estar vacío.")
        self._comando = comando
        self._directorio = directorio
        self._version_protocolo = version_protocolo
        self._entorno = entorno or os.environ.copy()
        self._proceso: subprocess.Popen[str] | None = None
        self._siguiente_id = 1
        self.informacion_servidor: dict[str, Any] | None = None

    def iniciar(self) -> dict[str, Any]:
        """Inicia el servidor y completa el ciclo de inicialización MCP."""
        if self._proceso is not None:
            raise ErrorClienteMCP("La sesión MCP ya fue iniciada.")

        try:
            self._proceso = subprocess.Popen(
                self._comando,
                cwd=self._directorio,
                env=self._entorno,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
        except OSError as error:
            raise ErrorClienteMCP(f"No se pudo iniciar el servidor MCP: {error}") from error

        try:
            resultado = self.solicitar(
                "initialize",
                {
                    "protocolVersion": self._version_protocolo,
                    "capabilities": {},
                    "clientInfo": {
                        "name": "anfitrion-bi-consola",
                        "title": "Anfitrión de consola para Business Intelligence",
                        "version": "0.1.0",
                    },
                },
            )
            version_servidor = resultado.get("protocolVersion")
            if not isinstance(version_servidor, str):
                raise ErrorClienteMCP("El servidor no devolvió una versión MCP válida.")

            self.notificar("notifications/initialized")
            self.informacion_servidor = resultado
            return resultado
        except Exception:
            self.cerrar()
            raise

    def solicitar(
        self, metodo: str, parametros: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Envía una solicitud JSON-RPC y espera su respuesta correlacionada."""
        identificador = self._siguiente_id
        self._siguiente_id += 1
        mensaje: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": identificador,
            "method": metodo,
            "params": parametros or {},
        }
        self._escribir(mensaje)

        proceso = self._obtener_proceso()
        assert proceso.stdout is not None
        linea = proceso.stdout.readline()
        if not linea:
            detalle = self._leer_error_del_proceso()
            mensaje_error = "El servidor MCP cerró stdout sin responder."
            if detalle:
                mensaje_error += f" Detalle: {detalle}"
            raise ErrorClienteMCP(mensaje_error)

        try:
            respuesta = json.loads(linea)
        except json.JSONDecodeError as error:
            raise ErrorClienteMCP("El servidor produjo una respuesta JSON inválida.") from error

        if not isinstance(respuesta, dict) or respuesta.get("jsonrpc") != "2.0":
            raise ErrorClienteMCP("La respuesta no cumple JSON-RPC 2.0.")
        if respuesta.get("id") != identificador:
            raise ErrorClienteMCP("La respuesta no corresponde a la solicitud enviada.")
        if "error" in respuesta:
            error = respuesta["error"]
            if isinstance(error, dict):
                raise ErrorClienteMCP(
                    f"Error JSON-RPC {error.get('code')}: {error.get('message')}"
                )
            raise ErrorClienteMCP("El servidor devolvió un error JSON-RPC inválido.")
        if not isinstance(respuesta.get("result"), dict):
            raise ErrorClienteMCP("La respuesta no contiene un resultado válido.")
        return respuesta["result"]

    def notificar(
        self, metodo: str, parametros: dict[str, Any] | None = None
    ) -> None:
        """Envía una notificación JSON-RPC que no espera respuesta."""
        self._escribir(
            {
                "jsonrpc": "2.0",
                "method": metodo,
                "params": parametros or {},
            }
        )

    def listar_herramientas(self) -> list[dict[str, Any]]:
        resultado = self.solicitar("tools/list")
        herramientas = resultado.get("tools")
        if not isinstance(herramientas, list):
            raise ErrorClienteMCP("El servidor devolvió una lista de herramientas inválida.")
        return herramientas

    def invocar_herramienta(
        self, nombre: str, argumentos: dict[str, Any]
    ) -> dict[str, Any]:
        return self.solicitar(
            "tools/call", {"name": nombre, "arguments": argumentos}
        )

    def listar_recursos(self) -> list[dict[str, Any]]:
        resultado = self.solicitar("resources/list")
        recursos = resultado.get("resources")
        if not isinstance(recursos, list):
            raise ErrorClienteMCP("El servidor devolvió una lista de recursos inválida.")
        return recursos

    def leer_recurso(self, uri: str) -> list[dict[str, Any]]:
        resultado = self.solicitar("resources/read", {"uri": uri})
        contenidos = resultado.get("contents")
        if not isinstance(contenidos, list):
            raise ErrorClienteMCP("El servidor devolvió contenido de recurso inválido.")
        return contenidos

    def cerrar(self) -> None:
        """Cierra stdin y termina el subproceso según el ciclo de vida MCP."""
        proceso = self._proceso
        if proceso is None:
            return

        if proceso.stdin is not None and not proceso.stdin.closed:
            proceso.stdin.close()
        try:
            proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proceso.terminate()
            try:
                proceso.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait(timeout=2)

        if proceso.stdout is not None:
            proceso.stdout.close()
        if proceso.stderr is not None:
            proceso.stderr.close()
        self._proceso = None

    def __enter__(self) -> ClienteMCP:
        self.iniciar()
        return self

    def __exit__(self, _tipo: object, _valor: object, _traza: object) -> None:
        self.cerrar()

    def _escribir(self, mensaje: dict[str, Any]) -> None:
        proceso = self._obtener_proceso()
        assert proceso.stdin is not None
        try:
            proceso.stdin.write(
                json.dumps(mensaje, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
            proceso.stdin.flush()
        except (BrokenPipeError, OSError) as error:
            raise ErrorClienteMCP("No se pudo escribir al servidor MCP.") from error

    def _obtener_proceso(self) -> subprocess.Popen[str]:
        if self._proceso is None:
            raise ErrorClienteMCP("La sesión MCP no está iniciada.")
        return self._proceso

    def _leer_error_del_proceso(self) -> str:
        proceso = self._obtener_proceso()
        if proceso.poll() is None or proceso.stderr is None:
            return ""
        return proceso.stderr.read().strip()
