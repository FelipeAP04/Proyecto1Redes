# Anfitrión MCP de consola

## Propósito

El anfitrión permite utilizar el servidor local desde una interfaz de consola. Su responsabilidad es iniciar el proceso del servidor, completar el ciclo de vida MCP, enviar solicitudes JSON-RPC, presentar resultados y mantener un registro de la comunicación.

Esta versión todavía no es un chatbot y no utiliza un LLM. El usuario selecciona explícitamente la herramienta y proporciona sus datos mediante archivos JSON o texto en la terminal.

## Arquitectura

```text
Usuario
   │ menú y archivos JSON
   ▼
Anfitrión de consola
   │ stdin: solicitudes y notificaciones JSON-RPC
   │ stdout: respuestas JSON-RPC
   ▼
Servidor MCP de BI
```

El anfitrión crea el servidor como un subproceso. La sesión sigue esta secuencia:

1. Envía `initialize` y espera la respuesta con la versión y capacidades.
2. Envía `notifications/initialized` sin esperar respuesta.
3. Utiliza `tools/list`, `tools/call`, `resources/list` y `resources/read` según el menú.
4. Cierra `stdin` cuando termina la sesión y espera que el servidor finalice.

Cada solicitud usa un identificador incremental. El anfitrión comprueba que la respuesta tenga el mismo `id` y reporta los errores JSON-RPC de forma legible.

## Ejecución

Sin instalar el proyecto:

```bash
PYTHONPATH=src python3 -m anfitrion_mcp
```

Después de instalarlo con `python3 -m pip install --editable .`:

```bash
anfitrion-bi
```

Para utilizar otra ruta de registro:

```bash
anfitrion-bi --registro logs/demostracion.jsonl
```

## Opciones del menú

### 1. Analizar diccionario de datos

Solicita la ruta de un archivo JSON. Puede ser un arreglo de tablas o un objeto con la propiedad `tablas`. Para la demostración se puede ingresar:

```text
ejemplos/diccionario_ventas.json
```

### 2. Recomendar dashboard

Solicita el objetivo y un archivo con un arreglo de campos o la propiedad `campos`. Ejemplo:

```text
Objetivo: Monitorear ventas por región
Archivo: ejemplos/campos_dashboard.json
```

### 3. Revisar consulta SQL

Solicita una consulta `SELECT` o `WITH` y un dialecto opcional. La consulta se envía al servidor para revisión, pero nunca se ejecuta.

### 4. Consultar recursos técnicos

Descubre los recursos mediante `resources/list`, permite seleccionar uno y obtiene su contenido mediante `resources/read`.

### 5. Mostrar log MCP

Muestra las solicitudes, notificaciones y respuestas acumuladas. Cada entrada contiene:

- Fecha UTC en formato ISO 8601.
- Dirección `cliente_a_servidor` o `servidor_a_cliente`.
- Mensaje JSON-RPC completo.

El archivo predeterminado es `logs/sesion_mcp.jsonl`. La carpeta `logs` se ignora en Git porque contiene información generada durante la ejecución.

### 6. Salir

Cierra la entrada estándar del servidor y espera su finalización. Si el proceso no responde, el cliente intenta terminarlo de forma controlada.

## Limitaciones actuales

- Las operaciones son secuenciales; no hay solicitudes MCP concurrentes.
- No existe conversación en lenguaje natural ni contexto de conversación.
- No se conecta a una API de LLM.
- No integra todavía los servidores Filesystem y Git.
- Solamente utiliza el transporte local stdio.
