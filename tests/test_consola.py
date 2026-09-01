import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


RAIZ = Path(__file__).parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from anfitrion_mcp.consola import AnfitrionConsola
from anfitrion_mcp.registro import RegistroMCP


class ClienteSimulado:
    def __init__(self) -> None:
        self.invocaciones: list[tuple[str, dict[str, Any]]] = []

    def invocar_herramienta(
        self, nombre: str, argumentos: dict[str, Any]
    ) -> dict[str, Any]:
        self.invocaciones.append((nombre, argumentos))
        return {
            "isError": False,
            "structuredContent": {"herramienta": nombre, "ok": True},
        }

    @staticmethod
    def listar_recursos() -> list[dict[str, Any]]:
        return [{"name": "Guía SQL", "uri": "bi://conocimiento/sql"}]

    @staticmethod
    def leer_recurso(_uri: str) -> list[dict[str, Any]]:
        return [{"text": "Contenido de prueba"}]


class PruebasConsola(unittest.TestCase):
    def ejecutar_menu(self, respuestas: list[str], registro: RegistroMCP):
        cliente = ClienteSimulado()
        salidas: list[str] = []
        iterador = iter(respuestas)
        consola = AnfitrionConsola(
            cliente,  # type: ignore[arg-type]
            registro,
            leer=lambda _mensaje: next(iterador),
            escribir=salidas.append,
        )
        consola.ejecutar()
        return cliente, salidas

    def test_recomienda_dashboard_desde_archivo(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "campos.json"
            ruta.write_text(
                json.dumps(
                    [
                        {"nombre": "ventas", "tipo": "decimal", "rol": "medida"},
                        {"nombre": "region", "tipo": "texto", "rol": "dimension"},
                    ]
                ),
                encoding="utf-8",
            )
            registro = RegistroMCP(Path(temporal) / "registro.jsonl")
            cliente, salidas = self.ejecutar_menu(
                ["2", "Comparar ventas por región", str(ruta), "6"], registro
            )

            nombre, argumentos = cliente.invocaciones[0]
            self.assertEqual(nombre, "recomendar_dashboard")
            self.assertEqual(argumentos["campos"][0]["nombre"], "ventas")
            self.assertTrue(any('"ok": true' in salida for salida in salidas))

    def test_consulta_recurso_y_muestra_registro(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            registro = RegistroMCP(Path(temporal) / "registro.jsonl")
            registro.guardar(
                "cliente_a_servidor",
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            )
            _cliente, salidas = self.ejecutar_menu(
                ["4", "1", "5", "6"], registro
            )

            self.assertTrue(any("Contenido de prueba" in salida for salida in salidas))
            self.assertTrue(any("tools/list" in salida for salida in salidas))

    def test_informa_opcion_y_archivo_invalidos(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            registro = RegistroMCP(Path(temporal) / "registro.jsonl")
            _cliente, salidas = self.ejecutar_menu(
                ["9", "1", str(Path(temporal) / "no-existe.json"), "6"],
                registro,
            )

            self.assertTrue(any("Opción inválida" in salida for salida in salidas))
            self.assertTrue(any("Error:" in salida for salida in salidas))


if __name__ == "__main__":
    unittest.main()
