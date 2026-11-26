"""Convierte entregables/informe_entrega_1.md a entregables/informe_entrega_1.tex,
agregando la trazabilidad con la rubrica y la guia, y las secciones extra (4.6, SCD)."""
import re
import textwrap
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MD = RAIZ / "entregables" / "informe_entrega_1.md"
TEX = RAIZ / "entregables" / "latex" / "anexos_latex.tex"

ESC = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
       "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
UNI = {"×": r"$\times$", "→": r"$\rightarrow$", "∈": r"$\in$", "≠": r"$\neq$",
       "≥": r"$\geq$", "✔": r"$\checkmark$", "…": r"\ldots{}", "–": "--", "—": "---"}


def esc(s):
    return "".join(ESC.get(c, UNI.get(c, c)) for c in s)


def inline(s):
    partes, out, i = re.split(r"(`[^`]*`)", s), [], 0
    for p in partes:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            out.append(r"\texttt{" + esc(p[1:-1]).replace(r"\_", r"\_\allowbreak{}") + "}")
            continue
        t = esc(p)
        t = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", t)
        t = re.sub(r"(?<![\w*])\*(?!\*)(.+?)(?<!\*)\*(?![\w*])", r"\\emph{\1}", t)
        t = re.sub(r"(?<![\w\\])\\_(?!\\_)(.+?)(?<!\\)\\_(?![\w])", r"\\emph{\1}", t) if "_[" in p else t
        t = re.sub(r"!\[.*?\]\(.*?\)", "", t)
        out.append(t)
    return "".join(out)


def tabla(filas):
    celdas = [[c.strip() for c in f.strip().strip("|").split("|")] for f in filas]
    cab, sep, cuerpo = celdas[0], celdas[1], celdas[2:]
    n = len(cab)
    alin = ["r" if s.endswith(":") and not s.startswith(":") else ("c" if s.startswith(":") and s.endswith(":") else "l") for s in sep]
    ancho = [max(len(re.sub(r"[`*_]", "", r[j])) for r in [cab] + cuerpo) for j in range(n)]
    ancho = [max(len(w) for w in re.sub(r"[`*_]", "", r[j]).split() + [""]) if False else
             max(len(re.sub(r"[`*_]", "", r[j])) for r in cuerpo) for j in range(n)]
    cabmax = [max([len(w) for w in c.split()] + [1]) for c in cab]
    pesos = [max(6, min(ancho[j], 60), cabmax[j] + 2) ** 0.8 for j in range(n)]
    tot = sum(pesos)
    spec = ""
    for j in range(n):
        f = 0.93 * pesos[j] / tot
        al = {"r": r"\raggedleft", "c": r"\centering", "l": r"\raggedright"}[alin[j]]
        spec += r">{" + al + r"\arraybackslash}p{\dimexpr %.3f\textwidth-2\tabcolsep\relax}" % f
    tam = r"\footnotesize" if n >= 7 else r"\small"
    L = [r"\begingroup" + tam + r"\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.15}",
         r"\begin{longtable}{" + spec + "}", r"\toprule",
         " & ".join(r"\textbf{" + inline(c) + "}" for c in cab) + r" \\", r"\midrule", r"\endhead"]
    for r in cuerpo:
        r = r + [""] * (n - len(r))
        L.append(" & ".join(inline(c) for c in r[:n]) + r" \\")
    L += [r"\bottomrule", r"\end{longtable}", r"\endgroup", ""]
    return L


def convertir(md):
    L, lines, i, en_codigo, lista = [], md.split("\n"), 0, False, None
    def cerrar():
        nonlocal lista
        if lista:
            L.append(r"\end{%s}" % lista); lista = None
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            cerrar()
            if not en_codigo:
                L.append(r"\begingroup\footnotesize\begin{verbatim}"); en_codigo = True
            else:
                L.append(r"\end{verbatim}\endgroup"); en_codigo = False
            i += 1; continue
        if en_codigo:
            lc = ln.replace("→", "->").replace("–", "-").replace("—", "-").replace("≥", ">=").replace("≤", "<=")
            L.extend(textwrap.wrap(lc, 100, subsequent_indent="    ", break_long_words=False, drop_whitespace=False) or [""]); i += 1; continue
        if ln.startswith("|"):
            cerrar(); j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            L += tabla(lines[i:j]); i = j; continue
        m = re.match(r"(#{1,3}) (.*)", ln)
        if m:
            cerrar(); n, t = len(m.group(1)), m.group(2)
            if n == 1:
                i += 1; continue
            estrella = t.startswith("0.") or t.startswith("Anexo")
            t = re.sub(r"^(\d+(\.\d+)*\.?)\s+", "", t)
            cmd = r"\section*{" if estrella else (r"\section{" if n == 2 else (r"\subsection*{" if re.match(r"[A-Z]\.\d", t) else r"\subsection{"))
            L.append(cmd + inline(t) + "}")
            i += 1; continue
        m = re.match(r"!\[(.*?)\]\((.*?)\)", ln)
        if m:
            cerrar()
            L += [r"\begin{figure}[H]\centering",
                  r"\includegraphics[width=\textwidth,height=0.45\textheight,keepaspectratio]{" + m.group(2).split("/")[-1] + "}",
                  r"\caption{" + inline(m.group(1)) + "}", r"\end{figure}"]
            i += 1; continue
        if ln.strip() == "---":
            cerrar(); i += 1; continue
        m = re.match(r"(\s*)(-|\d+\.) (.*)", ln)
        if m:
            tipo = "itemize" if m.group(2) == "-" else "enumerate"
            if lista != tipo:
                cerrar(); L.append(r"\begin{%s}[leftmargin=1.5em,itemsep=2pt]" % tipo); lista = tipo
            L.append(r"\item " + inline(m.group(3))); i += 1; continue
        if ln.startswith(">"):
            cerrar(); L.append(r"\begin{quote}" + inline(ln.lstrip("> ")) + r"\end{quote}"); i += 1; continue
        if ln.strip() == "":
            cerrar(); L.append(""); i += 1; continue
        cerrar(); L.append(inline(ln)); i += 1
    cerrar()
    return "\n".join(L)


PREAMBULO = r"""\documentclass[11pt,letterpaper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[spanish,es-nodecimaldot]{babel}
\usepackage[margin=2.2cm]{geometry}
\usepackage{graphicx,float,booktabs,longtable,array,enumitem,amssymb}
\usepackage[hidelinks]{hyperref}
\usepackage{xcolor,fancyhdr}
% Permite compilar desde la carpeta del documento, entregables o el proyecto.
\graphicspath{{../img/}{img/}{entregables/img/}{../../img/}{../../entregables/img/}{../entregables/img/}}
\setlength{\parskip}{4pt}\setlength{\parindent}{0pt}
\pagestyle{fancy}\fancyhf{}
\fancyhead[L]{MINE-4214 · Proyecto Entrega 1}\fancyhead[R]{CupiTaller · Universidad de los Andes}
\fancyfoot[C]{\thepage}
\setcounter{secnumdepth}{2}
\begin{document}
\begin{center}
{\Large\bfseries Proyecto · Entrega 1\\[2pt] Reservas y satisfacción en CupiTaller}\\[8pt]
MINE-4214 Modelado y Diseño de Datos\\
Universidad de los Andes · Octubre de 2026\\[6pt]
\textbf{Integrantes:} \emph{María Alejandra Pérez Petro}, \emph{Santiago Martinez Novoa}
\end{center}
\tableofcontents
\bigskip
"""


def main():
    """Genera solo los anexos. El informe principal (informe_latex.tex) se edita a mano y no se regenera."""
    md = MD.read_text(encoding="utf-8")
    cuerpo = md[md.index("## Anexo A"):]
    pre = PREAMBULO.replace("Proyecto · Entrega 1\\\\[2pt] Reservas y satisfacción en CupiTaller", "Anexos del informe\\\\[2pt] Proyecto · Entrega 1 · CupiTaller")
    pre = pre.replace("\\tableofcontents\n", "\\tableofcontents\n\\vspace{4pt}\nAnexos del informe principal (\\texttt{informe\\_latex.tex}). Las referencias a secciones numeradas (por ejemplo, 3.6) remiten a ese informe, y las reglas de negocio R01 a R04 se definen en su sección 1.3 y en el glosario de este documento.\n")
    tex = pre + convertir(cuerpo) + "\n\\end{document}\n"
    TEX.write_text(tex, encoding="utf-8")
    print("escrito", TEX, len(tex))


main()
