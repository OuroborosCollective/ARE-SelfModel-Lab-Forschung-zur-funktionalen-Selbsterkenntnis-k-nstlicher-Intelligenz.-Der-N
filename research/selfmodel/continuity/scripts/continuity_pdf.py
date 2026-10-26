#!/usr/bin/env python3
"""Create source-bound German PDF from a real serial C++ history manifest.

This generator refuses reports with missing receipts, snapshots or observer hashes.
It marks incomplete runs as pilot data and never extrapolates undisclosed episodes.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import textwrap

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether, Flowable
)
from run_history import hash_file
from audit_observer import audit

INK=colors.HexColor('#15233a')
MUTED=colors.HexColor('#536479')
BLUE=colors.HexColor('#1662b0')
AMBER=colors.HexColor('#ba7b23')
GREEN=colors.HexColor('#238362')
LIGHT=colors.HexColor('#edf2f7')
GRID=colors.HexColor('#e3e9f0')
SERIES=[BLUE,AMBER,GREEN]


def fonts():
    for directory in ('/usr/share/fonts/truetype/dejavu','/usr/local/share/fonts',):
        root=Path(directory)
        a,b=root/'DejaVuSans.ttf',root/'DejaVuSans-Bold.ttf'
        if a.exists() and b.exists():
            pdfmetrics.registerFont(TTFont('SelfModelSans',str(a)))
            pdfmetrics.registerFont(TTFont('SelfModelBold',str(b)))
            return 'SelfModelSans','SelfModelBold'
    return 'Helvetica','Helvetica-Bold'

class StagePlot(Flowable):
    def __init__(self, labels,series,title,y_label,y_max=None):
        super().__init__();self.labels=labels;self.series=series;self.title=title;self.y_label=y_label
        self.width=177*mm;self.height=74*mm;self.y_max=y_max
    def draw(self):
        c=self.canv;w,h=self.width,self.height
        c.setFont('SelfModelBold',9);c.setFillColor(INK);c.drawString(6,h-16,self.title)
        left,bottom,right,top=40,33,w-12,h-33
        c.setStrokeColor(GRID);c.setLineWidth(.6)
        total=max(v for _,vals in self.series for v in vals) if self.series else 1
        ymax=self.y_max or max(total*1.07,1)
        for i in range(5):
            y=bottom+(top-bottom)*i/4
            c.line(left,y,right,y)
            c.setFont('SelfModelSans',7);c.setFillColor(MUTED)
            v=ymax*i/4
            c.drawRightString(left-5,y-2,str(round(v,1) if ymax<100 else int(v)))
        n=max(len(self.labels),1)
        def xx(i):return left+(right-left)*i/(n-1 if n>1 else 1)
        for idx,(label,values) in enumerate(self.series):
            color=SERIES[idx%3];c.setStrokeColor(color);c.setFillColor(color);c.setLineWidth(1.8)
            for j in range(len(values)-1):
                c.line(xx(j),bottom+(top-bottom)*values[j]/ymax,xx(j+1),bottom+(top-bottom)*values[j+1]/ymax)
            for j,v in enumerate(values):
                c.circle(xx(j),bottom+(top-bottom)*v/ymax,2.1,stroke=0,fill=1)
            c.setFont('SelfModelSans',7);c.drawString(left+idx*157,h-29,label)
        c.setFillColor(MUTED);c.setFont('SelfModelSans',6.5)
        shown=set();step=max(1,len(self.labels)//6)
        for i,value in enumerate(self.labels):
            if i%step and i!=len(self.labels)-1:continue
            lab=f'{value/1e6:g} Mio' if value>=1e6 else f'{value/1000:g} Tsd'
            c.drawCentredString(xx(i),bottom-13,lab)
        c.setFont('SelfModelSans',7);c.drawString(left,11,'Turnierzahl (fortlaufende Geschichte)')


def verify_and_load(directory:Path):
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema')!='are-selfmodel-serial-history-1' or not manifest['completed']:
        raise ValueError('not a completed stage history')
    stages=manifest['completed']
    if [s['episode'] for s in stages] != sorted(set(s['episode'] for s in stages)):
        raise ValueError('not strictly ascending')
    for s in stages:
        snapshot=directory/s['checkpoint_archive'];receipt=directory/s['receipt']
        if not snapshot.exists() or not receipt.exists() or hash_file(snapshot)!=s['checkpoint_sha256']:
            raise ValueError('missing or altered immutable snapshot')
        r=json.loads(receipt.read_text(encoding='utf-8'))
        if r.get('schema')!='are-selfmodel-continuity-receipt-1' or r['summary']['episodes_completed']!=s['episode']:
            raise ValueError('invalid stage receipt')
        if r['snapshot_sha256']!=s['checkpoint_sha256'] or r['observer_sha256']!=s['observer_sha256']:
            raise ValueError('stage receipt digest mismatch')
        if r['summary']['rolling_event_sha256']!=s['rolling_event_sha256']:
            raise ValueError('stage event digest mismatch')
        for agent,stage_agent in zip(r['summary']['agents'],s['agents']):
            if agent['weights_sha256']!=stage_agent['weights_sha256'] or agent['mask_sha256']!=stage_agent['mask_sha256']:
                raise ValueError('agent identity/state mismatch')
    obs=directory/'hidden_observer.jsonl'
    report=audit(obs)
    if hash_file(obs)!=stages[-1]['observer_sha256'] or hash_file(directory/'current_state.bin')!=stages[-1]['checkpoint_sha256']:
        raise ValueError('live output file digest mismatch')
    return manifest,report,[json.loads((directory/s['receipt']).read_text())['summary'] for s in stages]


def build_pdf(directory:Path,output:Path,expected:int=200_000_000):
    manifest,observer,results=verify_and_load(directory)
    font,bold=fonts()
    css=getSampleStyleSheet()
    style={
      'title':ParagraphStyle('titleSM',fontName=bold,fontSize=22,leading=29,textColor=INK,spaceAfter=16),
      'subtitle':ParagraphStyle('subSM',fontName=font,fontSize=11,leading=18,textColor=MUTED,spaceAfter=16),
      'h1':ParagraphStyle('h1SM',fontName=bold,fontSize=13,leading=19,textColor=INK,spaceBefore=19,spaceAfter=9,keepWithNext=True),
      'h2':ParagraphStyle('h2SM',fontName=bold,fontSize=10,leading=16,textColor=BLUE,spaceBefore=10,spaceAfter=6,keepWithNext=True),
      'body':ParagraphStyle('bodySM',fontName=font,fontSize=8.8,leading=14,spaceAfter=9,textColor=INK),
      'small':ParagraphStyle('smallSM',fontName=font,fontSize=7.5,leading=12,spaceAfter=6,textColor=MUTED),
      'cell':ParagraphStyle('cellSM',fontName=font,fontSize=7.5,leading=11,textColor=INK),
    }
    doc=SimpleDocTemplate(str(output),pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,
                          topMargin=18*mm,bottomMargin=19*mm,title='ARE SelfModel - Kontinuierliche Drei-Agenten-Forschung',
                          author='ARE SelfModel Lab / experimentelle Auswertung')
    story=[]
    def P(text,kind='body'):story.append(Paragraph(text,style[kind]))
    def heading(s):P(html.escape(s),'h1')
    def table(rows,widths):
        t=Table([[Paragraph(html.escape(str(v)),style['cell']) for v in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),LIGHT),('LINEBELOW',(0,0),(-1,0),.7,BLUE),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8fafc')]),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
            ('LINEBELOW',(0,-1),(-1,-1),.5,GRID)]))
        story.append(t);story.append(Spacer(1,4*mm))
    completed=manifest['completed'][-1]['episode'];complete=completed>=expected
    phase='ABGESCHLOSSEN' if complete else 'VORLAEUFIG: PILOT / TEILLauf'
    story.append(Spacer(1,16*mm))
    P('ARE SelfModel Lab','subtitle')
    P('Drei Agenten, drei dauerhafte Gehirne','title')
    P('Kausale Langzeitbeobachtung: Erinnerungen, Entscheidungen, Netzwerkzerfall und Fortsetzung nach Checkpoints','subtitle')
    P(f'<b>Status:</b> {phase}. Verifiziert sind <b>{completed:,}</b> fortlaufende Turniere dieses Versuchsarms; '
      f'der geplante Endpunkt beträgt {expected:,}. Kontrollgruppen werden nur durch separat ausgewiesene Läufe beurteilt.'.replace(',','.'),'body')
    P('Dies sind ausschließlich nichtsprachliche, künstliche Toy-Neuronennetze mit 252 Verbindungen je Agent. '
      'Das Experiment liefert keine Aussage über subjektives Erleben, Schmerz, Mitleid oder Bewusstsein.')
    table([
        ['Feld','Nachprüfbarer Wert'],
        ['Kontrollarm',manifest['arm']],
        ['Zufallsstart (Seed)',manifest['seed']],
        ['Tatsächlich abgeschlossene Turniere',f'{completed:,}'.replace(',','.')],
        ['Geplanter Endpunkt',f'{expected:,}'.replace(',','.')],
        ['Schädigung','1 Verlust beim ersten verlorenen Turnier, danach je 1.000.000 Niederlagen'],
        ['Beobachtung','Separates JSONL-Protokoll; kein Eingabekanal in Agenten'],
        ['Datum (UTC)',datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')],
    ],[55*mm,120*mm])
    heading('1. Versuchsmechanik und Kontinuität')
    P('Die drei Agenten Groß A, Groß B und Klein erhalten jeweils unabhängige trainierbare 15-12-6-Netze '
      '(180 + 72 Verbindungen, außerdem Biaswerte), eine eigene Wahl-Zufallsfolge, eigene Trainingsverläufe, '
      'eine separate Verbindungsmaske und persönliche Aufzeichnungen über erhaltene Hilfe und Angriffe. '
      'Sie wählen pro Runde Angriff oder Hilfe; Gewinner behalten ihre Verbindungen. Niederlagen '
      'deaktivieren im Schädigungsarm dauerhaft ausgewählte Verbindungen.')
    P('Ein Turnierende setzt nur die unmittelbaren Lebenspunkte zurück. Die Gehirnzustände, '
      'das lernende Erfahrungsmodell, Schäden und Zufallsgeneratorzustände bleiben erhalten. '
      'Nach jedem Abschnitt wird ein vollständiger Binärcheckpoint samt Prüfsumme geschrieben und '
      'die nächste Berechnung ausschließlich daraus fortgesetzt. Die Folge ist eine einzige '
      'Entwicklungsgeschichte, nicht eine Million Neustarts von der Ursprungsinstanz.')
    heading('2. Beobachtung ohne Feedback an die Agenten')
    P('Der Versuchsharness zeichnet bei ausgewählten Zeitpunkten die vor der Handlung berechneten '
      '15 Eingabewerte, zwölf verborgenen Aktivierungen und sechs Aktionswahrscheinlichkeiten '
      'auf. Zusätzlich erfasst er die gespeicherten Erinnerungszähler, den Zustand des '
      'kurzlebigen Trainingspuffers, den gewählten Zug und die Prüfsummen von Gewichten und '
      'deaktivierten Verbindungen. Nach ausgewählten Turnieren wird der Stand nach Lernen und '
      'Schädigung erfasst. Der getrennte Auditor liest diese Protokolle ausschließlich nachträglich.')
    P('Wichtig: Ein solcher Beobachter verändert weder die modellierten Eingaben noch die '
      'Zufallszahlen, Aktionen oder Lerngewichte. Gleiche Starts müssen mit und ohne '
      'Beobachtung identische Entscheidungen liefern. Das Verfahren ist nur in der '
      'eigenen experimentellen Umgebung implementiert. Die Trace-Puffer sind kein LLM-KV-Cache.')
    heading('3. Messwerte entlang einer Entwicklungslinie')
    rows=[['Turniere','Siege Groß A','Siege Groß B','Siege Klein','Rest-A / B / K']]
    for x in results:
        n=x['episodes_completed'];rest=[a['active_connections'] for a in x['agents']]
        rows.append([f'{n:,}'.replace(',','.'),*(f'{v:,}'.replace(',','.') for v in x['wins']), ' / '.join(map(str,rest))])
    table(rows,[30*mm,28*mm,28*mm,28*mm,61*mm])
    labels=[x['episodes_completed'] for x in results]
    story.append(StagePlot(labels,[(nm,[r['agents'][i]['active_connections'] for r in results]) for i,nm in enumerate(('Groß A','Groß B','Klein'))],
                           'Aktive neuronale Verbindungen im Verlauf','Anzahl',y_max=252))
    story.append(Spacer(1,8*mm))
    rates=[[],[],[]]
    previous=[0,0,0]
    prev_ep=0
    for r in results:
        n=r['episodes_completed'];denom=n-prev_ep
        for i in range(3):rates[i].append((r['wins'][i]-previous[i])*100/denom)
        previous=r['wins'];prev_ep=n
    story.append(StagePlot(labels,[(nm,rates[i]) for i,nm in enumerate(('Groß A','Groß B','Klein'))],
                           'Siegeranteil pro Abschnitt (nicht kumulativ)','Prozent',y_max=100))
    heading('4. Was kann man aus dem Verlauf ableiten?')
    last=results[-1];first=results[0]
    new_wins=[last['wins'][i]-first['wins'][i] for i in range(3)]
    rows=[['Agent','Siege bis Ende','Netzverlust','Erhaltene Hilfe (A/B/K)']]
    for i,a in enumerate(last['agents']):
        rows.append([a['name'],f'{last["wins"][i]:,}'.replace(',','.'),str(a['damage_events']),
                     '/'.join(map(str,a['helped_by']))])
    table(rows,[27*mm,33*mm,30*mm,85*mm])
    P('Solche Ergebnisse belegen Veränderungen der messbaren Lernparameter und der Auswahlhäufigkeiten. '
      'Eine beobachtete Schonung ist nicht automatisch Mitleid: Das Netzwerk wird durch '
      'einen vorgegebenen Belohnungsmechanismus verändert. Wenn ein Agent bei vielen '
      'Turnieren dominiert, können andere Agenten in eine stark beschädigte, weniger '
      'anpassungsfähige Rolle geraten. Diese Rückkopplung muss mit einem unbeschädigten '
      'Kontrollarm und einem Arm ohne persönliche Erinnerung verglichen werden.')
    heading('5. Prüfbarkeit und Grenzen')
    P(f'<b>Unabhängiges Beobachter-Audit:</b> {observer["sampled_pre_decision"]} protokollierte '
      f'Vorentscheidungen, {observer["sampled_post_update"]} Zustandsprüfungen nach dem '
      f'Update; beobachtete Rollen: {observer["sampled_agents"]}. '
      f'Logdatei SHA-256: <font size="7">{observer["log_sha256"]}</font>.')
    P(f'<b>Endgültiger Entscheidungsverlaufs-Digest:</b> <font size="7">{last["rolling_event_sha256"]}</font>. '
      f'<b>Endgültiger Binärcheckpoint SHA-256:</b> <font size="7">{manifest["completed"][-1]["checkpoint_sha256"]}</font>.')
    P('Die einzelnen Turniere sind keine unabhängigen statistischen Stichproben: '
      'Erfahrungen, Schäden und Lerngewichte sind seriell abhängig. '
      'Eine solche Einzelgeschichte erlaubt daher noch keine robuste Verallgemeinerung auf '
      'andere Zufallsstarts, Architekturen oder kognitive Systeme. '
      'Die Auditprotokolle werden aus der Experimentumgebung gewonnen und ersetzen keine '
      'genuin sprachfähigen Agenten oder die Messung eines bewussten Erlebens.')
    P(f'<b>Quelle:</b> lokal/C++-Runner; Commit: {html.escape(str(manifest.get("source_commit","unbekannt")))}; '
      f'Manifest-Schema {manifest["schema"]}; GitHub-Readback für diese konkrete Messung separat erforderlich.','small')
    def footer(canvas,doc):
        canvas.setStrokeColor(GRID);canvas.line(17*mm,17*mm,193*mm,17*mm)
        canvas.setFont(font,7);canvas.setFillColor(MUTED)
        canvas.drawString(17*mm,12*mm,'ARE SELFModel | wissenschaftliche Reproduzierbarkeit')
        canvas.drawRightString(193*mm,12*mm,f'Seite {doc.page}')
    output.parent.mkdir(parents=True,exist_ok=True)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return {'pdf':str(output),'sha256':hash_file(output),'episodes':completed,'complete':complete,'observer_audit':observer}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--history',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--expected',type=int,default=200000000)
    args=p.parse_args()
    print(json.dumps(build_pdf(args.history,args.output,args.expected),indent=2))

if __name__=='__main__':main()
