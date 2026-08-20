import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from servidor_mcp.protocolo import ServidorJSONRPC, VERSION_PROTOCOLO


class PruebasProtocolo(unittest.TestCase):
    def setUp(self) -> None:
        self.servidor = ServidorJSONRPC()

    def enviar(self, mensaje: dict) -> dict | None:
        return self.servidor.procesar_linea(json.dumps(mensaje))

    def test_negocia_inicializacion(self) -> None:
        respuesta = self.enviar(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": VERSION_PROTOCOLO,
                    "capabilities": {},
                    "clientInfo": {"name": "prueba", "version": "1.0"},
                },
            }
        )

        self.assertEqual(respuesta["result"]["protocolVersion"], VERSION_PROTOCOLO)
        self.assertEqual(respuesta["id"], 1)

    def test_rechaza_operacion_antes_de_initialized(self) -> None:
        self.servidor.registrar("ejemplo", lambda _parametros: {"ok": True})
        respuesta = self.enviar(
            {"jsonrpc": "2.0", "id": 2, "method": "ejemplo", "params": {}}
        )
        self.assertEqual(respuesta["error"]["code"], -32002)

    def test_notificacion_no_genera_respuesta(self) -> None:
        respuesta = self.enviar(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        self.assertIsNone(respuesta)

    def test_reporta_json_mal_formado(self) -> None:
        respuesta = self.servidor.procesar_linea("{sin-json")
        self.assertEqual(respuesta["error"]["code"], -32700)
        self.assertIsNone(respuesta["id"])

    def test_responde_ping(self) -> None:
        respuesta = self.enviar({"jsonrpc": "2.0", "id": 3, "method": "ping"})
        self.assertEqual(respuesta["result"], {})

    def test_valida_identificador_y_parametros_de_inicio(self) -> None:
        identificador_invalido = self.enviar(
            {"jsonrpc": "2.0", "id": {"valor": 1}, "method": "ping"}
        )
        self.assertEqual(identificador_invalido["error"]["code"], -32600)

        inicio_invalido = self.enviar(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "initialize",
                "params": {
                    "protocolVersion": 2025,
                    "capabilities": {},
                    "clientInfo": {},
                },
            }
        )
        self.assertEqual(inicio_invalido["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
