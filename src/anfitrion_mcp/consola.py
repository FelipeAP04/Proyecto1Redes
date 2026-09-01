"""Interfaz de consola para utilizar las herramientas del servidor MCP de BI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from .cliente import ClienteMCP, ErrorClienteMCP
from .registro import RegistroMCP


class AnfitrionConsola:
    """Presenta un menú sencillo sobre las operaciones del cliente MCP."""

    def __init__(
        self,
        cliente: ClienteMCP,
        registro: RegistroMCP,
        leer: Callable[[str], str] = input,
        escribir: Callable[[str], None] = print,
    ) -> None:
        self._cliente = cliente
        self._registro = registro
        self._leer = leer
        self._escribir = escribir

    def ejecutar(self) -> None:
        opciones: dict[str, Callable[[], None]] = {
            "1": self._analizar_modelo,
            "2": self._recomendar_dashboard,
            "3": self._revisar_sql,
            "4": self._consultar_recursos,
            "5": self._mostrar_registro,
        }
        while True:
            self._mostrar_menu()
            opcion = self._leer("Seleccione una opción: ").strip()
            if opcion == "6":
                self._escribir("Sesión finalizada.")
                return
            accion = opciones.get(opcion)
            if accion is None:
                self._escribir("Opción inválida. Ingrese un número del 1 al 6.")
                continue
            try:
                accion()
            except (ErrorClienteMCP, OSError, ValueError) as error:
                self._escribir(f"Error: {error}")

    def _mostrar_menu(self) -> None:
        self._escribir(
            "\n=== Anfitrión MCP para Business Intelligence ===\n"
            "1. Analizar diccionario de datos\n"
            "2. Recomendar dashboard\n"
            "3. Revisar consulta SQL\n"
            "4. Consultar recursos técnicos\n"
            "5. Mostrar log MCP\n"
            "6. Salir"
        )

    def _analizar_modelo(self) -> None:
        ruta = self._leer("Ruta del diccionario JSON: ").strip()
        datos = self._leer_json(Path(ruta))
        if isinstance(datos, list):
            argumentos = {"tablas": datos}
        elif isinstance(datos, dict) and isinstance(datos.get("tablas"), list):
            argumentos = datos
        else:
            raise ValueError("El archivo debe ser un arreglo o contener la propiedad 'tablas'.")
        resultado = self._cliente.invocar_herramienta(
            "analizar_modelo_datos", argumentos
        )
        self._mostrar_resultado(resultado)

    def _recomendar_dashboard(self) -> None:
        objetivo = self._leer("Objetivo del dashboard: ").strip()
        ruta = self._leer("Ruta del archivo JSON con los campos: ").strip()
        datos = self._leer_json(Path(ruta))
        if isinstance(datos, list):
            campos = datos
        elif isinstance(datos, dict) and isinstance(datos.get("campos"), list):
            campos = datos["campos"]
        else:
            raise ValueError("El archivo debe ser un arreglo o contener la propiedad 'campos'.")
        resultado = self._cliente.invocar_herramienta(
            "recomendar_dashboard", {"objetivo": objetivo, "campos": campos}
        )
        self._mostrar_resultado(resultado)

    def _revisar_sql(self) -> None:
        consulta = self._leer("Consulta SELECT o WITH: ").strip()
        dialecto = self._leer("Dialecto SQL (opcional): ").strip()
        argumentos = {"consulta": consulta}
        if dialecto:
            argumentos["dialecto"] = dialecto
        resultado = self._cliente.invocar_herramienta(
            "revisar_consulta_sql", argumentos
        )
        self._mostrar_resultado(resultado)

    def _consultar_recursos(self) -> None:
        recursos = self._cliente.listar_recursos()
        if not recursos:
            self._escribir("El servidor no publicó recursos.")
            return
        self._escribir("\nRecursos disponibles:")
        for indice, recurso in enumerate(recursos, start=1):
            self._escribir(f"{indice}. {recurso.get('name')} ({recurso.get('uri')})")
        seleccion = self._leer("Número del recurso que desea leer: ").strip()
        if not seleccion.isdigit() or not 1 <= int(seleccion) <= len(recursos):
            raise ValueError("La selección del recurso no es válida.")
        uri = recursos[int(seleccion) - 1].get("uri")
        if not isinstance(uri, str):
            raise ValueError("El recurso seleccionado no contiene una URI válida.")
        contenidos = self._cliente.leer_recurso(uri)
        for contenido in contenidos:
            texto = contenido.get("text")
            if isinstance(texto, str):
                self._escribir(f"\n{texto}")

    def _mostrar_registro(self) -> None:
        entradas = self._registro.leer()
        if not entradas:
            self._escribir("Todavía no existen mensajes en el registro MCP.")
            return
        self._escribir(json.dumps(entradas, ensure_ascii=False, indent=2))

    def _mostrar_resultado(self, resultado: dict[str, Any]) -> None:
        if resultado.get("isError"):
            contenidos = resultado.get("content", [])
            texto = contenidos[0].get("text") if contenidos else "Error desconocido"
            self._escribir(f"La herramienta reportó un error: {texto}")
            return
        contenido = resultado.get("structuredContent", resultado)
        self._escribir(json.dumps(contenido, ensure_ascii=False, indent=2))

    @staticmethod
    def _leer_json(ruta: Path) -> Any:
        try:
            with ruta.open(encoding="utf-8") as archivo:
                return json.load(archivo)
        except json.JSONDecodeError as error:
            raise ValueError(f"El archivo {ruta} no contiene JSON válido.") from error


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Anfitrión de consola para el servidor MCP de Business Intelligence."
    )
    parser.add_argument(
        "--registro",
        type=Path,
        default=Path("logs/sesion_mcp.jsonl"),
        help="Archivo JSONL donde se guardará la comunicación MCP.",
    )
    argumentos = parser.parse_args()

    entorno = os.environ.copy()
    registro = RegistroMCP(argumentos.registro)
    cliente = ClienteMCP(
        [sys.executable, "-m", "servidor_mcp"],
        directorio=Path.cwd(),
        entorno=entorno,
        registro=registro,
    )
    try:
        inicio = cliente.iniciar()
        servidor = inicio.get("serverInfo", {})
        print(
            f"Conectado a {servidor.get('title', servidor.get('name', 'servidor MCP'))} "
            f"con protocolo {inicio.get('protocolVersion')}."
        )
        AnfitrionConsola(cliente, registro).ejecutar()
    except (ErrorClienteMCP, OSError, ValueError) as error:
        print(f"No fue posible ejecutar el anfitrión: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except (KeyboardInterrupt, EOFError):
        print("\nSesión finalizada por el usuario.")
    finally:
        cliente.cerrar()
