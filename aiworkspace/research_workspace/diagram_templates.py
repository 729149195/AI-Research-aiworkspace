"""Original editable starter diagrams; examples are plans, never scientific results."""
from __future__ import annotations
import copy


def node(key,label,detail='',role='process',group=None):
    result={'id':key,'label':label,'detail':detail,'role':role}
    if group: result['group']=group
    return result


def edge(a,b,label='',relation='flow',certainty='schematic'):
    return {'source':a,'target':b,'label':label,'relation':relation,'certainty':certainty,'evidence':[]}


def template(kind):
    s={'id':'FIG-DIAGRAM','kind':kind,'status':'illustrative','style':'editorial','direction':'LR','width_mm':180,
       'title':'','subtitle':'Illustrative template — replace with the actual study',
       'purpose':'Explain the stated research structure. This is an editable example, not study evidence.',
       'caption':'Illustrative research diagram. The layout does not encode measured quantities or prove causality.',
       'alt_text':'A structured diagram of an illustrative research workflow with explicitly labelled relationships.',
       'claims':[],'evidence':[],'nodes':[],'edges':[],'groups':[]}
    if kind=='pipeline':
        s.update(title='From observations to a comparison plan', direction='TB', width_mm=165)
        s['nodes']=[node('input','Input observations','Retain the original records','input'),node('qc','Quality criteria met?',role='decision'),
            node('revise','Investigate exclusions','Record reasons; retain originals','control'),node('baseline','Reference method','Use the agreed comparison'),node('candidate','Candidate method','Apply the proposed approach'),
            node('compare','Compare outcomes','Inspect uncertainty and limitations','output')]
        s['edges']=[edge('input','qc'),edge('qc','baseline','yes'),edge('qc','candidate','yes'),edge('qc','revise','no'),edge('revise','qc','recheck','feedback'),edge('baseline','compare'),edge('candidate','compare')]
        s['ranks']=[['qc','revise'],['baseline','candidate']]
    elif kind=='architecture':
        s.update(title='A research workspace with clear responsibilities',direction='TB',width_mm=130)
        s['groups']=[{'id':'interface','label':'01  AUTHOR INTERFACE'},{'id':'research','label':'02  RESEARCH SERVICES'},{'id':'storage','label':'03  VERSIONED ARTIFACTS'}]
        s['nodes']=[node('author','Author request','Goal, constraints and permissions','input','interface'),node('guide','Task routing','Choose the relevant specialist','process','interface'),
            node('evidence','Evidence service','Sources and claim relationships','process','research'),node('writing','Writing service','Bounded edits and consistency','process','research'),
            node('state','Research state','Logic, rules and change history','output','storage'),node('paper','Manuscript','Text, figures and references','output','storage')]
        s['edges']=[edge('author','guide'),edge('guide','evidence'),edge('guide','writing'),edge('evidence','state','records','data'),edge('writing','paper','edits','data'),edge('state','paper','linked context','association')]
        s['ranks']=[['evidence','writing'],['state','paper']]
    elif kind=='experiment':
        s.update(title='An experiment with parallel conditions',status='planned',direction='TB',width_mm=130)
        s['nodes']=[node('eligible','Eligible observation units','Sampling and eligibility to be defined','input'),node('assign','Allocate to conditions','Assignment procedure to be confirmed'),
            node('control','Control condition','Matched task and measurement','control'),node('treatment','Experimental condition','Only planned factor differs'),
            node('measure','Measure outcomes','Same protocol across both conditions'),node('analysis','Planned comparison','Define estimand and uncertainty','output')]
        s['edges']=[edge('eligible','assign'),edge('assign','control'),edge('assign','treatment'),edge('control','measure'),edge('treatment','measure'),edge('measure','analysis')]
        s['ranks']=[['control','treatment']]
    elif kind=='mechanism':
        s.update(title='A mechanism hypothesis to be tested',status='planned',direction='LR',width_mm=190)
        s['nodes']=[node('exposure','Exposure','Specify intervention or condition','input'),node('mediator','Candidate mediator','Proposed intermediate process'),
            node('outcome','Outcome','Define observable endpoint','output'),node('moderator','Competing influence','Potential alternative explanation','control')]
        s['edges']=[edge('exposure','mediator','promotes','causal','hypothesis'),edge('mediator','outcome','contributes to','causal','hypothesis'),
            edge('moderator','mediator','inhibits','inhibition','hypothesis'),edge('exposure','outcome','association','association','hypothesis')]
    elif kind=='graphical-abstract':
        s.update(title='Problem, approach and evaluation',width_mm=190)
        s['groups']=[{'id':'problem','label':'A  RESEARCH PROBLEM'},{'id':'method','label':'B  PROPOSED APPROACH'},{'id':'evaluation','label':'C  EVALUATION PLAN'}]
        s['nodes']=[node('need','Analytical need','State a concrete user task','input','problem'),node('gap','Unresolved limitation','Support with actual literature','control','problem'),
            node('idea','Core idea','State the proposed contribution','process','method'),node('system','Method or system','Connect design to the task','process','method'),
            node('measure','Fair comparison','Baseline, measures and uncertainty','output','evaluation'),node('limit','Scope and limitations','No results are claimed here','note','evaluation')]
        s['edges']=[edge('need','idea'),edge('idea','measure'),edge('gap','system'),edge('system','limit')]
        s['ranks']=[['need','gap'],['idea','system'],['measure','limit']]
    elif kind=='conceptual':
        s.update(title='A conceptual model and its observable measures',status='planned',direction='TB',width_mm=180)
        s['groups']=[{'id':'construct','label':'CONCEPTUAL LEVEL'},{'id':'measure','label':'OBSERVATION LEVEL'}]
        s['nodes']=[node('a','Construct A','Define the theoretical concept','input','construct'),node('b','Construct B','Define the related concept','output','construct'),
            node('ma','Measure of A','Operationalization to validate','process','measure'),node('mb','Measure of B','Operationalization to validate','process','measure')]
        s['edges']=[edge('a','b','proposed link','association','hypothesis'),edge('a','ma','operationalized by'),edge('b','mb','operationalized by')]
        s['ranks']=[['a','b'],['ma','mb']]
    elif kind=='response':
        s.update(title='A traceable response to reviewer concerns',direction='TB',width_mm=135)
        s['nodes']=[node('comment','Original reviewer comment','Keep the actual wording','input'),node('change','Make the scoped change','Preserve evidence and author intent'),
            node('check','Recheck the manuscript','Inspect figures, claims and citations'),node('reply','Draft a located response','Link actual changes and remaining work','output')]
        s['edges']=[edge('comment','change'),edge('change','check'),edge('check','reply'),edge('check','change','unresolved issue','feedback')]
    else:
        raise ValueError('Unknown diagram template: '+str(kind))
    return copy.deepcopy(s)
