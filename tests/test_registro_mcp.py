import os
import sys
import tempfile
import unittest
from pathlib import Path


RAIZ = Path(__file__).parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from anfitrion_mcp import ClienteMCP, RegistroMCP


class PruebasRegistroMCP(unittest.TestCase):
    def test_guarda_solicitudes_notificaciones_y_respuestas(self) -> None:
        entorno = os.environ.copy()
        entorno["PYTHONPATH"] = str(RAIZ / "src")
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "sesion.jsonl"
            registro = RegistroMCP(ruta)
            cliente = ClienteMCP(
                [sys.executable, "-m", "servidor_mcp"],
                directorio=RAIZ,
                entorno=entorno,
                registro=registro,
            )
            self.addCleanup(cliente.cerrar)

            cliente.iniciar()
            cliente.listar_herramientas()
            entradas = registro.leer()

            self.assertEqual(len(entradas), 5)
            self.assertEqual(
                [entrada["direccion"] for entrada in entradas],
                [
                    "cliente_a_servidor",
                    "servidor_a_cliente",
                    "cliente_a_servidor",
                    "cliente_a_servidor",
                    "servidor_a_cliente",
                ],
            )
            self.assertEqual(entradas[0]["mensaje"]["method"], "initialize")
            self.assertEqual(
                entradas[2]["mensaje"]["method"], "notifications/initialized"
            )
            self.assertEqual(entradas[3]["mensaje"]["method"], "tools/list")
            self.assertIn("fecha", entradas[4])

    def test_registro_inexistente_devuelve_lista_vacia(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            registro = RegistroMCP(Path(temporal) / "inexistente.jsonl")
            self.assertEqual(registro.leer(), [])


if __name__ == "__main__":
    unittest.main()
