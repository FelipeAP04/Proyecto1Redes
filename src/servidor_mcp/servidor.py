"""Punto de entrada del servidor MCP que utiliza el transporte stdio."""

from __future__ import annotations

import json
import sys

from .dominio import ServidorAsistenteBI


def ejecutar() -> None:
    """Lee un mensaje JSON-RPC por línea y escribe las respuestas en stdout."""
    servidor = ServidorAsistenteBI()
    for linea in sys.stdin:
        if not linea.strip():
            continue
        respuesta = servidor.procesar_linea(linea)
        if respuesta is not None:
            print(json.dumps(respuesta, ensure_ascii=False, separators=(",", ":")), flush=True)


def main() -> None:
    try:
        ejecutar()
    except KeyboardInterrupt:
        # stderr puede utilizarse para diagnóstico sin contaminar el canal JSON-RPC.
        print("Servidor detenido por el usuario.", file=sys.stderr)


if __name__ == "__main__":
    main()
