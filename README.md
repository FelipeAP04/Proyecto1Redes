# Asistente Inteligente para Modelado de Datos y Dashboards

Servidor MCP local para apoyar tareas iniciales de Business Intelligence. Esta primera entrega se concentra únicamente en el servidor: todavía no incluye chatbot anfitrión, conexión a un LLM ni transporte remoto.

La implementación se hizo manualmente con JSON-RPC 2.0 para estudiar el protocolo. No utiliza FastMCP ni otro SDK de MCP.

## Funcionalidades

- Negociación del ciclo de vida MCP mediante `initialize` y `notifications/initialized`.
- Transporte local stdio con un mensaje JSON por línea.
- Descubrimiento e invocación de tres herramientas:
  - `analizar_modelo_datos`: identifica hechos, dimensiones, relaciones y riesgos básicos.
  - `recomendar_dashboard`: sugiere KPIs, gráficos, filtros y distribución visual.
  - `revisar_consulta_sql`: aplica formato conservador y señala patrones SQL riesgosos.
- Publicación de recursos MCP con guías de SQL, DAX y visualización.
- Respuestas estructuradas para que un futuro anfitrión o LLM pueda procesarlas.
- Validación de entradas, límites de tamaño y errores JSON-RPC estándar.

## Requisitos e instalación

- Python 3.11 o posterior.
- Git.

```bash
git clone https://github.com/FelipeAP04/Proyecto1Redes.git
cd Proyecto1Redes
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --editable .
```

El proyecto no tiene dependencias de ejecución externas.

## Uso

Después de instalarlo, el servidor puede ser iniciado por un cliente MCP con:

```bash
asistente-bi-mcp
```

También se puede ejecutar directamente desde el código fuente:

```bash
PYTHONPATH=src python3 -m servidor_mcp
```

El servidor espera mensajes JSON-RPC en `stdin` y responde exclusivamente por `stdout`. Los mensajes deben ocupar una sola línea. Para reproducir una sesión completa de ejemplo:

```bash
PYTHONPATH=src python3 -m servidor_mcp < ejemplos/sesion_dashboard.jsonl
```

En una configuración de cliente compatible con MCP, el comando debe apuntar al ejecutable instalado. Un ejemplo genérico es:

```json
{
  "mcpServers": {
    "asistente-bi": {
      "command": "/ruta/al/proyecto/.venv/bin/asistente-bi-mcp"
    }
  }
}
```

La configuración exacta depende del anfitrión. Esta etapa no implementa ni configura dicho cliente.

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```

Las pruebas cubren el ciclo MCP, los errores JSON-RPC, las herramientas, los recursos y una conversación real con el subproceso stdio.

## Documentación

- [Especificación del servidor](docs/ESPECIFICACION.md)
- [Sesión de ejemplo](ejemplos/sesion_dashboard.jsonl)
- [Especificación oficial de MCP 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18)
- [Especificación de JSON-RPC 2.0](https://www.jsonrpc.org/specification)

## Alcance y limitaciones

Las recomendaciones se basan en reglas transparentes y no en un modelo generativo. La revisión SQL acepta únicamente consultas `SELECT` o `WITH`, no ejecuta código y no reemplaza el plan de ejecución del motor. El análisis dimensional es un punto de partida que siempre debe validarse con una persona que conozca el negocio.

---

## English project overview

This repository contains the local MCP server for an Intelligent Data Modeling and Dashboard Development Assistant. The current milestone is intentionally server-only; the chatbot host, LLM API, official Filesystem/Git servers, and remote deployment will be added in later stages.

### Features and implemented functionality

- Manual JSON-RPC 2.0 and MCP 2025-06-18 lifecycle implementation over newline-delimited stdio.
- Three discoverable tools for data-model analysis, dashboard planning, and conservative SQL review.
- Three readable MCP resources containing SQL, DAX, and visualization guidance.
- Structured tool results, input validation, size limits, protocol errors, and automated tests.
- No FastMCP or MCP SDK is used, so the protocol exchange remains visible for learning purposes.

### Installation

Python 3.11 or newer and Git are required.

```bash
git clone https://github.com/FelipeAP04/Proyecto1Redes.git
cd Proyecto1Redes
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --editable .
```

### Usage on your computer

Run `asistente-bi-mcp` after installation. An MCP host must launch this command as a child process and communicate through stdin/stdout. To run the included example without a host, execute:

```bash
PYTHONPATH=src python3 -m servidor_mcp < ejemplos/sesion_dashboard.jsonl
```

Run the full test suite with `python3 -m unittest discover -s tests -v`. Detailed methods, parameters, message flow, and example results are documented in [`docs/ESPECIFICACION.md`](docs/ESPECIFICACION.md).
