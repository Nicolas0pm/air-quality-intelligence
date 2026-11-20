# Guion del video demostrativo (máx. 6 minutos)

**0:00 – 0:30 · Presentación.** Nombre, asignatura y el reto: identificar el aire contaminado, purificarlo y verificar el resultado con BI.

**0:30 – 1:15 · Arquitectura.** Mostrar la Figura 1 del informe: sensores de entrada, purificación, validación, backend en Python, base de datos y dashboard en React. Explicar por qué un solo filtro no basta (HEPA para partículas, catalizador para CO, adsorbente para CO₂).

**1:15 – 2:15 · Módulo 1.** Pestaña Monitoreo → fuente «Zona industrial» → «Detectar ingreso de aire». Señalar la fecha y hora, los cuatro valores con su color, el nivel global, las alertas y los filtros recomendados.

**2:15 – 3:15 · Módulo 2.** Continuar a Descontaminación. Mostrar los filtros recomendados, mover el tiempo a 30 min y leer la estimación del modelo predictivo. Activar y comentar cómo bajan las curvas.

**3:15 – 3:50 · Módulo 3.** Ver la validación: tabla antes/después, % de reducción y resultado del tratamiento.

**3:50 – 5:10 · Dashboard.** Recorrer los 6 indicadores y los 4 gráficos. Filtrar por «Interior oficina» para mostrar que el problema allí es el CO₂. Usar el modelo predictivo con otra combinación. Abrir Reportes y descargar el CSV.

**5:10 – 6:00 · Resultados y cierre.** PM2.5 reducido 92 %, 83 % de lotes cumplen; los fallos se deben a gases sin tratar. Conclusión y siguiente paso: conectar sensores físicos a la misma API.
