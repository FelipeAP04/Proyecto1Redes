import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from servidor_mcp.dominio import ServidorAsistenteBI


class PruebasDominio(unittest.TestCase):
    def setUp(self) -> None:
        self.servidor = ServidorAsistenteBI()
        self.enviar(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "prueba", "version": "1.0"},
                },
            }
        )
        self.enviar({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def enviar(self, mensaje: dict) -> dict | None:
        return self.servidor.procesar_linea(json.dumps(mensaje))

    def invocar(self, nombre: str, argumentos: dict) -> dict:
        return self.enviar(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": nombre, "arguments": argumentos},
            }
        )["result"]

    def test_publica_tres_herramientas(self) -> None:
        respuesta = self.enviar(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        nombres = {herramienta["name"] for herramienta in respuesta["result"]["tools"]}
        self.assertEqual(
            nombres,
            {"analizar_modelo_datos", "recomendar_dashboard", "revisar_consulta_sql"},
        )

    def test_analiza_modelo_y_relaciones(self) -> None:
        resultado = self.invocar(
            "analizar_modelo_datos",
            {
                "tablas": [
                    {
                        "nombre": "ventas",
                        "columnas": [
                            {"nombre": "id", "tipo": "entero", "clave": "primaria"},
                            {"nombre": "total", "tipo": "decimal", "rol": "medida"},
                            {
                                "nombre": "cliente_id",
                                "tipo": "entero",
                                "clave": "foranea",
                                "referencia": "clientes.id",
                            },
                        ],
                    },
                    {
                        "nombre": "clientes",
                        "columnas": [
                            {"nombre": "id", "tipo": "entero", "clave": "primaria"},
                            {"nombre": "segmento", "tipo": "texto", "rol": "dimension"},
                        ],
                    },
                ]
            },
        )
        contenido = resultado["structuredContent"]
        self.assertEqual(contenido["tablas_de_hechos"], ["ventas"])
        self.assertEqual(contenido["dimensiones"], ["clientes"])
        self.assertEqual(contenido["relaciones_declaradas"][0]["destino"], "clientes.id")

    def test_recomienda_linea_barras_y_kpi(self) -> None:
        resultado = self.invocar(
            "recomendar_dashboard",
            {
                "objetivo": "Monitorear ventas por región",
                "campos": [
                    {"nombre": "ventas", "tipo": "decimal", "rol": "medida"},
                    {"nombre": "fecha", "tipo": "date", "rol": "fecha"},
                    {"nombre": "region", "tipo": "texto", "rol": "dimension"},
                ],
            },
        )["structuredContent"]
        tipos = {grafico["tipo"] for grafico in resultado["visualizaciones"]}
        self.assertEqual(resultado["kpis"][0]["calculo"], "SUM(ventas)")
        self.assertIn("gráfico de líneas", tipos)
        self.assertIn("gráfico de barras", tipos)

    def test_revisa_sql_sin_permitir_escrituras(self) -> None:
        resultado = self.invocar(
            "revisar_consulta_sql",
            {"consulta": "select * from ventas where total > 0", "dialecto": "PostgreSQL"},
        )["structuredContent"]
        self.assertIn("\nFROM ", resultado["consulta_refactorizada"])
        self.assertTrue(any("SELECT *" in item for item in resultado["hallazgos"]))

        error = self.invocar(
            "revisar_consulta_sql", {"consulta": "DELETE FROM ventas"}
        )
        self.assertTrue(error["isError"])

    def test_lista_y_lee_recursos(self) -> None:
        lista = self.enviar(
            {"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}}
        )
        self.assertEqual(len(lista["result"]["resources"]), 3)

        lectura = self.enviar(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "resources/read",
                "params": {"uri": "bi://conocimiento/sql"},
            }
        )
        self.assertIn("Buenas prácticas de SQL", lectura["result"]["contents"][0]["text"])

    def test_rechaza_valores_fuera_de_los_esquemas(self) -> None:
        modelo = self.invocar(
            "analizar_modelo_datos",
            {
                "tablas": [
                    {
                        "nombre": "ventas",
                        "columnas": [
                            {"nombre": "total", "tipo": "decimal", "rol": "desconocido"}
                        ],
                    }
                ]
            },
        )
        self.assertTrue(modelo["isError"])

        dashboard = self.invocar(
            "recomendar_dashboard",
            {
                "objetivo": "Comparar las ventas",
                "campos": [
                    {"nombre": "region", "tipo": "texto", "cardinalidad": 0}
                ],
            },
        )
        self.assertTrue(dashboard["isError"])


if __name__ == "__main__":
    unittest.main()
