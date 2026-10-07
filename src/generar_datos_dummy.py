"""Genera datos ficticios con la misma estructura que los Excel de Bookeau.

Sirven para probar el pipeline completo sin compartir datos personales: todos los
nombres, correos, códigos y comentarios son inventados. Escribe los libros de Excel en
data/bronce/dummy/<grupo>/ (no toca los datos reales de data/bronce/Bookeau/).

Usa solo la biblioteca estándar. Es determinista: la misma semilla da los mismos datos.
    python3 src/generar_datos_dummy.py
"""
from __future__ import annotations

import random
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DUMMY_BRONCE = ROOT / 'data/bronce/dummy'       # libros de Excel ficticios
SOURCE = DUMMY_BRONCE
SEED = 4214
PERIODOS = ['201710', '201719', '201720', '201819', '201820', '201920', '202010', '202110', '202120']

COMUNES = ['ID', 'Fecha inicio', 'Fecha fin', 'Fecha de llegada', 'Fecha de devolución', 'Estado de la reserva', 'Prioritaria', 'Categoría', 'Tipo de horario', 'Servicio']
USUARIO = ['Usuario', 'Correo usuario', 'Código usuario', 'Tipo de usuario', 'Programa', 'Prestador del servicio']
RESERVAS = COMUNES + ['Código servicio'] + USUARIO
BASE_ENCUESTA = COMUNES + ['Código del servicio'] + USUARIO + ['Estado']
P_EXPRESS = ['¿El tiempo fue adecuado para resolver su problema o duda puntual?', 'La mayor parte del tiempo de la tutoría lo dediqué a', 'Califique la ayuda que le dio su tutor', 'El tutor me explicó cómo solucionar mi duda/problema/proyecto', 'El tutor aclaró y reforzó conceptos', 'El tutor me brindó herramientas adicionales para trabajar por mi cuenta', 'El tutor fue receptivo frente a mis inquietudes durante la tutoría', 'El tutor es capaz de expresar claramente su conocimiento sobre el tema o temas trabajados']
P_NORMAL = ['La tutoría a la que asistí me permitió entender que la solución de un problema usando herramientas de programación es un proceso que implica leer el problema, entender los requerimientos, planear un algoritmo, escribir el código y probar lo implementado', 'La tutoría a la que asistí se enfocó en el desarrollo de mis habilidades de análisis y no solo en la corrección de mi código', 'La mayor parte del tiempo de la tutoría lo dediqué a', 'Aproveché el tiempo de la tutoría haciendo preguntas puntuales al tutor y participando de manera proactiva en el desarrollo de las mismas', 'Califique la ayuda que le dio su tutor', 'El tutor me explicó cómo solucionar mi duda/problema/proyecto', 'El tutor aclaró y reforzó conceptos', 'El tutor me brindó herramientas adicionales para trabajar por mi cuenta', 'El tutor fue receptivo frente a mis inquietudes durante la tutoría', 'El tutor es capaz de expresar claramente su conocimiento sobre el tema o temas trabajados']
P_COLAS = ['Durante la tutoría, el tutor hizo uso de alguna herramienta de inteligencia artificial, tal como pero no limitándose a ChatGPT, Bard/Gemini o Bing AI.', 'Indique cuál fue la herramienta usada durante la tutoría (si sabe cuál es) y el uso que tuvo la misma en la tutoría.', '¿Cuál considera que es su comprensión del tema actual del curso?', '¿Considera que el material del curso permite un buen proceso de aprendizaje?', 'Comente aspectos positivos y negativos del tutor y la tutoría. Recuerde que las respuestas van a ser anónimas.', 'Escriba en este recuadro cualquier observación o comentario relacionado al curso y sus contenidos.', 'Sugerencias, reclamos y observaciones']
P_PREVIA = ['La mayoría del tiempo de la tutoría que estoy reservando lo usaré para', 'Entiendo que durante la tutoría no debo usar mi celular', 'Acepto que si quiero trabajar en una tarea en senecode debo tener una solución probada y que pueda explicar, en caso de no cumplir estas condiciones se configurará un comportamiento inadecuado', 'Acepto que he leído los términos de uso de CupiTaller que están disponibles en la URL https://cupitaller.uniandes.edu.co/terminos-de-uso/']
RATING = 'Califique la ayuda que le dio su tutor'
COMENTARIO, OBSERVACION, SUGERENCIA = P_COLAS[4], P_COLAS[5], P_COLAS[6]
IA, IA_TEXTO, COMPRENSION, MATERIAL = P_COLAS[0], P_COLAS[1], P_COLAS[2], P_COLAS[3]

# grupo -> (carpeta, patrón del archivo, hoja, encabezados)
GRUPOS = {
    'Reservas': ('Reservas', 'Reservas{p}.xlsx', 'Citas', RESERVAS),
    'Express': ('Encuesta Express', 'Encuesta Estudiante Express {p}.xlsx', 'Respuestas', BASE_ENCUESTA + P_EXPRESS + P_COLAS),
    'Normal': ('Encuesta Normal', 'Encuesta Estudiante Normal {p}.xlsx', 'Respuestas', BASE_ENCUESTA + P_NORMAL + P_COLAS),
    'PreviaExpress': ('Encuesta Reserva Express', 'Encuesta Reserva Express IP {p}.xlsx', 'Respuestas', BASE_ENCUESTA + P_PREVIA),
    'PreviaNormal': ('Encuesta Reserva Normal IP', 'Encuesta Reserva Normal IP {p}.xlsx', 'Respuestas', BASE_ENCUESTA + P_PREVIA),
}

ESTADOS = [('Finalizada', 45), ('Cancelada a tiempo', 20), ('En cola', 11), ('No asistió', 6), ('Cola cancelada por reservación', 5), ('Realizada', 5),
           ('Cancelada por sanción', 3), ('Cancelada con excusa', 1.5), ('Cancelada', 1), ('Cancelada y sancionada', 0.5)]
TIPOS = [('Normal', 55), ('Express', 25), ('Normal pico', 8), ('Entrevistas', 4), ('Sala', 3), ('Deprecated, Grupal', 3), ('Deprecated, Torre Séneca', 2)]
MINUTOS = {'Normal': 60, 'Express': 30, 'Normal pico': 60, 'Entrevistas': 30, 'Sala': 120, 'Deprecated, Grupal': 50, 'Deprecated, Torre Séneca': 60}
SERVICIOS_VIEJOS = [('Deprecated, APO 1', 'ISIS 1204'), ('Deprecated, APO 2', 'ISIS 1205'), ('EDA', 'ISIS-1225'), ('Deprecated, DPOO', 'ISIS 1226')]
PROGRAMAS = ['INGENIERIA DE SISTEMAS', 'Ingeniería de Sistemas', 'INGENIERÍA DE SISTEMAS', 'INGENIERIA INDUSTRIAL', 'ECONOMIA', 'ARTE', 'MATEMATICAS', 'Ingeniería Electrónica', 'INGENIERIA ELECTRONICA', 'DISEÑO']
ESCALA = ['Totalmente de acuerdo', 'De acuerdo', 'Neutral', 'En desacuerdo']
COMENTARIOS = ['Muy buena explicación, gracias', 'Excelente tutor, resolvió todas mis dudas', 'Nada', 'N/A', 'Faltó un poco más de tiempo', 'El tutor fue amable pero no pudo resolver mi duda', 'Me ayudó a entender los errores de mi código', 'Problemas de conexión durante la sesión', 'Todo perfecto', 'Poco claro al explicar', 'Muy atento y paciente', 'Sin comentarios', 'Regular, esperaba más ayuda', 'Genial']
SUGERENCIAS = ['Más horarios en la tarde', 'Ninguna', 'Mejorar la conexión remota', 'Más tutores en semana de parciales', 'Todo bien', 'Recordar la hora de la cita']
USOS = ['Resolver una duda de un ejercicio', 'Revisar mi código', 'Preparar un parcial', 'Entender un concepto del curso']


def pesos(opciones, rng):
    return rng.choices([o for o, _ in opciones], weights=[w for _, w in opciones])[0]


def ventana(periodo, rng):
    anio, sufijo = int(periodo[:4]), periodo[4:]
    inicio = {'10': (2, 1), '19': (6, 1), '20': (8, 1)}[sufijo]
    dias = {'10': 105, '19': 50, '20': 110}[sufijo]
    base = datetime(anio, *inicio) + timedelta(days=rng.randint(0, dias))
    while base.weekday() > 4:
        base += timedelta(days=1)
    return base.replace(hour=rng.randint(8, 18), minute=rng.choice([0, 30]))


def generar_reservas(periodo, indice, rng, contador):
    anio = int(periodo[:4])
    abiertos = periodo == PERIODOS[-1]
    filas = []
    for _ in range(rng.randint(160, 260)):
        contador[0] += 1
        n = contador[0]
        tipo = pesos(TIPOS, rng)
        estado = pesos(ESTADOS, rng)
        if abiertos and rng.random() < 0.05:
            estado = rng.choice(['En ejecución', 'Reservada'])
        inicio = ventana(periodo, rng)
        fin = inicio + timedelta(minutes=MINUTOS[tipo])
        if tipo == 'Entrevistas':
            servicio, codigo, categoria = 'Entrevista', 'Entrevista', 'Candidatos'
        elif tipo == 'Sala':
            servicio, codigo, categoria = 'Sala', 'Sala', 'Sala'
        else:
            servicio, codigo = ('IP', 'ISIS-1221') if (anio >= 2019 or rng.random() < 0.3) else rng.choice(SERVICIOS_VIEJOS)
            categoria = rng.choice(['Tutor Presencial', 'Monitor Remoto', 'Monitor Presencial'])
        atendida = estado in ('Finalizada', 'Realizada', 'En ejecución')
        llegada = inicio + timedelta(minutes=rng.randint(-10, 10)) if atendida else None
        if estado == 'Reservada' and rng.random() < 0.75:
            llegada = inicio
        # anomalías deliberadas para probar las banderas de calidad
        if estado == 'Finalizada' and rng.random() < 0.01:
            llegada = None
        if estado in ('No asistió', 'Cancelada a tiempo') and rng.random() < 0.01:
            llegada = inicio
        programa = None if rng.random() < 0.02 else rng.choice(PROGRAMAS)
        filas.append({
            'ID': 100000 + n, 'Fecha inicio': inicio, 'Fecha fin': fin, 'Fecha de llegada': llegada, 'Fecha de devolución': None,
            'Estado de la reserva': estado, 'Prioritaria': 'sí' if rng.random() < 0.03 else 'no', 'Categoría': categoria,
            'Tipo de horario': tipo, 'Servicio': servicio, 'Código servicio': codigo, 'Código del servicio': codigo,
            'Usuario': f'Estudiante Ficticio {n % 400:03d}', 'Correo usuario': f'estudiante{n % 400:03d}@ejemplo.invalid',
            'Código usuario': 900000 + n % 400, 'Tipo de usuario': 'Aspirante' if tipo == 'Entrevistas' else rng.choice(['Normal'] * 9 + ['Estudiante Honores']),
            'Programa': programa, 'Prestador del servicio': f'Monitor Ficticio {rng.randint(1, 25):02d}' if atendida else None,
            '_periodo': periodo, '_atendida': atendida})
    return filas


def respuestas_satisfaccion(fila, periodo, grupo, rng):
    r = {}
    if periodo >= '201819':
        nota = rng.choices([1, 2, 3, 4, 5, None], weights=[1, 1, 4, 12, 70, 12])[0]
        if rng.random() < 0.08:
            nota = rng.choice([1, 2, 3])  # más notas bajas en algunas sesiones
        r[RATING] = nota
        for p in (P_EXPRESS[3:] if grupo == 'Express' else P_NORMAL[5:]):
            r[p] = rng.choice(ESCALA) if rng.random() > 0.2 else None  # preguntas sobre el tutor, desde 201819
    for p in (P_EXPRESS if grupo == 'Express' else P_NORMAL):
        if p != RATING and p not in r:
            r[p] = rng.choice(ESCALA + ['Resolver dudas', 'Revisar código']) if rng.random() > 0.05 else None
    if periodo >= '202110':
        r[IA] = rng.choice(['Sí', 'No', 'No'])
        r[IA_TEXTO] = 'Un asistente de código para explicar un error' if r[IA] == 'Sí' and rng.random() < 0.05 else None
        r[COMPRENSION] = rng.choice(['Alta', 'Media', 'Baja'])
        r[MATERIAL] = rng.choice(['Sí', 'No', 'Parcialmente'])
    r[COMENTARIO] = rng.choice(COMENTARIOS) if rng.random() < 0.78 else None
    r[OBSERVACION] = rng.choice(COMENTARIOS) if rng.random() < 0.08 else None
    r[SUGERENCIA] = rng.choice(SUGERENCIAS) if rng.random() < 0.25 else None
    return r


def respuestas_previa(rng):
    return {P_PREVIA[0]: rng.choice(USOS), P_PREVIA[1]: 'Sí', P_PREVIA[2]: 'Sí', P_PREVIA[3]: 'Sí'}


def derivar_encuesta(reserva, rng):
    """Copia los atributos de la reserva; en ~1% de los casos introduce una diferencia."""
    e = {k: v for k, v in reserva.items() if not k.startswith('_')}
    e['Estado'] = 'Inválida' if rng.random() < 0.01 else 'Válida'
    if rng.random() < 0.01:
        e['Prestador del servicio'] = (e['Prestador del servicio'] or 'Monitor Ficticio 01').upper()
    if rng.random() < 0.005:
        e['Programa'] = 'ECONOMIA'
    return e


def generar_todo():
    rng = random.Random(SEED)
    contador = [0]
    salida = {g: {} for g in GRUPOS}
    for i, periodo in enumerate(PERIODOS):
        reservas = generar_reservas(periodo, i, rng, contador)
        salida['Reservas'][periodo] = reservas
        for g in ('Express', 'Normal', 'PreviaExpress', 'PreviaNormal'):
            salida[g][periodo] = []
        for r in reservas:
            tipo = r['Tipo de horario']
            if r['Estado de la reserva'] in ('Finalizada', 'Realizada') and rng.random() < 0.62:
                g = 'Express' if tipo in ('Express', 'Deprecated, Grupal') else 'Normal'
                e = derivar_encuesta(r, rng)
                e.update(respuestas_satisfaccion(r, periodo, g, rng))
                salida[g][periodo].append(e)
            if periodo >= '201920' and tipo in ('Express', 'Normal', 'Normal pico') and r['Servicio'] == 'IP' \
                    and r['Estado de la reserva'] not in ('En cola', 'Cola cancelada por reservación', 'Cancelada') and rng.random() < 0.55:
                g = 'PreviaExpress' if tipo == 'Express' else 'PreviaNormal'
                e = derivar_encuesta(r, rng)
                e.update(respuestas_previa(rng))
                salida[g][periodo].append(e)
    return salida


# ---- horarios (oferta): resumen de las reservas de Tutor Presencial por período, día y hora ----
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
ENCABEZADOS_HORARIOS = ['Día', 'Hora', 'Asistencias', 'Cancelaciones', 'Inasistencias', 'En lista de espera', 'Reservaron luego de estar en lista', 'Cupos reservados', 'Cupos disponibles']


def generar_horarios(reservas, periodo, rng):
    franjas = {}
    for r in reservas:
        if r['Categoría'] != 'Tutor Presencial':
            continue
        inicio = r['Fecha inicio']
        clave = (DIAS[inicio.weekday()], f"{inicio.hour % 12 or 12}:{inicio.minute:02d} {'am' if inicio.hour < 12 else 'pm'}")
        f = franjas.setdefault(clave, dict.fromkeys(ENCABEZADOS_HORARIOS[2:], 0))
        estado = r['Estado de la reserva']
        if estado in ('Finalizada', 'Realizada', 'En ejecución'):
            f['Asistencias'] += 1
        elif estado == 'No asistió':
            f['Inasistencias'] += 1
        elif estado.startswith('Cancelada'):
            f['Cancelaciones'] += 1
        elif estado == 'En cola':
            f['En lista de espera'] += 1
        elif estado == 'Cola cancelada por reservación':
            f['Reservaron luego de estar en lista'] += 1
    filas = []
    for (dia, hora), f in sorted(franjas.items(), key=lambda x: (DIAS.index(x[0][0]), x[0][1])):
        reservados = 0 if periodo < '201719' else round(0.9 * (f['Asistencias'] + f['Inasistencias'] + f['Cancelaciones']))
        filas.append({'Día': dia, 'Hora': hora, **f, 'Cupos reservados': reservados, 'Cupos disponibles': reservados + rng.randint(5, 30)})
    return filas


# ---- escritura de libros .xlsx con la biblioteca estándar --------------------------------
def columna(i):
    letras = ''
    i += 1
    while i:
        i, resto = divmod(i - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def celda(ref, valor):
    if valor is None or valor == '':
        return ''
    if isinstance(valor, datetime):
        serial = (valor - datetime(1899, 12, 30)).total_seconds() / 86400
        return f'<c r="{ref}" s="1"><v>{serial!r}</v></c>'
    if isinstance(valor, (int, float)):
        return f'<c r="{ref}"><v>{valor}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(str(valor))}</t></is></c>'


def escribir_xlsx(ruta, hoja, encabezados, filas):
    cuerpo = ['<row r="1">' + ''.join(celda(f'{columna(i)}1', h) for i, h in enumerate(encabezados)) + '</row>']
    for n, fila in enumerate(filas, 2):
        cuerpo.append(f'<row r="{n}">' + ''.join(celda(f'{columna(i)}{n}', fila.get(h)) for i, h in enumerate(encabezados)) + '</row>')
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    partes = {
        '[Content_Types].xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
        '_rels/.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="{escape(hoja)}" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        'xl/styles.xml': f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="{ns}"><fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="22" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs></styleSheet>',
        'xl/worksheets/sheet1.xml': f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="{ns}"><sheetData>{"".join(cuerpo)}</sheetData></worksheet>',
    }
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ruta, 'w', zipfile.ZIP_DEFLATED) as zf:
        for nombre, contenido in partes.items():
            info = zipfile.ZipInfo(nombre, date_time=(2026, 1, 1, 0, 0, 0))  # fecha fija: archivos idénticos en cada generación
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, contenido)


def main():
    datos = generar_todo()
    total = 0
    for g, (carpeta, patron, hoja, encabezados) in GRUPOS.items():
        for periodo, filas in datos[g].items():
            if g.startswith('Previa') and periodo < '201920':
                continue
            escribir_xlsx(SOURCE / carpeta / patron.format(p=periodo), hoja, encabezados, filas)
            total += 1
        print(f'{carpeta}: {sum(len(f) for f in datos[g].values())} filas')
    rng = random.Random(SEED + 1)
    franjas = 0
    for periodo, reservas in datos['Reservas'].items():
        filas = generar_horarios(reservas, periodo, rng)
        escribir_xlsx(SOURCE / 'horarios' / f'horarios{periodo}.xlsx', 'Citas', ENCABEZADOS_HORARIOS, filas)
        total += 1
        franjas += len(filas)
    print(f'horarios: {franjas} franjas')
    print(f'{total} libros en {SOURCE.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
