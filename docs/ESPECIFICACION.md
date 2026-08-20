# Especificación del servidor MCP

## 1. Propósito

El servidor expone conocimiento y heurísticas para que un futuro chatbot pueda convertir requerimientos de lenguaje natural en apoyo para modelado dimensional, consultas SQL y dashboards. En esta etapa el servidor no interpreta lenguaje natural por sí solo: recibe parámetros estructurados desde un cliente MCP.

## 2. Arquitectura y transporte

```text
Cliente MCP ──stdin/JSON-RPC──▶ Servidor MCP ──▶ Herramientas de BI
Cliente MCP ◀─stdout/JSON-RPC── Servidor MCP ──▶ Recursos Markdown
```

- Transporte: `stdio`.
- Codificación: UTF-8.
- Enmarcado: un objeto JSON-RPC 2.0 por línea, sin saltos de línea físicos dentro del mensaje.
- Versión MCP: `2025-06-18`.
- Registros: cualquier diagnóstico utiliza `stderr`; `stdout` queda reservado para MCP.
- Finalización: el servidor termina cuando el cliente cierra `stdin`.

En stdio no existen endpoints HTTP. Los “endpoints” equivalentes son los métodos JSON-RPC descritos a continuación.

## 3. Ciclo de comunicación

1. El cliente envía `initialize` con `protocolVersion`, `capabilities` y `clientInfo`.
2. El servidor responde su versión, información y capacidades `tools` y `resources`.
3. El cliente envía la notificación `notifications/initialized`, sin `id`.
4. El cliente puede utilizar las operaciones anunciadas.
5. Para finalizar, el cliente cierra la entrada estándar del proceso.

Antes del paso 3 solamente se acepta `ping`. Las notificaciones nunca generan respuesta.

## 4. Métodos MCP

| Método | Tipo | Parámetros | Resultado |
|---|---|---|---|
| `initialize` | Solicitud | Versión, capacidades e información del cliente | Versión, capacidades e información del servidor |
| `notifications/initialized` | Notificación | Ninguno | Sin respuesta |
| `ping` | Solicitud | Ninguno | Objeto vacío |
| `tools/list` | Solicitud | Cursor opcional, actualmente no utilizado | Definiciones y esquemas de herramientas |
| `tools/call` | Solicitud | `name` y `arguments` | Contenido textual y estructurado |
| `resources/list` | Solicitud | Cursor opcional, actualmente no utilizado | Recursos disponibles |
| `resources/read` | Solicitud | `uri` | Contenido Markdown del recurso |

## 5. Herramientas

### `analizar_modelo_datos`

Recibe un diccionario de datos y propone una separación inicial entre hechos y dimensiones.

Parámetros:

- `tablas` (arreglo, requerido): máximo 100 tablas.
  - `nombre` (texto, requerido).
  - `descripcion` (texto, opcional).
  - `columnas` (arreglo, requerido): máximo 200 por tabla.
    - `nombre` y `tipo` (texto, requeridos).
    - `rol` (opcional): `medida`, `dimension` o `identificador`.
    - `clave` (opcional): `primaria` o `foranea`.
    - `referencia` (opcional): destino de una clave foránea, como `clientes.id`.

Devuelve el modelo recomendado, hechos, dimensiones, relaciones, hallazgos y siguiente paso. La clasificación se basa en roles declarados y convenciones de nombres; no reemplaza la definición del grano con el área de negocio.

### `recomendar_dashboard`

Parámetros:

- `objetivo` (texto, requerido): finalidad de negocio del dashboard.
- `campos` (arreglo, requerido): máximo 500 campos.
  - `nombre` y `tipo` (texto, requeridos).
  - `rol` (opcional): `medida`, `dimension`, `fecha` o `identificador`.
  - `cardinalidad` (entero positivo, opcional).

Devuelve KPIs, visualizaciones, filtros y una distribución sugerida. Las reglas favorecen líneas para tiempo, barras para categorías y dispersión para dos medidas.

### `revisar_consulta_sql`

Parámetros:

- `consulta` (texto, requerido): máximo 50,000 caracteres; debe comenzar con `SELECT` o `WITH`.
- `dialecto` (texto, opcional): motor de destino.

Devuelve una consulta con formato básico, hallazgos y una advertencia de alcance. Si existen literales, identificadores entre comillas o comentarios, se conserva la consulta original para no cambiar su semántica. Nunca ejecuta SQL y rechaza instrucciones de escritura.

## 6. Recursos

| URI | Tipo | Contenido |
|---|---|---|
| `bi://conocimiento/sql` | `text/markdown` | Buenas prácticas de consultas SQL para BI |
| `bi://conocimiento/dax` | `text/markdown` | Buenas prácticas de medidas DAX |
| `bi://conocimiento/visualizaciones` | `text/markdown` | Heurísticas para escoger y diseñar gráficos |

El esquema `bi://` es un URI propio conforme a RFC 3986. Los recursos son de solo lectura y vienen incluidos en el paquete.

## 7. Errores

| Código | Significado en este servidor |
|---:|---|
| `-32700` | El texto recibido no es JSON válido |
| `-32600` | La solicitud no cumple JSON-RPC 2.0 |
| `-32601` | El método no existe |
| `-32602` | Parámetros inválidos o herramienta desconocida |
| `-32603` | Error interno no esperado |
| `-32002` | Servidor no inicializado o recurso inexistente |

Los errores corregibles de datos dentro de una herramienta se devuelven como un resultado MCP con `isError: true`, de manera que el futuro LLM pueda ajustar sus argumentos.

## 8. Ejemplo resumido

Solicitud:

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"recomendar_dashboard","arguments":{"objetivo":"Monitorear ventas por región","campos":[{"nombre":"ventas","tipo":"decimal","rol":"medida"},{"nombre":"fecha","tipo":"date","rol":"fecha"},{"nombre":"region","tipo":"texto","rol":"dimension"}]}}}
```

La respuesta contiene una tarjeta para `SUM(ventas)`, una línea por fecha, barras por región y filtros sugeridos. La conversación completa, incluyendo inicialización y descubrimiento, se encuentra en `ejemplos/sesion_dashboard.jsonl`.
