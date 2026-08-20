import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).parents[1]


class PruebasIntegracionStdio(unittest.TestCase):
    def test_conversacion_con_el_proceso_real(self) -> None:
        entorno = os.environ.copy()
        entorno["PYTHONPATH"] = str(RAIZ / "src")
        proceso = subprocess.Popen(
            [sys.executable, "-m", "servidor_mcp"],
            cwd=RAIZ,
            env=entorno,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        def solicitar(mensaje: dict, espera_respuesta: bool = True) -> dict | None:
            proceso.stdin.write(json.dumps(mensaje) + "\n")
            proceso.stdin.flush()
            if espera_respuesta:
                return json.loads(proceso.stdout.readline())
            return None

        inicio = solicitar(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "integracion", "version": "1.0"},
                },
            }
        )
        self.assertIn("tools", inicio["result"]["capabilities"])

        solicitar(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            espera_respuesta=False,
        )
        lista = solicitar(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        self.assertEqual(len(lista["result"]["tools"]), 3)

        proceso.stdin.close()
        proceso.wait(timeout=5)
        self.assertEqual(proceso.returncode, 0)
        self.assertEqual(proceso.stderr.read(), "")
        proceso.stdout.close()
        proceso.stderr.close()


if __name__ == "__main__":
    unittest.main()
