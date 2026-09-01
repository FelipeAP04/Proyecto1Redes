import os
import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from anfitrion_mcp import ClienteMCP, ErrorClienteMCP


class PruebasClienteMCP(unittest.TestCase):
    def crear_cliente(self) -> ClienteMCP:
        entorno_python = os.environ.copy()
        entorno_python["PYTHONPATH"] = str(RAIZ / "src")
        return ClienteMCP(
            [sys.executable, "-m", "servidor_mcp"],
            directorio=RAIZ,
            entorno=entorno_python,
        )

    def test_completa_ciclo_y_descubre_capacidades(self) -> None:
        cliente = self.crear_cliente()
        self.addCleanup(cliente.cerrar)

        inicio = cliente.iniciar()
        herramientas = cliente.listar_herramientas()
        recursos = cliente.listar_recursos()

        self.assertIn("tools", inicio["capabilities"])
        self.assertEqual(len(herramientas), 3)
        self.assertEqual(len(recursos), 3)

    def test_invoca_herramienta_y_lee_recurso(self) -> None:
        cliente = self.crear_cliente()
        self.addCleanup(cliente.cerrar)
        cliente.iniciar()

        resultado = cliente.invocar_herramienta(
            "recomendar_dashboard",
            {
                "objetivo": "Monitorear ventas por región",
                "campos": [
                    {"nombre": "ventas", "tipo": "decimal", "rol": "medida"},
                    {"nombre": "fecha", "tipo": "date", "rol": "fecha"},
                    {"nombre": "region", "tipo": "texto", "rol": "dimension"},
                ],
            },
        )
        recurso = cliente.leer_recurso("bi://conocimiento/visualizaciones")

        self.assertFalse(resultado["isError"])
        self.assertEqual(
            resultado["structuredContent"]["kpis"][0]["calculo"], "SUM(ventas)"
        )
        self.assertIn("Heurísticas para visualizaciones", recurso[0]["text"])

    def test_reporta_error_json_rpc(self) -> None:
        cliente = self.crear_cliente()
        self.addCleanup(cliente.cerrar)
        cliente.iniciar()

        with self.assertRaisesRegex(ErrorClienteMCP, "Herramienta desconocida"):
            cliente.invocar_herramienta("no_existe", {})

    def test_requiere_iniciar_la_sesion(self) -> None:
        cliente = self.crear_cliente()
        with self.assertRaisesRegex(ErrorClienteMCP, "no está iniciada"):
            cliente.listar_herramientas()


if __name__ == "__main__":
    unittest.main()
