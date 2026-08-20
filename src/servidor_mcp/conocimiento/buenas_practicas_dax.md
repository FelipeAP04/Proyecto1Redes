# Buenas prácticas de DAX

- Preferir medidas explícitas sobre columnas calculadas para agregaciones dinámicas.
- Utilizar `DIVIDE(numerador, denominador)` para manejar divisiones entre cero.
- Separar medidas base, como ventas totales, de medidas derivadas, como crecimiento porcentual.
- Mantener una tabla de fechas continua y marcarla como tabla de fechas en el modelo.
- Evitar iteradores como `SUMX` cuando una agregación simple produce el mismo resultado.
- Nombrar medidas con términos que una persona del negocio pueda reconocer.
