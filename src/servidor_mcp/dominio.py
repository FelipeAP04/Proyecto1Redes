"""Herramientas del asistente de modelado de datos y dashboards."""

from __future__ import annotations

import json
import re
from importlib.resources import files
from typing import Any

from .protocolo import ErrorRPC, ServidorJSONRPC


RECURSOS = {
    "bi://conocimiento/sql": {
        "archivo": "buenas_practicas_sql.md",
        "nombre": "Buenas prácticas de SQL",
        "descripcion": "Criterios para consultas legibles y eficientes.",
    },
    "bi://conocimiento/dax": {
        "archivo": "buenas_practicas_dax.md",
        "nombre": "Buenas prácticas de DAX",
        "descripcion": "Criterios básicos para medidas de Power BI.",
    },
    "bi://conocimiento/visualizaciones": {
        "archivo": "heuristicas_visualizacion.md",
        "nombre": "Heurísticas de visualización",
        "descripcion": "Selección de gráficos según el objetivo y los datos.",
    },
}


HERRAMIENTAS = [
    {
        "name": "analizar_modelo_datos",
        "title": "Analizar un diccionario de datos",
        "description": (
            "Analiza tablas y columnas para sugerir un modelo dimensional y detectar riesgos de calidad."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tablas": {
                    "type": "array",
                    "description": "Tablas del diccionario de datos.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nombre": {"type": "string"},
                            "descripcion": {"type": "string"},
                            "columnas": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "nombre": {"type": "string"},
                                        "tipo": {"type": "string"},
                                        "rol": {
                                            "type": "string",
                                            "enum": ["medida", "dimension", "identificador"],
                                        },
                                        "clave": {
                                            "type": "string",
                                            "enum": ["primaria", "foranea"],
                                        },
                                        "referencia": {"type": "string"},
                                    },
                                    "required": ["nombre", "tipo"],
                                },
                            },
                        },
                        "required": ["nombre", "columnas"],
                    },
                }
            },
            "required": ["tablas"],
        },
    },
    {
        "name": "recomendar_dashboard",
        "title": "Recomendar un dashboard",
        "description": (
            "Propone KPIs, visualizaciones y filtros a partir del objetivo y los campos disponibles."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "objetivo": {"type": "string", "minLength": 5},
                "campos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nombre": {"type": "string"},
                            "tipo": {"type": "string"},
                            "rol": {
                                "type": "string",
                                "enum": ["medida", "dimension", "fecha", "identificador"],
                            },
                            "cardinalidad": {"type": "integer", "minimum": 1},
                        },
                        "required": ["nombre", "tipo"],
                    },
                },
            },
            "required": ["objetivo", "campos"],
        },
    },
    {
        "name": "revisar_consulta_sql",
        "title": "Revisar y ordenar SQL",
        "description": (
            "Ordena una consulta SELECT sin cambiar su lógica y señala patrones que deben revisarse."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "consulta": {"type": "string", "minLength": 1},
                "dialecto": {
                    "type": "string",
                    "description": "Motor SQL de destino, por ejemplo PostgreSQL o BigQuery.",
                },
            },
            "required": ["consulta"],
        },
    },
]


class ServidorAsistenteBI(ServidorJSONRPC):
    """Servidor MCP con las capacidades específicas del caso de uso de BI."""

    def __init__(self) -> None:
        super().__init__()
        self.registrar("tools/list", self._listar_herramientas)
        self.registrar("tools/call", self._invocar_herramienta)
        self.registrar("resources/list", self._listar_recursos)
        self.registrar("resources/read", self._leer_recurso)

    def _inicializar(self, parametros: dict[str, Any]) -> dict[str, Any]:
        resultado = super()._inicializar(parametros)
        resultado["capabilities"] = {"tools": {}, "resources": {}}
        return resultado

    @staticmethod
    def _listar_herramientas(_parametros: dict[str, Any]) -> dict[str, Any]:
        return {"tools": HERRAMIENTAS}

    @staticmethod
    def _invocar_herramienta(parametros: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(parametros, dict) or not isinstance(parametros.get("name"), str):
            raise ErrorRPC(-32602, "tools/call requiere el nombre de una herramienta")

        argumentos = parametros.get("arguments", {})
        if not isinstance(argumentos, dict):
            raise ErrorRPC(-32602, "Los argumentos de la herramienta deben ser un objeto")

        funciones = {
            "analizar_modelo_datos": analizar_modelo_datos,
            "recomendar_dashboard": recomendar_dashboard,
            "revisar_consulta_sql": revisar_consulta_sql,
        }
        funcion = funciones.get(parametros["name"])
        if funcion is None:
            raise ErrorRPC(-32602, f"Herramienta desconocida: {parametros['name']}")

        try:
            resultado = funcion(argumentos)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(resultado, ensure_ascii=False, indent=2),
                    }
                ],
                "structuredContent": resultado,
                "isError": False,
            }
        except ValueError as error:
            return {
                "content": [{"type": "text", "text": str(error)}],
                "isError": True,
            }

    @staticmethod
    def _listar_recursos(_parametros: dict[str, Any]) -> dict[str, Any]:
        return {
            "resources": [
                {
                    "uri": uri,
                    "name": datos["nombre"],
                    "description": datos["descripcion"],
                    "mimeType": "text/markdown",
                }
                for uri, datos in RECURSOS.items()
            ]
        }

    @staticmethod
    def _leer_recurso(parametros: dict[str, Any]) -> dict[str, Any]:
        uri = parametros.get("uri") if isinstance(parametros, dict) else None
        recurso = RECURSOS.get(uri)
        if recurso is None:
            raise ErrorRPC(-32002, "Recurso no encontrado", {"uri": uri})

        ruta = files("servidor_mcp").joinpath("conocimiento", recurso["archivo"])
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "text/markdown",
                    "text": ruta.read_text(encoding="utf-8"),
                }
            ]
        }


def analizar_modelo_datos(argumentos: dict[str, Any]) -> dict[str, Any]:
    tablas = argumentos.get("tablas")
    if not isinstance(tablas, list) or not tablas:
        raise ValueError("Se requiere al menos una tabla en el diccionario de datos.")
    if len(tablas) > 100:
        raise ValueError("El análisis admite como máximo 100 tablas por solicitud.")

    hechos: list[str] = []
    dimensiones: list[str] = []
    relaciones: list[dict[str, str]] = []
    hallazgos: list[str] = []

    for tabla in tablas:
        if not isinstance(tabla, dict) or not isinstance(tabla.get("nombre"), str):
            raise ValueError("Cada tabla debe tener un nombre de texto.")
        columnas = tabla.get("columnas")
        if not isinstance(columnas, list) or not columnas:
            raise ValueError(f"La tabla {tabla['nombre']} debe incluir columnas.")
        if len(columnas) > 200:
            raise ValueError(f"La tabla {tabla['nombre']} supera el límite de 200 columnas.")
        if any(
            not isinstance(columna, dict)
            or not columna.get("nombre")
            or not columna.get("tipo")
            for columna in columnas
        ):
            raise ValueError(
                f"Todas las columnas de {tabla['nombre']} requieren nombre y tipo."
            )

        nombre = tabla["nombre"]
        medidas = [columna for columna in columnas if columna.get("rol") == "medida"]
        primarias = [columna for columna in columnas if columna.get("clave") == "primaria"]
        es_hecho = bool(medidas) or any(
            palabra in nombre.lower() for palabra in ("venta", "transaccion", "hecho", "fact")
        )
        (hechos if es_hecho else dimensiones).append(nombre)

        if not primarias:
            hallazgos.append(f"{nombre}: no se declaró una clave primaria.")
        nombres = [str(columna.get("nombre", "")) for columna in columnas]
        if len(nombres) != len(set(nombres)):
            hallazgos.append(f"{nombre}: contiene nombres de columna repetidos.")

        for columna in columnas:
            if columna.get("clave") == "foranea":
                referencia = columna.get("referencia")
                if referencia:
                    relaciones.append(
                        {"origen": f"{nombre}.{columna['nombre']}", "destino": referencia}
                    )
                else:
                    hallazgos.append(
                        f"{nombre}.{columna['nombre']}: la clave foránea no tiene referencia."
                    )
            if "fecha" in columna["nombre"].lower() and columna["tipo"].lower() in {
                "texto",
                "string",
                "varchar",
            }:
                hallazgos.append(
                    f"{nombre}.{columna['nombre']}: conviene usar un tipo fecha en lugar de texto."
                )

    if not dimensiones:
        hallazgos.append("No se identificaron dimensiones; considere separar entidades descriptivas.")
    if not hechos:
        hallazgos.append("No se identificó una tabla de hechos con medidas del negocio.")

    return {
        "modelo_recomendado": "estrella",
        "tablas_de_hechos": hechos,
        "dimensiones": dimensiones,
        "relaciones_declaradas": relaciones,
        "hallazgos": hallazgos or ["No se detectaron riesgos básicos en el diccionario."],
        "siguiente_paso": "Definir el grano de cada tabla de hechos antes de crear medidas.",
    }


def recomendar_dashboard(argumentos: dict[str, Any]) -> dict[str, Any]:
    objetivo = argumentos.get("objetivo")
    campos = argumentos.get("campos")
    if not isinstance(objetivo, str) or len(objetivo.strip()) < 5:
        raise ValueError("El objetivo del dashboard debe describirse con al menos 5 caracteres.")
    if not isinstance(campos, list) or not campos:
        raise ValueError("Se requiere al menos un campo para recomendar el dashboard.")

    medidas: list[str] = []
    fechas: list[str] = []
    dimensiones: list[dict[str, Any]] = []
    tipos_numericos = {"int", "integer", "entero", "decimal", "float", "double", "number"}
    tipos_fecha = {"date", "datetime", "timestamp", "fecha"}

    for campo in campos:
        if not isinstance(campo, dict) or not campo.get("nombre") or not campo.get("tipo"):
            raise ValueError("Cada campo requiere nombre y tipo.")
        tipo = str(campo["tipo"]).lower()
        rol = campo.get("rol")
        if rol == "medida" or (tipo in tipos_numericos and rol != "identificador"):
            medidas.append(campo["nombre"])
        elif rol == "fecha" or tipo in tipos_fecha:
            fechas.append(campo["nombre"])
        elif rol != "identificador":
            dimensiones.append(campo)

    kpis = [
        {"nombre": f"Total de {medida}", "calculo": f"SUM({medida})"}
        for medida in medidas[:4]
    ]
    visualizaciones: list[dict[str, str]] = []
    if medidas and fechas:
        visualizaciones.append(
            {
                "tipo": "gráfico de líneas",
                "campos": f"{fechas[0]} y {medidas[0]}",
                "motivo": "permite observar la tendencia de la medida en el tiempo",
            }
        )
    if medidas and dimensiones:
        visualizaciones.append(
            {
                "tipo": "gráfico de barras",
                "campos": f"{dimensiones[0]['nombre']} y {medidas[0]}",
                "motivo": "facilita comparar categorías con una línea base común",
            }
        )
    if len(medidas) >= 2:
        visualizaciones.append(
            {
                "tipo": "gráfico de dispersión",
                "campos": f"{medidas[0]} y {medidas[1]}",
                "motivo": "ayuda a identificar relación y valores atípicos",
            }
        )
    if not visualizaciones:
        visualizaciones.append(
            {
                "tipo": "tabla",
                "campos": "campos disponibles",
                "motivo": "faltan medidas o dimensiones para justificar otro gráfico",
            }
        )

    return {
        "objetivo_interpretado": objetivo.strip(),
        "kpis": kpis or [{"nombre": "Conteo de registros", "calculo": "COUNTROWS(tabla)"}],
        "visualizaciones": visualizaciones,
        "filtros_sugeridos": [campo["nombre"] for campo in dimensiones[:3]] + fechas[:1],
        "distribucion": [
            "Fila superior: tarjetas de KPI.",
            "Zona central: tendencia y comparación principal.",
            "Panel lateral: filtros con mayor utilidad para el análisis.",
        ],
    }


def revisar_consulta_sql(argumentos: dict[str, Any]) -> dict[str, Any]:
    consulta = argumentos.get("consulta")
    dialecto = argumentos.get("dialecto", "SQL genérico")
    if not isinstance(consulta, str) or not consulta.strip():
        raise ValueError("La consulta SQL no puede estar vacía.")
    if len(consulta) > 50_000:
        raise ValueError("La consulta supera el límite de 50,000 caracteres.")
    if not re.match(r"^\s*(WITH\b|SELECT\b)", consulta, flags=re.IGNORECASE):
        raise ValueError("Por seguridad, esta herramienta solo revisa consultas SELECT o WITH.")

    hallazgos: list[str] = []
    elementos_sensibles = ("'", '"', "--", "/*")
    if any(elemento in consulta for elemento in elementos_sensibles):
        ordenada = consulta.strip()
        hallazgos.append(
            "No se aplicó formato automático porque hay literales, identificadores o comentarios que deben preservarse."
        )
    else:
        compacta = re.sub(r"[ \t]+", " ", consulta.strip().rstrip(";"))
        palabras = (
            "FROM",
            "LEFT JOIN",
            "RIGHT JOIN",
            "INNER JOIN",
            "FULL JOIN",
            "WHERE",
            "GROUP BY",
            "HAVING",
            "ORDER BY",
            "LIMIT",
        )
        ordenada = compacta
        for palabra in palabras:
            patron_palabra = palabra.replace(" ", r"\s+")
            ordenada = re.sub(
                rf"\s+{patron_palabra}\s+",
                f"\n{palabra} ",
                ordenada,
                flags=re.IGNORECASE,
            )
        ordenada = re.sub(r"^select\s+", "SELECT ", ordenada, flags=re.IGNORECASE) + ";"

    if re.search(r"\bSELECT\s+\*", consulta, flags=re.IGNORECASE):
        hallazgos.append("Evite SELECT * y enumere únicamente las columnas necesarias.")
    if re.search(r"\b(DISTINCT)\b", consulta, flags=re.IGNORECASE):
        hallazgos.append("Confirme que DISTINCT no esté ocultando duplicados causados por un JOIN.")
    if re.search(r"\bWHERE\b[^;]*(YEAR|MONTH|DATE)\s*\(", consulta, flags=re.IGNORECASE):
        hallazgos.append("Una función sobre la columna filtrada puede impedir el uso de índices.")
    if " join " in consulta.lower() and not re.search(r"\bON\b", consulta, flags=re.IGNORECASE):
        hallazgos.append("Se encontró JOIN sin una condición ON visible; revise un posible producto cartesiano.")

    return {
        "dialecto": str(dialecto),
        "consulta_refactorizada": ordenada,
        "hallazgos": hallazgos or ["No se detectaron los patrones básicos revisados."],
        "alcance": (
            "La herramienta aplica formato básico y heurísticas; no reemplaza el plan de ejecución del motor."
        ),
    }
