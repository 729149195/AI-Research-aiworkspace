"""Portable scientific figure recipes. Data in; inspectable SVG/PDF/PNG out.

No network, arbitrary expressions, external TeX, hidden filtering, or inference.
This file is copied into each local provenance bundle for standalone regeneration.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import math
from pathlib import Path
import random
import statistics
import textwrap
import warnings

KINDS = ('scatter', 'line', 'distribution', 'paired', 'interval', 'heatmap', 'workflow')
ALLOWED = {'id', 'kind', 'input', 'title', 'purpose', 'caption', 'alt_text', 'claims', 'evidence',
           'x', 'y', 'group', 'pair_id', 'label', 'lower', 'upper', 'interval_definition',
           'row', 'column', 'value', 'xlabel', 'ylabel', 'unit', 'width_mm', 'height_mm',
           'font_family', 'font_size', 'dpi', 'missing', 'omission_reason', 'steps', 'workflow_status'}
MISSING = {'', 'na', 'n/a', 'null', 'none', 'nan'}
MAX_BYTES = 10 * 1024 * 1024


class FigureError(ValueError):
    """A figure cannot be generated without an explicit correction."""


def need(ok, message):
    if not ok:
        raise FigureError(message)


def text(value, name, limit=2000):
    need(isinstance(value, str) and value.strip() and len(value) <= limit, name + ' needs bounded nonempty text.')
    need(not any(ord(c) < 32 and c not in '\n\t' for c in value), 'Control character in ' + name)
    return value.strip()


def table(data: bytes):
    need(len(data) <= MAX_BYTES, 'CSV exceeds 10 MiB. Prepare a declared analysis table first.')
    try:
        reader = csv.reader(io.StringIO(data.decode('utf-8-sig')), strict=True)
        names = next(reader)
        need(names and all(n.strip() for n in names) and len(set(names)) == len(names), 'Empty or duplicate CSV headers.')
        rows = []
        for line, fields in enumerate(reader, 2):
            need(len(fields) == len(names), f'CSV row {line} has the wrong field count; no silent skipping.')
            rows.append(dict(zip(names, fields)))
            need(len(rows) <= 50000, 'CSV exceeds 50,000 observations. Aggregate explicitly outside the renderer.')
        need(rows, 'CSV contains no observations.')
        return names, rows
    except (UnicodeError, csv.Error, StopIteration) as exc:
        raise FigureError('Read a nonempty, rectangular UTF-8 CSV table.') from exc


def number(value, label):
    if isinstance(value, str) and value.strip().lower() in MISSING:
        return None
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise FigureError('Nonnumeric value at ' + label) from exc
    need(math.isfinite(result), 'Nonfinite value at ' + label)
    return result


def prepare(spec: dict, data: bytes | None = None):
    need(isinstance(spec, dict) and not set(spec) - ALLOWED, 'Unknown figure fields; inspect the recipe instead of ignoring options.')
    kind = spec.get('kind'); need(kind in KINDS, 'Choose a supported figure recipe.')
    for key in ('title', 'purpose', 'caption', 'alt_text'):
        text(spec.get(key), key, 120 if key == 'title' else 2000)
    for key in ('claims', 'evidence'):
        need(isinstance(spec.get(key, []), list) and all(isinstance(v, str) for v in spec.get(key, [])), key + ' must be an ID list.')
    width = spec.get('width_mm', 180 if kind in ('workflow', 'heatmap') else 90)
    height = spec.get('height_mm', 80 if kind != 'workflow' else 55)
    fontsize = spec.get('font_size', 8)
    dpi = spec.get('dpi', 300)
    for name, value, lo, hi in (('width_mm',width,80,240), ('height_mm',height,45,240), ('font_size',fontsize,7,14), ('dpi',dpi,150,600)):
        need(type(value) in (int, float) and math.isfinite(value) and lo <= value <= hi, f'{name} outside supported range {lo}–{hi}.')
    family = spec.get('font_family', 'DejaVu Sans')
    text(family, 'font_family', 100)
    need(not any(c in family for c in '/\\:'), 'Supply a font family name, not a file path.')
    missing = spec.get('missing', 'error'); need(missing in ('error','omit'), 'missing must be error or omit.')
    if missing == 'omit':
        text(spec.get('omission_reason'), 'omission_reason')
    summary = {'kind':kind, 'width_mm':width, 'height_mm':height, 'font_size':fontsize,
               'font_family':family, 'dpi':dpi, 'raw_rows':0, 'used_rows':0, 'omitted_csv_rows':[],
               'missing_line_gaps':[], 'warnings':[], 'transformation':'No filtering, rescaling, smoothing, significance test or inferred intervals.'}
    if kind == 'workflow':
        steps = spec.get('steps')
        need(isinstance(steps, list) and 2 <= len(steps) <= 6, 'Workflow needs 2–6 ordered steps; use a dedicated diagram tool for larger graphs.')
        for step in steps: text(step, 'step', 70)
        need(spec.get('workflow_status') in ('planned','implemented'), 'Declare workflow_status as planned or implemented.')
        need(data is None and not spec.get('input'), 'Workflow is a labeled schematic; quantitative inputs require a data recipe.')
        summary['transformation'] = 'Sequential process schematic, not an experimental result or causal mechanism.'
        return [], summary
    names, raw = table(data if isinstance(data, bytes) else b'')
    summary['raw_rows'] = len(raw)
    numeric = {'scatter':['x','y'], 'line':['x','y'], 'distribution':['y'], 'paired':['x','y'],
               'interval':['x','lower','upper'], 'heatmap':['value']}[kind]
    categories = {'distribution':['group'], 'paired':['pair_id'], 'interval':['label'], 'heatmap':['row','column']}.get(kind, [])
    if kind in ('scatter','line') and spec.get('group'): categories += ['group']
    for key in numeric + categories:
        need(isinstance(spec.get(key), str) and spec[key] in names, 'Missing CSV column mapping: ' + key)
    for label in ('xlabel','ylabel','unit'):
        if kind == 'interval' and label == 'ylabel': continue
        text(spec.get(label), label, 120)
    if kind == 'interval': text(spec.get('interval_definition'), 'interval_definition', 300)
    clean = []
    for line, item in enumerate(raw, 2):
        row = {'csv_row':line}
        for key in numeric: row[key] = number(item[spec[key]], f'CSV row {line}, {spec[key]}')
        for key in categories: row[key] = text(item[spec[key]], 'category at CSV row ' + str(line), 100)
        empty = [k for k in numeric if row[k] is None]
        if empty:
            need(missing == 'omit', f'Missing values at CSV row {line}; choose and explain a missing-data policy.')
            if kind == 'line':
                need(empty == ['y'], 'Missing line x coordinates cannot be ordered safely.')
                row['y'] = float('nan'); summary['missing_line_gaps'].append(line)
            else:
                summary['omitted_csv_rows'].append(line); continue
        clean.append(row)
    need(clean and (kind != 'line' or any(math.isfinite(r['y']) for r in clean)), 'No plottable observations remain.')
    summary['used_rows'] = len(clean) - len(summary['missing_line_gaps'])
    if kind in ('scatter','line','distribution'):
        groups = list(dict.fromkeys(r.get('group', 'Observations') for r in clean))
        need(len(groups) <= 6, 'More than six series: split the scientific question into separate figures.')
        summary['groups'] = groups
    if kind == 'line':
        keys = [(r.get('group'), r['x']) for r in clean]
        need(len(keys) == len(set(keys)), 'Duplicate x in a series. Choose and record an estimator before drawing a line.')
        summary['transformation'] = 'Stable numeric x sort per series; missing y remains a visible line gap.'
    if kind == 'paired':
        ids = [r['pair_id'] for r in clean]
        need(len(ids) == len(set(ids)), 'Repeated pair IDs would give some units excess weight.')
        need(len(clean) <= 300, 'More than 300 pairs: use an explicitly designed summary without hiding observations.')
        summary['paired_mean_difference'] = statistics.mean(r['y']-r['x'] for r in clean)
        summary['difference_direction'] = 'y minus x; descriptive only, no inferential test'
    if kind == 'distribution':
        need(len(clean) <= 2000, 'More than 2,000 raw points: plan bins or a density analysis explicitly.')
        summary['transformation'] = 'Box: median/IQR, whiskers within 1.5 IQR; all observations overlaid; x-only jitter seed 0.'
    if kind == 'interval':
        labels = [r['label'] for r in clean]; need(len(labels) == len(set(labels)) and len(labels) <= 20, 'Use 1–20 unique interval labels.')
        need(all(r['lower'] <= r['x'] <= r['upper'] for r in clean), 'Bounds must bracket the supplied estimate.')
        summary['interval_definition'] = spec['interval_definition']
    if kind == 'heatmap':
        keys = [(r['row'], r['column']) for r in clean]
        need(len(keys) == len(set(keys)), 'Duplicate heatmap cell; aggregate explicitly.')
        ys = list(dict.fromkeys(r['row'] for r in clean)); xs = list(dict.fromkeys(r['column'] for r in clean))
        need(len(ys) <= 12 and len(xs) <= 12, 'Use at most 12 rows/columns for a legible labeled heatmap.')
        summary.update(rows=ys, columns=xs, absent_cells=len(ys)*len(xs)-len(clean))
    if summary['omitted_csv_rows'] or summary['missing_line_gaps']:
        summary['omission_reason'] = spec['omission_reason']
        summary['warnings'].append('Missing observations are disclosed; scientific appropriateness needs review.')
    return clean, summary


def render(spec: dict, data: bytes | None, output: Path) -> dict:
    rows, summary = prepare(spec, data)
    need(not output.exists(), 'Output directory must be new; never overwrite a prior figure.')
    try:
        import matplotlib as mpl
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib import font_manager
        from matplotlib.text import Text
    except ImportError as exc:
        raise FigureError('Plotting dependency missing. The agent should request scoped installation of the figures extra.') from exc
    try:
        font_manager.findfont(font_manager.FontProperties(family=summary['font_family']), fallback_to_default=False)
    except ValueError as exc:
        raise FigureError('Requested font is unavailable; choose an installed font family.') from exc
    with mpl.rc_context({'text.usetex':False, 'text.parse_math':False, 'font.family':summary['font_family'],
                         'font.size':summary['font_size'], 'axes.titlesize':summary['font_size']+1,
                         'axes.labelsize':summary['font_size'], 'legend.fontsize':summary['font_size']-1,
                         'svg.fonttype':'none', 'svg.hashsalt':'AI-Research-Workspace', 'pdf.fonttype':42}):
        fig = Figure(figsize=(summary['width_mm']/25.4, summary['height_mm']/25.4), layout='constrained')
        FigureCanvasAgg(fig); ax = fig.add_subplot(111)
        kind = spec['kind']; wrap = lambda s,n=25: textwrap.fill(s,n)
        ax.set_title(wrap(spec['title'], 36 if summary['width_mm'] < 120 else 70), pad=10)
        shapes = ('o','s','^','D','v','P'); styles = ('-','--','-.',':','--','-.')
        if kind in ('scatter','line'):
            for i, group in enumerate(summary['groups']):
                series = [r for r in rows if r.get('group','Observations') == group]
                if kind == 'line': series = sorted(series, key=lambda r:r['x'])
                if kind == 'scatter': ax.scatter([r['x'] for r in series],[r['y'] for r in series],marker=shapes[i],s=17,alpha=.8,label=wrap(group,18))
                else: ax.plot([r['x'] for r in series],[r['y'] for r in series],marker=shapes[i],markersize=3,linestyle=styles[i],linewidth=1.2,label=wrap(group,18))
            if len(summary['groups']) > 1: ax.legend(loc='best',frameon=False)
        elif kind == 'distribution':
            rng = random.Random(0)
            arrays = [[r['y'] for r in rows if r['group']==g] for g in summary['groups']]
            ax.boxplot(arrays, positions=list(range(len(arrays))),widths=.45,showfliers=False,manage_ticks=False)
            for i, values in enumerate(arrays):
                ax.scatter([i+rng.uniform(-.13,.13) for _ in values], values,s=9,alpha=.6,marker=shapes[i])
            ax.set_xticks(range(len(arrays)),[wrap(g,14)+'\nn='+str(len(a)) for g,a in zip(summary['groups'],arrays)])
        elif kind == 'paired':
            for row in rows: ax.plot([0,1],[row['x'],row['y']],linewidth=.6,alpha=.55)
            ax.scatter([0]*len(rows),[r['x'] for r in rows],marker='o',s=15)
            ax.scatter([1]*len(rows),[r['y'] for r in rows],marker='s',s=15)
            ax.set_xticks([0,1],[wrap(spec['x'],16),wrap(spec['y'],16)]); ax.set_xlim(-.25,1.25)
        elif kind == 'interval':
            for i,row in enumerate(rows):
                ax.errorbar(row['x'],i,xerr=[[row['x']-row['lower']],[row['upper']-row['x']]],fmt='o',markersize=4,capsize=3,linewidth=1.2)
            ax.set_yticks(range(len(rows)),[wrap(r['label'],20) for r in rows]); ax.invert_yaxis()
        elif kind == 'heatmap':
            xs,ys=summary['columns'],summary['rows']; values={(r['row'],r['column']):r['value'] for r in rows}
            grid=[[values.get((y,x),float('nan')) for x in xs] for y in ys]
            image=ax.imshow(grid,aspect='auto',interpolation='nearest')
            fig.colorbar(image,ax=ax,label=wrap(spec['unit'],20),shrink=.85)
            ax.set_xticks(range(len(xs)),[wrap(x,12) for x in xs]);ax.set_yticks(range(len(ys)),[wrap(y,16) for y in ys])
            for i,y in enumerate(ys):
                for j,x in enumerate(xs):
                    if (y,x) not in values: ax.text(j,i,'NA',ha='center',va='center')
        else:
            ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
            steps=spec['steps']; positions=[(i+.5)/len(steps) for i in range(len(steps))]
            for i,(x,step) in enumerate(zip(positions,steps)):
                ax.text(x,.53,wrap(step,14),ha='center',va='center',bbox={'boxstyle':'round,pad=.55','fill':False})
                if i: ax.annotate('',xy=(x-.40/len(steps),.53),xytext=(positions[i-1]+.40/len(steps),.53),arrowprops={'arrowstyle':'->','linewidth':1})
            ax.text(.5,.12,spec['workflow_status'].upper()+' PROCESS / schematic',ha='center',va='center')
        if kind != 'workflow':
            ax.set_xlabel(wrap(spec['xlabel'],35));ax.set_ylabel(wrap(spec.get('ylabel',''),28))
            if kind != 'heatmap':
                ax.spines[['top','right']].set_visible(False);ax.tick_params(direction='out',length=3,width=.7)
                ax.margins(y=.13)
        with warnings.catch_warnings(record=True) as found:
            warnings.simplefilter('always');fig.canvas.draw()
            renderer=fig.canvas.get_renderer(); limits=fig.bbox
            clipped=[]
            artists=[]
            for axes in fig.axes:
                artists += list(axes.texts)+[axes.title,axes.xaxis.label,axes.yaxis.label,axes.xaxis.offsetText,axes.yaxis.offsetText]
                if axes.get_legend(): artists += axes.get_legend().get_texts()
                for axis,limits_data in (((axes.xaxis,axes.get_xlim()),(axes.yaxis,axes.get_ylim())) if axes.axison else ()):
                    lo,hi=sorted(limits_data)
                    for tick in axis.get_major_ticks()+axis.get_minor_ticks():
                        if lo <= tick.get_loc() <= hi: artists += [tick.label1,tick.label2]
                
            for artist in artists:
                if artist.get_visible() and artist.get_text():
                    box=artist.get_window_extent(renderer)
                    if box.width and (box.x0 < -2 or box.y0 < -2 or box.x1 > limits.x1+2 or box.y1 > limits.y1+2):
                        clipped.append(artist.get_text())
            need(not clipped, 'Text would be clipped: '+repr(clipped)+'; shorten labels or enlarge the requested physical dimensions.')
            output.mkdir(parents=True)
            for ext in ('svg','pdf','png'):
                metadata={'Creator':'AI Research Workspace','Title':spec['title']}
                if ext in ('svg','png'): metadata['Description']=spec['alt_text']
                if ext=='pdf': metadata['Subject']=spec['alt_text']
                if ext=='pdf': metadata.update(CreationDate=None,ModDate=None)
                if ext=='svg': metadata['Date']=None
                fig.savefig(output/('figure.'+ext),format=ext,dpi=summary['dpi'],metadata=metadata)
        errors=[str(w.message) for w in found if 'Glyph' in str(w.message) or 'constrained_layout not applied' in str(w.message)]
        need(not errors, 'Font/layout failed: ' + '; '.join(errors))
        summary['warnings'] += sorted(set(str(w.message) for w in found))
        summary.update(matplotlib=mpl.__version__,visual_review='required',formats=['svg','pdf','png'])
        fig.clear()
    return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec');parser.add_argument('--data');parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    try:
        spec=json.loads(Path(args.spec).read_text(encoding='utf-8'))
        summary=render(spec,Path(args.data).read_bytes() if args.data else None,Path(args.output))
        print(json.dumps(summary,ensure_ascii=False,indent=2));return 0
    except (FigureError,OSError,ValueError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False));return 2


if __name__=='__main__': raise SystemExit(main())
