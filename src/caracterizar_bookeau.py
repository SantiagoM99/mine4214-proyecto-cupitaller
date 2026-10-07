"""Characterize original Bookeau workbooks without changing them.

Uses Python's standard library. Run from anywhere with Python 3.9+.
Excel cells are aligned by their coordinates, including missing cells.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import statistics
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# CUPITALLER_FUENTE: carpeta de los Excel, relativa a ROOT. Por defecto, los datos reales;
# con `main.py --dummy` apunta a data/bronce/dummy.
SOURCE = ROOT / os.environ.get('CUPITALLER_FUENTE', 'data/bronce/Bookeau')
OUTPUT = ROOT / 'docs/artifacts/caracterizacion'
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
DATE_COLUMNS = ['Fecha inicio', 'Fecha fin', 'Fecha de llegada', 'Fecha de devolución']
SAFE_CATEGORIES = {'Estado de la reserva', 'Prioritaria', 'Categoría', 'Tipo de horario', 'Servicio', 'Código servicio', 'Código del servicio', 'Tipo de usuario', 'Programa', 'Estado'}
TEXT_MARKERS = ('comente', 'escriba', 'sugerencias', 'indique cuál')
DATE_FORMAT_IDS = set(range(14, 23)) | set(range(45, 48))


def column_index(reference):
    result = 0
    for letter in re.match(r'[A-Z]+', reference).group():
        result = result * 26 + ord(letter) - ord('A') + 1
    return result - 1


def read_workbook(path, include_source_row=False):
    """Yield (sheet name, headers, records) with sparse cells correctly aligned."""
    with zipfile.ZipFile(path) as archive:
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            with archive.open('xl/sharedStrings.xml') as stream:
                for _, element in ET.iterparse(stream, events=('end',)):
                    if element.tag == NS + 'si':
                        strings.append(''.join(t.text or '' for t in element.iter(NS + 't')))
                        element.clear()
        styles = ET.fromstring(archive.read('xl/styles.xml'))
        custom = {int(e.get('numFmtId')): e.get('formatCode', '') for e in styles.iter(NS + 'numFmt')}
        formats = [int(e.get('numFmtId', '0')) for e in styles.find(NS + 'cellXfs')]
        is_1904 = False
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        props = workbook.find(NS + 'workbookPr')
        if props is not None:
            is_1904 = props.get('date1904') in {'1', 'true'}
        relations = {e.get('Id'): e.get('Target') for e in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
        for sheet in workbook.iter(NS + 'sheet'):
            target = relations[sheet.get(REL + 'id')]
            target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            headers, records = None, []
            with archive.open(target) as stream:
                for _, element in ET.iterparse(stream, events=('end',)):
                    if element.tag != NS + 'row':
                        continue
                    values = {}
                    for cell in element:
                        value_element = cell.find(NS + 'v')
                        kind = cell.get('t', 'n')
                        value = value_element.text if value_element is not None else None
                        if kind == 'inlineStr':
                            value = ''.join(t.text or '' for t in cell.iter(NS + 't'))
                        elif kind == 's' and value is not None:
                            value = strings[int(value)]
                        elif kind == 'b' and value is not None:
                            value = value == '1'
                        elif kind == 'n' and value is not None:
                            number = float(value)
                            fmt = formats[int(cell.get('s', '0'))]
                            code = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', '', custom.get(fmt, ''))
                            if fmt in DATE_FORMAT_IDS or re.search(r'[ydhs]', code, re.I):
                                epoch = datetime(1904, 1, 1) if is_1904 else datetime(1899, 12, 30)
                                value = epoch + timedelta(days=number)
                            else:
                                value = int(number) if number.is_integer() else number
                        if value is not None and value != '':
                            values[column_index(cell.get('r'))] = value
                    if values:
                        if headers is None:
                            headers = [str(values.get(i, '')).strip() for i in range(max(values) + 1)]
                            if len(set(headers)) != len(headers) or '' in headers:
                                raise ValueError(f'Nonunique or empty headers: {path}')
                        else:
                            if max(values) >= len(headers):
                                raise ValueError(f'Values beyond headers: {path}, row {element.get("r")}')
                            record = {h: values.get(i) for i, h in enumerate(headers)}
                            if include_source_row:
                                record['__fila_excel__'] = int(element.get('r'))
                            records.append(record)
                    element.clear()
            yield sheet.get('name'), headers or [], records


def missing(value):
    return value is None or isinstance(value, str) and not value.strip()


def serializable(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=' ', timespec='microseconds')
    return value


def write_csv(name, records):
    if not records:
        return
    with (OUTPUT / name).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def characterize():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    by_group = defaultdict(list)
    files = []
    signatures = defaultdict(Counter)
    for path in sorted(SOURCE.rglob('*.xlsx')):
        period = re.search(r'(\d{6})\.xlsx$', path.name).group(1)
        for sheet, headers, records in read_workbook(path):
            group = path.parent.name
            files.append({'grupo': group, 'archivo': str(path.relative_to(ROOT)), 'hoja': sheet, 'periodo': period, 'filas': len(records), 'variables': len(headers)})
            signatures[group][tuple(headers)] += 1
            for record in records:
                by_group[group].append((period, record))
        print('Read', path.name, flush=True)
    variables, categories, summaries, period_counts, quality, text_stats = [], [], [], [], [], []
    all_id_maps = {}
    temporal_coverage, arrival_states, category_variants, answer_rules = [], [], [], []
    for group, records in by_group.items():
        n = len(records)
        columns = list(signatures[group].most_common(1)[0][0])
        ids, period_ids = Counter(), Counter()
        seen_rows = Counter()
        id_map = defaultdict(list)
        date_rules = {rule: [0, 0] for rule in ['fin_anterior_a_inicio', 'devolucion_anterior_a_llegada', 'inicio_fuera_anio_periodo']}
        start_dates, durations = [], []
        for period, record in records:
            identifier = record.get('ID')
            if not missing(identifier):
                ids[identifier] += 1
                period_ids[(period, identifier)] += 1
                id_map[identifier].append((period, record))
            fingerprint = hashlib.sha256(repr(tuple(record.get(c) for c in columns)).encode()).hexdigest()
            seen_rows[fingerprint] += 1
            start, end, arrival, departure = (record.get(c) for c in DATE_COLUMNS)
            if isinstance(start, datetime):
                start_dates.append(start)
                date_rules['inicio_fuera_anio_periodo'][0] += 1
                date_rules['inicio_fuera_anio_periodo'][1] += start.year != int(period[:4])
            if isinstance(start, datetime) and isinstance(end, datetime):
                date_rules['fin_anterior_a_inicio'][0] += 1
                date_rules['fin_anterior_a_inicio'][1] += end < start
                durations.append((end - start).total_seconds() / 60)
            if isinstance(arrival, datetime) and isinstance(departure, datetime):
                date_rules['devolucion_anterior_a_llegada'][0] += 1
                date_rules['devolucion_anterior_a_llegada'][1] += departure < arrival
        all_id_maps[group] = id_map
        for period in sorted({f['periodo'] for f in files if f['grupo'] == group}):
            subset = [r for p, r in records if p == period]
            for column in columns:
                filled = sum(not missing(r.get(column)) for r in subset)
                temporal_coverage.append({'grupo': group, 'periodo': period, 'variable': column, 'filas': len(subset), 'no_vacios': filled, 'porcentaje_no_vacios': round(100*filled/len(subset),4) if subset else ''})
        if group == 'Reservas':
            for state in sorted({r['Estado de la reserva'] for _,r in records}):
                subset = [r for _,r in records if r['Estado de la reserva'] == state]
                filled = sum(not missing(r.get('Fecha de llegada')) for r in subset)
                arrival_states.append({'estado_reserva':state,'filas':len(subset),'con_llegada':filled,'sin_llegada':len(subset)-filled,'porcentaje_con_llegada':round(100*filled/len(subset),4)})
        summaries.append({'grupo': group, 'archivos': len({f['archivo'] for f in files if f['grupo'] == group}), 'filas': n, 'variables': len(columns), 'variantes_encabezado': len(signatures[group]), 'id_distintos': len(ids), 'id_faltantes': n-sum(ids.values()), 'filas_excedentes_id_repetido': sum(v-1 for v in ids.values()), 'filas_excedentes_id_periodo_repetido': sum(v-1 for v in period_ids.values()), 'filas_excedentes_duplicado_exacto': sum(v-1 for v in seen_rows.values()), 'inicio_min': serializable(min(start_dates)) if start_dates else '', 'inicio_max': serializable(max(start_dates)) if start_dates else '', 'duracion_programada_min_minutos': min(durations) if durations else '', 'duracion_programada_mediana_minutos': statistics.median(durations) if durations else '', 'duracion_programada_max_minutos': max(durations) if durations else ''})
        for (period, count) in sorted(Counter(p for p, _ in records).items()):
            period_counts.append({'grupo': group, 'periodo': period, 'filas': count})
        for rule, (evaluated, violations) in date_rules.items():
            quality.append({'grupo': group, 'regla': rule, 'evaluables': evaluated, 'incumplimientos': violations, 'porcentaje_evaluables': round(100*violations/evaluated, 4) if evaluated else ''})
        for column in columns:
            values = [r.get(column) for _, r in records]
            present = [v for v in values if not missing(v)]
            counts = Counter(present)
            types = Counter(type(v).__name__ for v in present)
            dates = [v for v in present if isinstance(v, datetime)]
            numbers = [v for v in present if isinstance(v, (int, float)) and not isinstance(v, bool)]
            is_text = column.lower().startswith(TEXT_MARKERS)
            role = 'texto libre' if is_text else 'fecha/hora' if column in DATE_COLUMNS else 'identificador' if column in {'ID', 'Código usuario', 'Código servicio', 'Código del servicio', 'Correo usuario'} else 'atributo personal' if column in {'Usuario', 'Prestador del servicio'} else 'categoría o respuesta'
            if role == 'identificador':
                numbers = []
            variables.append({'grupo': group, 'variable': column, 'rol_inicial': role, 'tipos_observados': json.dumps(types, ensure_ascii=False), 'filas': n, 'no_vacios': len(present), 'faltantes': n-len(present), 'porcentaje_faltantes': round(100*(n-len(present))/n,4) if n else '', 'valores_distintos': len(counts), 'fecha_min': serializable(min(dates)) if dates else '', 'fecha_max': serializable(max(dates)) if dates else '', 'numerico_min': min(numbers) if numbers else '', 'numerico_max': max(numbers) if numbers else '', 'numerico_media': statistics.mean(numbers) if numbers else ''})
            if column == 'Califique la ayuda que le dio su tutor':
                invalid = 0
                for value in present:
                    try:
                        invalid += float(value) not in {1,2,3,4,5}
                    except (TypeError, ValueError):
                        invalid += 1
                answer_rules.append({'grupo':group,'variable':column,'regla':'valor entero entre 1 y 5 (dominio candidato observado)','no_vacios_evaluados':len(present),'fuera_dominio':invalid,'faltantes':n-len(present)})
            if column in SAFE_CATEGORIES and column != 'Estado':
                normalized = defaultdict(list)
                for value,count in counts.items():
                    if not isinstance(value,str):
                        continue
                    key = ' '.join(''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c)).split())
                    normalized[key].append((value,count))
                for key, variants in normalized.items():
                    if len(variants)>1:
                        category_variants.append({'grupo':group,'variable':column,'valor_normalizado_candidato':key,'variantes_originales_json':json.dumps(variants,ensure_ascii=False),'filas':sum(n for _,n in variants)})
            if is_text:
                lengths = [len(str(v)) for v in present]
                text_stats.append({'grupo': group, 'variable': column, 'respuestas_no_vacias': len(present), 'porcentaje_cobertura': round(100*len(present)/n,4) if n else '', 'textos_distintos': len(counts), 'longitud_min': min(lengths) if lengths else '', 'longitud_mediana': statistics.median(lengths) if lengths else '', 'longitud_max': max(lengths) if lengths else ''})
            elif column in SAFE_CATEGORIES or column not in set(columns[:18]):
                for value, count in counts.most_common():
                    categories.append({'grupo': group, 'variable': column, 'valor': serializable(value), 'frecuencia': count, 'porcentaje_filas': round(100*count/n,4) if n else ''})
        print('Profiled', group, flush=True)
    links, agreement = [], []
    reservations = all_id_maps['Reservas']
    for group, mapping in all_id_maps.items():
        if group == 'Reservas':
            continue
        common = set(mapping) & set(reservations)
        n = sum(len(v) for v in mapping.values())
        matched = sum(len(mapping[key]) for key in common)
        period_matches = sum(any(p == rp for rp, _ in reservations[key]) for key in common for p, _ in mapping[key])
        links.append({'grupo_encuesta': group, 'filas_con_id': n, 'id_distintos': len(mapping), 'id_en_reservas': len(common), 'filas_con_id_en_reservas': matched, 'filas_sin_id_en_reservas': n-matched, 'filas_con_id_y_periodo_en_reservas': period_matches, 'porcentaje_filas_con_id_en_reservas': round(100*matched/n,4) if n else ''})
        checks = defaultdict(lambda: [0,0])
        for key in common:
            # Only compare records with an unambiguous reservation in the same period.
            for period, record in mapping[key]:
                candidates = [r for p, r in reservations[key] if p == period]
                if len(candidates) != 1:
                    continue
                canonical = candidates[0]
                for column in canonical:
                    survey_column = 'Código del servicio' if column == 'Código servicio' else column
                    a, b = canonical[column], record.get(survey_column)
                    if missing(a) or missing(b):
                        continue
                    checks[column][0] += 1
                    equal = abs((a-b).total_seconds()) <= 1 if isinstance(a,datetime) and isinstance(b,datetime) else a == b
                    checks[column][1] += not equal
        for column,(compared,different) in checks.items():
            agreement.append({'grupo_encuesta':group,'variable':column,'pares_no_vacios_comparados':compared,'diferencias':different,'porcentaje_diferencias':round(100*different/compared,4) if compared else ''})
    datasets = {'archivos.csv': files, 'resumen_grupos.csv': summaries, 'variables.csv': variables, 'categorias.csv': categories, 'periodos.csv': period_counts, 'reglas_fechas.csv': quality, 'texto_libre.csv': text_stats, 'vinculos_reservas_encuestas.csv': links, 'consistencia_entre_fuentes.csv': agreement, 'cobertura_variables_periodo.csv': temporal_coverage, 'estado_llegada.csv': arrival_states, 'variantes_categoricas.csv': category_variants, 'reglas_respuestas.csv': answer_rules}
    for name, records in datasets.items():
        write_csv(name, records)
    schema = {g: [{'archivos': n, 'columnas': list(h)} for h,n in counts.items()] for g,counts in signatures.items()}
    (OUTPUT/'esquemas.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'resumen': summaries, 'vinculos': links, 'fechas': quality, 'textos':text_stats},ensure_ascii=False,indent=2), flush=True)
    return datasets


if __name__ == '__main__':
    characterize()
