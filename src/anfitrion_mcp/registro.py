"""Registro persistente de mensajes intercambiados con servidores MCP."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RegistroMCP:
    """Guarda cada mensaje MCP como una entrada JSON Lines."""

    def __init__(self, ruta: Path) -> None:
        self.ruta = ruta

    def guardar(self, direccion: str, mensaje: dict[str, Any]) -> None:
        if direccion not in {"cliente_a_servidor", "servidor_a_cliente"}:
            raise ValueError("La dirección del mensaje MCP no es válida.")
        entrada = {
            "fecha": datetime.now(timezone.utc).isoformat(),
            "direccion": direccion,
            "mensaje": mensaje,
        }
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self.ruta.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(entrada, ensure_ascii=False, separators=(",", ":")))
            archivo.write("\n")

    def leer(self) -> list[dict[str, Any]]:
        if not self.ruta.exists():
            return []
        entradas: list[dict[str, Any]] = []
        with self.ruta.open(encoding="utf-8") as archivo:
            for numero, linea in enumerate(archivo, start=1):
                try:
                    entrada = json.loads(linea)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"La línea {numero} del registro MCP no contiene JSON válido."
                    ) from error
                if not isinstance(entrada, dict):
                    raise ValueError(f"La línea {numero} del registro MCP no es un objeto.")
                entradas.append(entrada)
        return entradas
