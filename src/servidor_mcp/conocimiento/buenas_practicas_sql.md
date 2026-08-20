# Buenas prácticas de SQL para BI

- Seleccionar únicamente las columnas requeridas en lugar de utilizar `SELECT *`.
- Definir el grano esperado del resultado antes de agregar tablas mediante `JOIN`.
- Revisar cardinalidades y duplicados antes de utilizar `DISTINCT` como corrección.
- Filtrar lo más temprano posible, sin aplicar funciones a columnas indexadas cuando pueda evitarse.
- Utilizar alias breves y descriptivos, y calificar columnas ambiguas.
- Revisar el plan de ejecución del motor; una heurística no sustituye sus estadísticas reales.
