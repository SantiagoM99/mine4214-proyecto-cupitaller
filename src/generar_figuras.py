"""Draw the report figures (analytics ecosystem and dimensional star models) into img/."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from limpiar_bookeau import ROOT

OUT=ROOT/'img'
INK='#17243a'
MUTED='#526177'
FACT='#356db8'
DIM='#e8eef6'
TEAM='#fff3d6'
EDGE='#9fb0c5'


def box(ax,x,y,w,h,title,lines=(),fill=DIM,ink=INK,title_size=11,dashed=False):
    ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=0.02,rounding_size=0.08',
        fc=fill,ec=EDGE if fill!=FACT else FACT,lw=1.2,ls='--' if dashed else '-'))
    top=y+h/2-0.17
    ax.text(x,top,title,ha='center',va='top',fontsize=title_size,fontweight='bold',color=ink)
    for i,line in enumerate(lines):
        ax.text(x,top-0.32-0.24*i,line,ha='center',va='top',fontsize=8.5,color=ink if fill==FACT else MUTED)


def arrow(ax,a,b,dashed=False,text=None):
    ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='-|>',color=MUTED,lw=1.3,ls='--' if dashed else '-',shrinkA=2,shrinkB=2))
    if text:ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+0.12,text,ha='center',fontsize=8,color=MUTED)


def canvas(w,h):
    fig,ax=plt.subplots(figsize=(w,h),dpi=200)
    ax.set_xlim(0,w);ax.set_ylim(0,h);ax.axis('off')
    return fig,ax


def ecosystem():
    fig,ax=canvas(14.4,6.2)
    stages=[(1.2,'Bookeau',['Reservas y','encuestas'],DIM),
            (3.5,'Exportación',['Excel por período','(coordinación)'],DIM),
            (5.9,'Bronze',['114 Excel originales','ZIP intacto'],TEAM),
            (8.3,'Silver',['5 CSV limpios','banderas, R01/R02'],TEAM),
            (10.7,'Gold',['Modelo dimensional','SQLite: 3 hechos'],TEAM),
            (13.0,'Consumo',['Tablero HTML','consultas SQL'],TEAM)]
    for x,t,l,f in stages:box(ax,x,3.6,2.0,1.3,t,l,fill=f)
    for (x1,*_),(x2,*_) in zip(stages,stages[1:]):arrow(ax,(x1+1.0,3.6),(x2-1.0,3.6))
    box(ax,8.3,1.35,7.4,0.85,'Calidad y metadatos',['Diccionarios, reglas de negocio, bitácora, conciliación por capa, controles de integridad'],fill=TEAM)
    for x in (5.9,8.3,10.7):arrow(ax,(x,2.95),(x,1.8))
    box(ax,3.5,5.55,2.6,0.8,'Oferta y capacidad',['fuente no disponible'],dashed=True,title_size=9.5)
    arrow(ax,(4.8,5.55),(5.9,4.45),dashed=True,text='futura')
    ax.add_patch(FancyBboxPatch((0.25,0.1),0.35,0.25,boxstyle='round,pad=0.01',fc=TEAM,ec=EDGE))
    ax.text(0.7,0.22,'Componente intervenido por el equipo',va='center',fontsize=8.5,color=MUTED)
    fig.savefig(OUT/'ecosistema.png',bbox_inches='tight');plt.close(fig)


def star(name,fact,measures,dims,extra=None,size=(13,8.5),extra_w=0):
    w,h=size
    fig,ax=canvas(w+extra_w,h)
    cx,cy=w/2,h/2
    import math
    rx,ry=w/2-1.7,h/2-1.0
    n=len(dims)
    for i,(title,lines) in enumerate(dims):
        ang=math.pi/2-2*math.pi*i/n
        x,y=cx+rx*math.cos(ang),cy+ry*math.sin(ang)
        ax.plot([cx,x],[cy,y],color=EDGE,lw=1.2,zorder=0)
        box(ax,x,y,2.9,0.55+0.24*len(lines)+0.15,title,lines)
    box(ax,cx,cy,3.3,0.75+0.24*len(measures),fact,measures,fill=FACT,ink='white',title_size=12)
    if extra:extra(ax,cx,cy)
    fig.savefig(OUT/name,bbox_inches='tight');plt.close(fig)


def stars():
    star('modelo_reserva.png','HECHO_RESERVA',
         ['Grano: un evento de reserva','id_reserva (degenerada)','evento_reserva = 1','minutos_programados','es_prioritaria'],
         [('Fecha',['roles: inicio · fin · llegada','día → mes → año','nombre del día · fin de semana']),
          ('Hora',['minuto → hora → franja']),
          ('Período',['código → tipo → año','Semestre 1/2 · Intersemestral']),
          ('Servicio',['código + etiqueta original']),
          ('Modalidad',['tipo de horario','categoría original']),
          ('Estado',['original → analítico (R01)','→ grupo (D1)']),
          ('Programa',['programa normalizado','0 = No informado'])])

    def detail(ax,cx,cy):
        rx,ry=cx+9.3,cy-3.9
        box(ax,rx,ry,3.3,1.25,'HECHO_RESPUESTA',['Grano: pregunta no vacía','de una encuesta','valor_original · valor_numérico'],fill=FACT,ink='white',title_size=10)
        box(ax,rx,cy-1.4,3.0,0.95,'Pregunta',['texto completo','texto libre / calificación'])
        ax.plot([rx,rx],[cy-1.88,ry+0.63],color=EDGE,lw=1.2)
        ax.plot([cx+1.62,cx+1.62],[cy-0.98,ry],color=FACT,lw=1.6)
        ax.annotate('',xy=(rx-1.65,ry),xytext=(cx+1.62,ry),arrowprops=dict(arrowstyle='-|>',color=FACT,lw=1.6))
        ax.text(cx+6.2,ry+0.12,'1 : N  (detalle de la encuesta)',ha='center',fontsize=9,color=MUTED)
    star('modelo_encuesta.png','HECHO_ENCUESTA',
         ['Grano: una encuesta válida','de una reserva (R02)','id_reserva (degenerada)','respuesta_encuesta = 1','calificación 1–5 (nullable)'],
         [('Tipo de encuesta',['grupo de fuente','etapa: previa / posterior']),
          ('Fecha',['fecha del evento reservado','día → mes → año']),
          ('Hora',['minuto → hora → franja']),
          ('Período',['código → tipo → año']),
          ('Servicio',['conformada con Reserva']),
          ('Modalidad',['conformada con Reserva']),
          ('Estado',['estado de la reserva','conformada (R01, D1)']),
          ('Programa',['conformada con Reserva'])],
         extra=detail,size=(15,9.5),extra_w=4.8)


if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    ecosystem();stars()
    print('Figuras en',OUT)
