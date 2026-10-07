Este `README` tiene el propósito de explicar el contenido y procesamiento de los datos de obtenidos desde Bookeau para las tutorías de CupiTaller.


- [Encuesta Reserva Express](#encuesta-reserva-express)
- [Encuesta Reserva Normal](#encuesta-reserva-normal)
- [Encuesta Express](#encuesta-express)
- [Encuesta Normal](#encuesta-normal)
- [Reservas](#reservas)
    - [Obtención de los datos](#obtención-de-los-datos)
    - [Procesamiento de los datos](#procesamiento-de-los-datos)


# Encuesta Reserva Express
Los datos de la carpeta `data/raw/Bookeau/Encuesta Reserva Express` son archivos Excel que contienen las respuestas de los estudiantes a la encuesta previa a la reserva de una tutoria de 30 minutos (tutorias "express").

La carpeta contiene un archivo excel por cada semestre desde 201620 hasta 202610.
    
# Encuesta Reserva Normal
Los datos de la carpeta `data/raw/Bookeau/Encuesta Reserva Normal` son archivos Excel que contienen las respuestas de los estudiantes a la encuesta previa a la reserva de una tutoria de 1 hora (tutoria "normal").

La carpeta contiene un archivo excel por cada semestre desde 201620 hasta 202610.

# Encuesta Express
Los datos de la carpeta `data/raw/Bookeau/Encuesta Express` son archivos Excel que contienen las respuestas de los estudiantes a las encuestas sobre la satisfacción con las tutorias de 30 minutos (tutorias "express").

La carpeta contiene un archivo excel por cada semestre desde 201620 hasta 202610.

# Encuesta Normal
Los datos de la carpeta `data/raw/Bookeau/Encuesta Normal` son archivos Excel que contienen las respuestas de los estudiantes a las encuestas sobre la satisfacción con las tutorias de 1 hora (tutoria "normal").

La carpeta contiene un archivo excel por cada semestre desde 201620 hasta 202610.

---
# Reservas
Los datos en la carpeta `data/raw/Bookeau/Reservas` son archivos Excel que contienen las reservas solicitadas por los estudiantes para las tutorías de CupiTaller.

La carpeta contiene un archivo excel por cada semestre desde 201620 hasta 202610.

Cada archivo tiene la misma estructura y su nombre corresponde al semestre que representa, por ejemplo, `Reservas202010.xlsx` es para las reservas a CupiTaller en el semestre 202010.

### Obtención de los datos
1. Entra a [Bookeau de CupiTaller](https://cupitaller.bookeau.com/#/reportes) y escoges el rol de **Analista**.
2. En la sección de **Reportes** seleccionas **Reservas**.
3. Luego, configuras los parámetros deseados, en este caso:
   - Nivel de detalle: Semanas
   - Periodo: El semestre que deseas descargar
   - Categoría: Todas
   - Tipo de horario: Todos
   - Servicio: Todos
4. Finalmente, en la parte inferior derecha hay un botón llamado **Descargar reservas**, el cual te permite descargar un archivo Excel con las asistencias del semestre seleccionado.
5. Finalmente, cambiale el nombre al archivo a `Reservas<SEMESTRE>.xlsx` por el semestre correspondiente y guárdalo en la carpeta `data/raw/Bookeau/Reservas`.

### Procesamiento de los datos
El procesamiento de los datos se realiza en el archivo `src/Bookeau/reservas_cupitaller_procesamiento_raw.ipynb`. Este archivo es un notebook de Jupyter que contiene el código necesario para procesar los datos de asistencias. Básicamente lo que se hace es:
1. Añadir una columna llamada `SEMESTRE` a cada archivo con el semestre correspondiente.
2. Concatenar todos los archivos en un solo DataFrame.
3. Cambiar el nombre de algunas columnas para que sean más fáciles de manejar.
4. Guardar el DataFrame resultante en un archivo CSV en la carpeta `data/compilados/` llamado `asistencias_cupi_desde_202010.csv`.