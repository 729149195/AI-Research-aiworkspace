"""Original VIS/HCI worked examples; synthetic observations, no research result.

Regenerate local editable SVGs/specs with Python. No network or imported artwork.
The geometry, masks and coordinated-view counts derive from the adjacent CSV.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parent
INK='#263238';MUTED='#5e666d';GRID='#cdd3d7';BLUE='#216b91';LIGHT='#e7f0f5';BG='#b8c1c7';WARM='#b5653e'

class Drawing:
    def __init__(self,w=1100,h=540):
        self.w=w;self.h=h;self.elements=[]
        self.rect(0,0,w,h,'white','none')
    def tag(self,tag,content='',**kw):
        attrs=' '.join(f'{k.replace("_","-")}="{escape(str(v))}"' for k,v in kw.items())
        self.elements.append(f'<{tag} {attrs}>{content}</{tag}>')
    def text(self,x,y,t,size=17,fill=INK,weight='normal',anchor='start'):
        self.tag('text',escape(str(t)),x=x,y=y,font_family='Liberation Sans',font_size=size,font_weight=weight,fill=fill,text_anchor=anchor)
    def line(self,x1,y1,x2,y2,color=GRID,sw=1.2,dash=None):
        kw={} if dash is None else {'stroke_dasharray':dash}
        self.tag('line',x1=x1,y1=y1,x2=x2,y2=y2,stroke=color,stroke_width=sw,**kw)
    def rect(self,x,y,w,h,fill='none',stroke=GRID,sw=1.2):
        self.tag('rect',x=x,y=y,width=w,height=h,fill=fill,stroke=stroke,stroke_width=sw)
    def dot(self,x,y,r=5,fill=BLUE,stroke='none'):
        self.tag('circle',cx=x,cy=y,r=r,fill=fill,stroke=stroke,stroke_width=1.3)
    def arrow(self,x1,y1,x2,y2,color=MUTED):
        self.line(x1,y1,x2,y2,color,1.6)
        if y1==y2:
            s=1 if x2>x1 else -1;pts=f'{x2},{y2} {x2-7*s},{y2-4} {x2-7*s},{y2+4}'
        else:pts=f'{x2},{y2} {x2-4},{y2-7} {x2+4},{y2-7}'
        self.tag('polygon',points=pts,fill=color)
    def group(self,id): self.elements.append('<g id="'+id+'">')
    def end(self): self.elements.append('</g>')
    def save(self,path,title):
        out=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="180mm" height="{180*self.h/self.w}mm"><title>{escape(title)}</title><desc>Original illustrative figure using synthetic data. No reported experiment or product screenshot.</desc>'
        Path(path).write_text(out+'\n'.join(self.elements)+'</svg>',encoding='utf-8')

def load():
    rows=list(csv.DictReader((ROOT/'worked-example.csv').open(encoding='utf-8')))
    return [dict(id=r['id'],x=float(r['x']),y=float(r['y']),group=r['group']) for r in rows]

def selected(rows):return {r['id'] for r in rows if 1.5<=r['x']<=4.5 and 3.5<=r['y']<=7.5}

def scatter(d,rows,x,y,w,h,brush=False,highlight=False,labels=True):
    ids=selected(rows)
    d.line(x,y,x,y+h);d.line(x,y+h,x+w,y+h)
    for n in (0,5,10):
        xx=x+n*w/10; yy=y+h-n*h/10
        d.line(xx,y+h,xx,y+h+4);d.text(xx,y+h+22,n,16,anchor='middle')
        d.line(x-4,yy,x,yy);d.text(x-9,yy+5,n,16,anchor='end')
    d.text(x+w/2,y+h+44,'Attribute x',17,anchor='middle');d.text(x,y-10,'Attribute y',17)
    if brush:
        d.rect(x+1.5*w/10,y+h-7.5*h/10,3*w/10,4*h/10,LIGHT,BLUE,1.3)
    for r in rows:
        xx=x+r['x']*w/10;yy=y+h-r['y']*h/10
        col=BLUE if r['id'] in ids and highlight else BG
        d.dot(xx,yy,5.2,col,BLUE if highlight and r['id'] in ids else 'none')
        if labels:d.text(xx+8,yy-7,r['id'],16,BLUE if highlight and r['id'] in ids else MUTED)

def panel(d,id,x,y,title):
    d.group('panel-'+id);d.text(x,y,'('+id+') '+title,22,INK,'bold')

def table(d,rows,x,y,width=270,show_xy=False,mask=False):
    cols=[x+10,x+64,x+116,x+183] if show_xy else [x+10,x+76,x+161]
    names=['ID','x','y','Group'] if show_xy else ['ID','Group','Selected']
    for xx,n in zip(cols,names):d.text(xx,y,n,17,MUTED,'bold')
    d.line(x,y+9,x+width,y+9,MUTED,1.2)
    for i,r in enumerate(rows):
        yy=y+31+i*21
        if r['id'] in selected(rows):d.rect(x,yy-15,width,21,LIGHT,'none')
        vals=[r['id'],f'{r["x"]:g}',f'{r["y"]:g}',r['group']] if show_xy else [r['id'],r['group'],'1' if r['id'] in selected(rows) else '0']
        for xx,v in zip(cols,vals):d.text(xx,yy,v,17,BLUE if r['id'] in selected(rows) else INK)
    d.line(x,y+31+len(rows)*21-10,x+width,y+31+len(rows)*21-10,GRID)

def overview(rows):
    d=Drawing(1100,565)
    panel(d,'a',15,29,'Brush the visible marks')
    scatter(d,rows,52,80,235,155,True,True)
    d.text(26,318,'The same eight rows throughout',17,MUTED)
    table(d,rows,26,346,278,True)
    d.end()
    # Whitespace, panel lettering and local detail carry hierarchy, not big cards.
    panel(d,'b',356,29,'From geometry to row identity')
    d.text(363,70,'Brush B',19,BLUE,'bold')
    d.text(363,99,'1.5 <= x <= 4.5',18)
    d.text(363,126,'3.5 <= y <= 7.5',18)
    d.arrow(510,104,558,104)
    d.text(582,71,'Hit-test each mark',19)
    for i,r in enumerate(rows):
        xx=576+(i%4)*41;yy=110+(i//4)*44
        d.dot(xx,yy,11,BLUE if r['id'] in selected(rows) else '#eef1f3')
        d.text(xx,yy+6,r['id'],16,'white' if r['id'] in selected(rows) else MUTED,anchor='middle')
    d.text(363,207,'S = {b, c, d}',22,BLUE,'bold')
    d.text(363,239,'Selected identity survives the view change.',17)
    d.end()
    d.line(355,261,759,261,GRID,1)
    panel(d,'c',356,294,'Aggregate the selected rows')
    d.text(363,332,'Row IDs',17,MUTED)
    for i,r in enumerate(rows):
        xx=363+i*47
        d.text(xx+16,362,r['id'],18,anchor='middle')
        d.rect(xx,380,32,31,BLUE if r['id'] in selected(rows) else '#f1f3f4','none')
        d.text(xx+16,402,'1' if r['id'] in selected(rows) else '0',17,'white' if r['id'] in selected(rows) else MUTED,anchor='middle')
    d.text(363,446,'Mask: membership in S',18)
    d.text(363,477,'Count selected rows within each group:',17)
    d.text(363,512,'Group A: 1 of 4      Group B: 2 of 4',19,BLUE,'bold')
    d.end()
    panel(d,'d',812,29,'Inspect linked views')
    d.text(814,72,'Shared group-count scale',18,MUTED)
    x=910;y=99;w=146
    for idx,g in enumerate(('A','B')):
        yy=y+idx*51;n=sum(r['group']==g and r['id'] in selected(rows) for r in rows)
        d.text(818,yy+24,'Group '+g,17)
        d.rect(x,yy,w,32,'#e5e9ec','none');d.rect(x,yy,w*n/4,32,BLUE,'none')
        d.text(x+w*n/4+8,yy+23,str(n),17,BLUE,'bold')
    d.line(x,y+91,x+w,y+91)
    for n in (0,2,4):d.text(x+w*n/4,y+117,n,16,anchor='middle')
    d.dot(822,245,5,BLUE);d.text(837,251,'Selected',17)
    d.dot(944,245,5,'#d9dfe3');d.text(959,251,'All rows',17)
    d.text(816,302,'Linked table: retained IDs',18,MUTED)
    for i,r in enumerate([r for r in rows if r['id'] in selected(rows)]):
        yy=339+i*39;d.line(815,yy+13,1080,yy+13,GRID,1)
        d.text(827,yy,r['id'],20,BLUE,'bold');d.text(882,yy,'Group '+r['group'],18)
    d.text(816,485,'No new observations;',17);d.text(816,511,'only the selection changes.',17)
    d.end()
    d.arrow(311,150,343,150)
    d.arrow(756,390,799,390)
    d.arrow(744,204,744,268)
    d.text(16,555,'Illustrative worked example • synthetic rows • no experimental finding',16,MUTED)
    return d

def storyboard(rows):
    d=Drawing(1100,470)
    for id,x,title in [('a',15,'Initial view'),('b',387,'User brushes a region'),('c',760,'Linked views update')]:
        panel(d,id,x,30,title)
        if id != 'c':
            scatter(d,rows,x+37,89,260,160,id!='a',id!='a')
        else:
            d.text(x+13,91,'Selected rows / group totals',17,MUTED)
            bx=x+97; bw=199
            for i,g in enumerate(('A','B')):
                by=114+i*49
                n=sum(r['group']==g and r['id'] in selected(rows) for r in rows)
                total=sum(r['group']==g for r in rows)
                d.text(x+13,by+22,'Group '+g,17)
                d.rect(bx,by,bw,30,'#e5e9ec','none')
                d.rect(bx,by,bw*n/total,30,BLUE,'none')
                d.text(bx+bw*n/total+8,by+21,str(n),17,BLUE,'bold')
            d.line(bx,206,bx+bw,206)
            for n in (0,2,4):d.text(bx+bw*n/4,230,n,16,anchor='middle')
            d.text(x+13,270,'Retained IDs:',17,MUTED)
            for i,r in enumerate([r for r in rows if r['id'] in selected(rows)]):
                d.dot(x+148+i*57,265,14,LIGHT)
                d.text(x+148+i*57,271,r['id'],18,BLUE,'bold',anchor='middle')
        if id=='a':
            d.text(x+12,329,'Eight observations; no active selection.',17)
            d.text(x+12,365,'Task: compare a local subset',18)
            d.text(x+12,391,'without losing the surrounding context.',17)
        elif id=='b':
            # Pointer references the actual brush boundary, not a decorative icon.
            px=x+154;py=89+160-3.5*16
            d.tag('polygon',points=f'{px},{py} {px+5},{py+26} {px+12},{py+16} {px+23},{py+18}',fill=INK,stroke='white',stroke_width=1)
            d.text(x+12,329,'Drag the brush; b, c and d are selected.',17)
            d.text(x+12,365,'Action: spatial selection',18,BLUE,'bold')
            d.text(x+12,391,'Feedback: highlight, keep context.',17)
        else:
            d.text(x+12,329,'Selection S = {b, c, d}',19,BLUE,'bold')
            d.text(x+12,365,'Group A: 1 / 4    Group B: 2 / 4',18)
            d.text(x+12,391,'Correspondence uses the same row IDs.',17)
        d.end()
    d.arrow(331,164,373,164);d.arrow(704,164,746,164)
    d.line(16,423,1085,423,GRID,1)
    d.text(16,452,'Illustrative interaction storyboard • design sketch with synthetic data; not a product screenshot or user-study result',16,MUTED)
    return d

def spec(name,panels):
    return {'kind':'paper-composite','id':'FIG-'+name.upper(),'title':name.replace('-',' '),
            'purpose':'Explain identity-preserving linked brushing with one fully specified synthetic example.',
            'caption':'Illustrative linked-brushing example. Eight synthetic rows are kept fixed; the geometric brush selects b, c and d. The linked groups contain one selected A row and two selected B rows. This explains a familiar interaction mechanism and claims no research novelty, measured salience or user-study benefit.',
            'alt_text':'Labeled panels trace eight synthetic observations through a brush, a selected identity set and coordinated displays. Selected rows remain blue and keep their letter IDs.',
            'status':'illustrative','artwork':name+'.svg','claims':[],'evidence':[], 'edges':[],
            'width_mm':180,'min_font_pt':7,'dpi':220,
            'panels':[{'id':'panel-'+p[0],'role':p[1],'object':p[2],'shows':p[3],
                       'source_status':'illustrative','source_note':'Synthetic worked-example.csv; known deterministic selection, not empirical evidence.'} for p in panels]}


def main():
    rows=load();assert selected(rows)=={'b','c','d'}
    items=[('method-detail',overview(rows), [('a','input','Eight labeled points and rows','Brush geometry on the input coordinates'),('b','transformation','Brush and selected row IDs','Actual hit-test produces S={b,c,d}'),('c','encoding','The same eight IDs and binary mask','One A and two B rows pass the predicate'),('d','output','Linked bars and filtered rows','Counts and identity remain consistent')]),
           ('interaction-storyboard',storyboard(rows), [('a','input','Unselected observations','Initial task state'),('b','interaction','The same points with a brush and pointer','User action and its visible local feedback'),('c','output','Selected identities and linked counts','Stable cross-view correspondence')])]
    for name,draw,panels in items:
        draw.save(ROOT/(name+'.svg'),name)
        (ROOT/(name+'.json')).write_text(json.dumps(spec(name,panels),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
