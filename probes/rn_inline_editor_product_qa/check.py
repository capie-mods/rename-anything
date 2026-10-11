"""Read-only source-contract check; optionally writes this candidate's report.

Uses the existing deliberately limited ApplyVM for actual pair-source control
flow. It is not HOI4's parser, native GUI, network model or an engine setter.
No hook, process, configuration, compiled output or protected source is changed.
"""
from __future__ import annotations
import copy
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE = REPO/'probes/rn_inline_editor_apply_qa'
spec = importlib.util.spec_from_file_location('product_apply_vm', REPO/'probes/rn_inline_pair_apply_source/check.py')
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)
parse, ApplyVM, Country = model.parse, model.ApplyVM, model.Country
GROUPS = [(1,'democratic'), (2,'communism'), (3,'fascism'), (4,'neutrality')]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def get(nodes, key):
    found=[v for k,_,v in nodes if k==key]
    assert len(found)==1, ('expected singleton',key,len(found))
    return found[0]
def walk(nodes):
    for node in nodes:
        yield node
        if isinstance(node[2],list): yield from walk(node[2])
def tokens(nodes): return {v for _,_,v in walk(nodes) if isinstance(v,str)}
def named(nodes): return {get(v,'name'):v for _,_,v in walk(nodes) if isinstance(v,list) and any(k=='name' for k,_,_ in v)}
def declarations(folder):
    result={}
    for path in sorted(folder.glob('*.txt')):
        for name,_,body in parse(path.read_text(encoding='utf-8-sig')):
            assert name not in result, ('duplicate declaration',name,path)
            result[name]=body
    return result
def group_nodes():
    return [('OR','=', [('check_variable','=',[('rn_ip_party_group','=',str(i))]) for i,_ in GROUPS])]
def group_gate(nodes):
    want=group_nodes()[0]
    assert list(walk(nodes)).count(want)==1, 'missing or different exact pinned-group gate'
    assert not any(k=='has_government' for k,_,_ in walk(nodes)), 'iteration 4: any base group may be renamed'
def then(nodes): return [n for n in nodes if n[0]!='limit']
def success_if(nodes):
    out=next(value for key,_,value in nodes if key=='if')
    assert get(get(out,'limit'),'check_variable') in [[('temp_var:rn_pair_err','=','0')], [('temp_var:rn_ip_leader_error','=','0')]], 'unguarded success branch'
    return then(out)

def structural(effects, models, gui, triggers, locs):
    expected={'rn_ip_leader_launcher_gui','rn_ip_leader_gui','rn_ip_party_neutrality_launcher_gui','rn_ip_party_neutrality_gui','rn_ip_country_launcher_gui','rn_ip_country_gui','rn_ilqa_guard_gui','rn_ip_subject_gui'}
    assert set(models)==expected
    # Iteration 4: subject placeholder stays hidden and inert until both switches are proven.
    subject=models['rn_ip_subject_gui']
    assert get(subject,'context_type')=='diplomacy_target_context' and ('rn_ip_subject_rename_enabled','=','yes') in get(subject,'visible')
    assert triggers['rn_ip_subject_rename_enabled']==[('always','=','no')] and triggers['rn_ip_subject_country_capability']==[('always','=','no')]
    assert ('rn_ip_subject_country_capability','=','yes') in get(get(subject,'triggers'),'rn_ips_country_click_enabled')
    assert all([k for k,_,_ in body]==['log'] for _,_,body in get(subject,'effects')), 'subject placeholder must not write'
    models={k:v for k,v in models.items() if k!='rn_ip_subject_gui'}
    for name,body in models.items():
        assert get(body,'context_type')=='player_context'
        assert get(body,'parent_window_token')=='politics_tab'
        assert get(body,'ai_enabled')==[('always','=','no')]
        for branch in [get(body,'visible'), *[v for k,_,v in get(body,'triggers') if k.endswith('_enabled')]]:
            resolved=triggers['rn_ipp_party_target_matches'] if branch==[('rn_ipp_party_target_matches','=','yes')] else branch
            assert ('tag','=','ROOT') in resolved and ('is_ai','=','no') in resolved, ('own country guard',name)
            assert not any(v=='POL' for _,_,v in walk(branch)), name
        for key,_,enabled in get(body,'triggers'):
            if key.endswith('_apply_click_enabled'):
                symbols=tokens(enabled) | {k for k,_,_ in walk(enabled)}
                assert not any('temp_var:' in v or 'rn_native_' in v for v in symbols), 'pre-ctor temp dependency'
        if name!='rn_ilqa_guard_gui':
            for legacy in ('rn_open','rn_input'):
                assert ('NOT','=',[('has_country_flag','=',legacy)]) in get(body,'visible'), ('legacy visible guard',name)
    for kind,key,helper in [('leader','rn_ip_leader_apply_click','rn_inline_leader_apply'), ('party','rn_ip_party_neutrality_apply_click','rn_inline_pair_apply_party'), ('country','rn_ip_country_apply_click','rn_inline_pair_apply_country')]:
        model_name={'leader':'rn_ip_leader_gui','party':'rn_ip_party_neutrality_gui','country':'rn_ip_country_gui'}[kind]
        prefix={'leader':'rn_ip_leader','party':'rn_ip_party_neutrality','country':'rn_ip_country'}[kind]
        assert get(models[model_name],'window_name')==prefix+'_window'
        open_helper={'leader':'rn_inline_leader_open','party':'rn_inline_pair_open_party','country':'rn_inline_pair_open_country'}[kind]
        cancel_helper={'leader':'rn_inline_leader_cancel','party':'rn_inline_pair_cancel_party','country':'rn_inline_pair_cancel_country'}[kind]
        launcher=models[prefix+'_launcher_gui']
        assert get(launcher,'window_name')==prefix+'_launcher_window'
        assert get(get(launcher,'effects'),prefix+'_open_click')==[(open_helper,'=','yes'),('rn_ip_status_clear','=','yes')]
        assert get(get(models[model_name],'effects'),prefix+'_cancel_click')==[(cancel_helper,'=','yes'),('rn_ip_status_clear','=','yes')]
        for flag in ('rn_open','rn_input'):
            assert ('NOT','=',[('has_country_flag','=',flag)]) in get(get(launcher,'triggers'),prefix+'_open_click_enabled')
        block=get(get(models[model_name],'effects'),key)
        status='rn_ip_status_record_leader' if kind=='leader' else 'rn_ip_status_record_pair'
        assert [k for k,_,_ in block]==['log',helper,status,'log'], 'Apply = log, guarded helper, UI status, log'
        assert 'before' in block[0][2] and 'after' in block[3][2] and 'PASS' not in block[3][2]
        cancel=get(get(models[model_name],'triggers'),key.replace('apply_click','cancel_click_enabled'))
        assert not any(k=='has_government' for k,_,_ in walk(cancel)), 'Cancel must survive government change'
    # Enter/Esc: at most one editor (one RETURN/ESCAPE pair) can be open. Country/party Open require all
    # three inline flags clear; leader Open requires leader/country clear and closes the party editor.
    flags=['rn_ip_leader_open','rn_ip_country_open','rn_ip_party_neutrality_open']
    for helper,need in [('rn_inline_pair_open_country',flags),('rn_inline_pair_open_party',flags),('rn_inline_leader_open',flags[:2])]:
        lim=get(get(effects[helper],'if'),'limit')
        assert all(('NOT','=',[('has_country_flag','=',f)]) in lim for f in need), ('open not exclusive',helper)
    assert ('clr_country_flag','=','rn_ip_party_neutrality_open') in list(walk(effects['rn_inline_leader_open']))
    party=models['rn_ip_party_neutrality_gui']
    switch=get(effects['rn_inline_pair_switch_party'],'if'); slim=get(switch,'limit')
    for need in [('has_country_flag','=','rn_ip_party_neutrality_open'),('NOT','=',[('rn_ip_cooldown_active_party','=','yes')]),('NOT','=',[('check_variable','=',[('rn_ip_party_group','=','temp_var:rn_ip_party_tab')])])]:
        assert need in slim, ('tab switch guard',need)
    assert then(switch)==[('clear_array','=','rn_ip_party_target'),('add_to_array','=',[('rn_ip_party_target','=','THIS')]),('set_variable','=',[('rn_ip_party_group','=','temp_var:rn_ip_party_tab')]),('add_to_variable','=',[('rn_ip_epoch','=','1')])], 'tab switch = re-pin + group + new epoch only'
    for i in range(1,5):
        assert get(get(party,'effects'),'rn_ipp_tab_%d_click'%i)==[('set_temp_variable','=',[('rn_ip_party_tab','=',str(i))]),('rn_inline_pair_switch_party','=','yes'),('rn_ip_status_clear','=','yes')]
        en=get(get(party,'triggers'),'rn_ipp_tab_%d_click_enabled'%i)
        assert ('NOT','=',[('check_variable','=',[('rn_ip_party_group','=',str(i))])]) in en and ('has_country_flag','=','rn_ip_party_neutrality_open') in en
    assert not any(k=='has_government' for k,_,_ in walk(get(party,'visible')))
    group_gate(triggers['rn_ipp_party_target_matches'])
    group_gate(effects['rn_inline_pair_guard_party'])
    for kind in ('party','country','leader'):
        guard=effects['rn_inline_leader_guard' if kind=='leader' else 'rn_inline_pair_guard_'+kind]
        model.pure_audit(effects,'rn_inline_leader_guard' if kind=='leader' else 'rn_inline_pair_guard_'+kind)
        assert ('tag','=','ROOT') in list(walk(guard))
        for flag in ('rn_open','rn_input'):
            assert ('NOT','=',[('has_country_flag','=',flag)]) in list(walk(guard))
        assert ('check_variable','=',[('temp_var:rn_ip_cmd_epoch','=','rn_ip_epoch')]) in list(walk(guard))
        assert ('check_variable','=',[('rn_ip_epoch','>','0')]) in list(walk(guard))
        assert any(k=='round_temp_variable' for k,_,_ in walk(guard))
    # All Apply paths run the complete pure guard both before and after actual strict validation.
    for kind in ('party','country'):
        body=effects['rn_inline_pair_apply_'+kind]
        assert body[0]==('rn_inline_pair_guard_'+kind,'=','yes')
        first=success_if(body)
        assert first[0]==('rn_inline_pair_validate','=','yes')
        second=success_if(first)
        assert second[0]==body[0]
        final=success_if(second)
        if kind=='party':
            branches=[v for k,_,v in final if k in ('if','else_if')]
            assert len(branches)==4
            for branch,(i,g) in zip(branches,GROUPS):
                assert get(branch,'limit')==[('check_variable','=',[('rn_ip_party_group','=',str(i))])]
                commands=then(branch)
                assert [k for k,_,_ in commands]==['rn_inline_party_copy_validated','meta_effect','rn_inline_party_finish']
                setter=get(get(commands[1][2],'text'),'set_party_name')
                assert setter==[('ideology','=',g),('name','=','[S]'),('long_name','=','[L]')]
                for token,prefix in [('S','PS'),('L','PL')]:
                    assert get(commands[1][2],token)==''.join('[ROOT.RN_'+prefix+'_'+str(slot)+']' for slot in range(32))
    leader=effects['rn_inline_leader_apply']
    assert leader[0]==('rn_inline_leader_guard','=','yes')
    first=success_if(leader)
    assert first[:2]==[('rn_inline_validate_payload','=','yes'),('set_temp_variable','=',[('rn_ip_leader_error','=','temp_var:rn_inline_error')])]
    second=success_if(first)
    assert second[0]==leader[0]
    final=success_if(second)
    assert final[1]==('rn_inline_leader_refresh','=','yes')
    assert ('any_character','=',[('is_country_leader','=','yes'),('is_in_array','=',[('array','=','ROOT.rn_ip_leader_target'),('value','=','THIS')])]) in list(walk(effects['rn_inline_leader_guard']))
    assert ('check_variable','=',[('rn_ip_leader_current^num','=','1')]) in list(walk(final))
    assert len([n for n in walk(leader) if n[0]=='set_character_name'])==1
    assert not any(v=='POL' or v.startswith('POL_') for body in effects.values() for v in tokens(body))
    # Private buffer writer has no exposed SG entry; all calls are four selected branches.
    assert sum(n[0]=='rn_inline_party_copy_validated' for body in effects.values() for n in walk(body))==4
    assert not any(n[0]=='rn_inline_party_copy_validated' for body in models.values() for n in walk(body))
    status_texts=[n for n in locs['RN_IPP_PARTY_STATUS'] if n[0]=='text']
    assert [get(t[2],'localization_key') for t in status_texts]==['RN_IP_ERR_CD_PARTY','RN_IP_ERR_PARTY_SHORT','RN_IP_ERR_PARTY_LONG','RN_IP_LONG_NAME','RN_IPP_LONG_UNKNOWN','RN_IPP_TARGET_CHANGED']
    assert all(('rn_ipp_party_target_matches','=','yes') in get(t[2],'trigger') for t in status_texts[:5])
    assert [get(t[2],'localization_key') for t in locs['RN_IP_STATUS'] if t[0]=='text']==['RN_IP_HINT','RN_IP_ERR_CD_LEADER','RN_IP_ERR_CD_COUNTRY','RN_IP_ERR_STALE','RN_IP_ERR_LEADER','RN_IP_ERR_COUNTRY_ADJ','RN_IP_ERR_COUNTRY_NAME']
    cooldown_audit(effects,models,triggers,locs)
    # Status variables are display-only: written only by rn_ip_status_*, never read by guards/triggers/other effects.
    for name,body in effects.items():
        if not name.startswith('rn_ip_status_'):
            assert not any(isinstance(v,str) and 'rn_ip_status_' in v for _,_,v in walk(body)) and not any('rn_ip_status_' in k for k,_,_ in walk(body)), ('status read outside UI',name)
    for name,body in triggers.items(): assert not any('rn_ip_status_' in str(n) for n in walk(body)), name
    for name,body in models.items():
        for key,_,trig in get(body,'triggers'): assert not any('rn_ip_status_' in str(n) for n in walk(trig)), (name,key)
    GK=['DEMOCRATIC','COMMUNISM','FASCISM','NEUTRALITY']
    for name,ruling in [('RN_IPP_PARTY_SHORT','RN_IPP_PARTY_SHORT_CURRENT'),('RN_IPP_PARTY_LONG','RN_IPP_PARTY_LONG_CURRENT')]:
        texts=[n[2] for n in locs[name] if n[0]=='text']
        want=[[('trigger','=',[('rn_ipp_party_target_matches','=','yes'),('check_variable','=',[('rn_ip_party_group','=',str(i))]),('has_government','=',g)]),('localization_key','=',ruling)] for i,g in GROUPS]
        want+=[[('trigger','=',[('rn_ipp_party_target_matches','=','yes'),('check_variable','=',[('rn_ip_party_group','=',str(i))])]),('localization_key','=','RN_IPP_PARTY_SHORT_'+GK[i-1])] for i,_ in GROUPS]
        want+=[[('localization_key','=','RN_IPP_EMPTY')]]
        assert texts==want, ('party carrier branches',name)
    fields={'rn_ip_leader_edit','rn_ip_party_neutrality_edit','rn_ip_party_neutrality_long_edit','rn_ip_country_name_edit','rn_ip_country_adj_edit'}
    actual={get(body,'name') for kind,_,body in walk(gui) if kind=='editBoxType'}
    assert actual==fields
    widgets=named(gui)
    label=widgets['rn_ip_country_label']
    assert get(label,'font')=='hoi_18mbs' and get(label,'format')=='right' and get(label,'text')=='[ROOT.GetName]'
    lw=widgets['rn_ip_country_launcher_window']; lx,ly=xy(lw); bx,by=xy(widgets['rn_ip_country_open'])
    assert ly+by+20<=30 and lx+xy(label)[0]+int(get(label,'maxWidth'))<=lx+bx and lx+bx+20<=460, 'country pencil on the title line, name right-aligned ending at it, before the rules icon'
    for kind in ('leader','party_neutrality','country'): assert get(widgets['rn_ip_'+kind+'_epoch'],'text')=='[?ROOT.rn_ip_epoch|0]'
    assert get(widgets['rn_ip_party_neutrality_prefill'],'text')=='[ROOT.RN_IPP_PARTY_SHORT]'
    assert get(widgets['rn_ip_party_neutrality_long_prefill'],'text')=='[ROOT.RN_IPP_PARTY_LONG]'
    assert get(widgets['rn_ip_party_neutrality_long_label'],'text')=='[ROOT.RN_IPP_PARTY_STATUS]'
    for status in ('rn_ip_leader_status','rn_ip_country_status'): assert get(widgets[status],'text')=='[ROOT.RN_IP_STATUS]' and get(widgets[status],'font')=='Arial12'
    geometry_audit(gui,widgets)

def xy(node,key='position'):
    d=dict((k,v) for k,_,v in get(node,key))
    return int(d.get('x',d.get('width'))),int(d.get('y',d.get('height')))
BIG={'GFX_edit_designer_notes_button','GFX_preset_button_save'}
def button_rect(body,ox,oy):
    x,y=xy(body)
    sprite=[v for k,_,v in body if k=='quadTextureSprite']
    scale=[float(v) for k,_,v in body if k=='scale']
    if sprite and sprite[0] in BIG:
        assert scale and not any(k=='size' for k,_,_ in body), ('30px icon button needs scale, not size',get(body,'name'))
        side=round(30*scale[0])
    elif [v for k,_,v in body if k=='spriteType']==['GFX_button_94x31']:
        return (ox+x,oy+y,ox+x+94,oy+y+31)
    else:
        assert sprite==['GFX_closebutton_16'] and not scale, get(body,'name'); side=16
    return (ox+x,oy+y,ox+x+side,oy+y+side)
def disjoint(a,b): return a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1]
def inside(a,b): return b[0]<=a[0] and b[1]<=a[1] and a[2]<=b[2] and a[3]<=b[3]
FONT_WIDEST={'hoi_18':11,'hoi_16mbs':12}  # max xadvance over the 84-code alphabet (font_width_audit.py)
LEADER_NAME=(18,262,173,298); RULING=(88,305,343,365); PIE_X=270; ACTIONS_Y=383; PANEL_W=550
def geometry_audit(gui,widgets):
    rects={}
    for kind,_,win in walk(gui):
        if kind!='containerWindowType' or not get(win,'name').startswith('rn_ip') or get(win,'name')=='rn_ip_subject_window': continue
        ox,oy=xy(win); w,h=xy(win,'size')
        if not get(win,'name').startswith(('rn_ipc_','rn_ipl_','rn_ipp_')): rects[get(win,'name')]=(ox,oy,ox+w,oy+h)
        for k,_,body in win:
            if k=='buttonType': rects[get(body,'name')]=button_rect(body,ox,oy)
            elif k=='editBoxType':
                x,y=xy(body); ew,eh=xy(body,'size')
                rects[get(body,'name')]=(ox+x,oy+y,ox+x+ew,oy+y+eh)
                assert get(body,'font')=='hoi_18' and ('ignore_enter','=','yes') in body, get(body,'name')
                assert ew>=32*FONT_WIDEST[get(body,'font')], ('field narrower than 32 widest glyphs',get(body,'name'),ew)
            elif k=='containerWindowType':
                x,y=xy(body); fw,fh=xy(body,'size')
                assert get(get(body,'background'),'spriteType')=='GFX_tiles_dark_area_cut_8'
                rects[get(body,'name')]=(ox+x,oy+y,ox+x+fw,oy+y+fh)
    for editor,fields,frames in [('leader',['rn_ip_leader_edit'],['rn_ipl_frame']),
                                 ('party_neutrality',['rn_ip_party_neutrality_edit','rn_ip_party_neutrality_long_edit'],['rn_ipp_short_frame','rn_ipp_long_frame']),
                                 ('country',['rn_ip_country_name_edit','rn_ip_country_adj_edit'],['rn_ipc_name_frame','rn_ipc_adj_frame'])]:
        win=rects['rn_ip_'+editor+'_window']; apply_=rects['rn_ip_'+editor+'_apply']; cancel=rects['rn_ip_'+editor+'_cancel']
        assert disjoint(apply_,cancel), ('Apply/Cancel overlap',editor)
        for f,fr in zip(fields,frames):
            assert inside(rects[f],rects[fr]) and disjoint(rects[f],apply_) and disjoint(rects[f],cancel), (editor,f)
        for r in [apply_,cancel,*[rects[f] for f in fields]]: assert inside(r,win), (editor,r)
        assert win[2]<=PANEL_W and win[3]<=ACTIONS_Y, ('editor leaves panel / reaches y383',editor,win)
        btn={get(b,'name'):b for k,_,b in walk(gui) if k=='buttonType'}
        assert get(btn['rn_ip_'+editor+'_apply'],'shortcut')=='RETURN'
        assert not any(k=='shortcut' for k,_,_ in btn['rn_ip_'+editor+'_cancel']), 'Esc belongs to the vanilla politics close_button (PID49352)'
    assert sum(1 for k,_,b in walk(gui) if k=='buttonType' and any(kk=='shortcut' for kk,_,_ in b))==3, 'only the 3 Apply buttons carry a shortcut'
    assert not any(v=='ESCAPE' for _,_,v in walk(gui)), 'no ESCAPE shortcut anywhere'
    # Tabs: vanilla 94x31 buttons inside the party editor, disjoint from each other and from the fields.
    tabs=[rects['rn_ipp_tab_%d'%i] for i in range(1,5)]
    for i,a in enumerate(tabs):
        assert inside(a,rects['rn_ip_party_neutrality_window'])
        for b in tabs[i+1:]+[rects['rn_ipp_short_frame'],rects['rn_ipp_long_frame'],rects['rn_ip_party_neutrality_apply'],rects['rn_ip_party_neutrality_cancel']]: assert disjoint(a,b)
    # M1: leader pencil never over the leader_name text box; party pencil inside ruling_party_info, left of the pie.
    assert disjoint(rects['rn_ip_leader_open'],LEADER_NAME) and rects['rn_ip_leader_open'][2]<=174 and rects['rn_ip_leader_open'][3]<=LEADER_NAME[1]
    assert inside(rects['rn_ip_party_neutrality_open'],RULING) and rects['rn_ip_party_neutrality_open'][2]<PIE_X
    assert inside(rects['rn_ip_leader_open'],rects['rn_ip_leader_launcher_window'])
    assert inside(rects['rn_ip_party_neutrality_open'],rects['rn_ip_party_neutrality_launcher_window'])

def cooldown_audit(effects,models,triggers,locs):
    # One constant; per-type expiry variables; guard (error 11) in every guard round; start only on success.
    consts=[n for body in effects.values() for n in walk(body) if n[0]=='set_temp_variable' and n[2][0][0]=='rn_ip_cd_days']
    assert len(consts)==1 and list(effects['rn_ip_cooldown_days'])==[('set_temp_variable','=',[('rn_ip_cd_days','=','5')])], 'single cooldown constant'
    for k in ('country','leader','party'):
        t=triggers['rn_ip_cooldown_active_'+k]
        assert t==[('set_temp_variable','=',[('rn_ip_cd_left','=','rn_ip_cd_'+k+'_until')]),('subtract_from_temp_variable','=',[('rn_ip_cd_left','=','global.num_days')]),('check_variable','=',[('rn_ip_cd_left','>','0')])]
        start=effects['rn_ip_cooldown_start_'+k]
        assert ('set_variable','=',[('rn_ip_cd_'+k+'_until','=','global.num_days')]) in start and ('add_to_variable','=',[('rn_ip_cd_'+k+'_until','=','temp_var:rn_ip_cd_days')]) in start
        assert not any('rn_ip_cd_' in str(n) and 'rn_ip_cd_'+k not in str(n) and 'rn_ip_cd_days' not in str(n) for n in walk(start)), ('cross-type write',k)
        guard=effects['rn_inline_leader_guard' if k=='leader' else 'rn_inline_pair_guard_'+k]
        err='rn_ip_leader_error' if k=='leader' else 'rn_pair_err'
        assert guard[-1]==('if','=',[('limit','=',[('check_variable','=',[('temp_var:'+err,'=','0')]),('rn_ip_cooldown_active_'+k,'=','yes')]),('set_temp_variable','=',[(err,'=','11')])]), ('cooldown guard',k)
        callers=[name for name,body in effects.items() if any(n[0]=='rn_ip_cooldown_start_'+k for n in walk(body))]
        assert callers==[{'country':'rn_inline_pair_apply_country','leader':'rn_inline_leader_apply','party':'rn_inline_party_finish'}[k]], ('start callers',k,callers)
        opener={'country':'rn_inline_pair_open_country','leader':'rn_inline_leader_open','party':'rn_inline_pair_open_party'}[k]
        assert ('NOT','=',[('rn_ip_cooldown_active_'+k,'=','yes')]) in get(get(effects[opener],'if'),'limit')
        prefix={'country':'rn_ip_country','leader':'rn_ip_leader','party':'rn_ip_party_neutrality'}[k]
        assert ('NOT','=',[('rn_ip_cooldown_active_'+k,'=','yes')]) in get(get(models[prefix+'_launcher_gui'],'triggers'),prefix+'_open_click_enabled'), ('pencil not disabled',k)
        assert 'rn_ip_cooldown_active_'+k not in str(get(models[prefix+'_launcher_gui'],'visible')), 'pencil must stay visible'
        assert [get(x[2],'localization_key') for x in locs['RN_IP_CD_LEFT_'+k.upper()] if x[0]=='text']==['RN_IP_CD_DAYS_%d'%n for n in range(1,31)]+['RN_IP_CD_DAYS_MORE']
    leader=effects['rn_inline_leader_apply']
    tail=next(v for kk,_,v in reversed(leader) if kk=='if')
    assert get(tail,'limit')==[('check_variable','=',[('temp_var:rn_ip_leader_error','=','0')])] and ('rn_ip_cooldown_start_leader','=','yes') in tail, 'leader cooldown only on success'

class ProductVM(ApplyVM):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.root_tag=self.tag
        self.persistent['global.num_days']=Decimal(1000)
    def condition(self,nodes):
        for key,op,value in nodes:
            if key=='tag' and value=='ROOT':
                answer=self.tag==self.root_tag
            elif key in ('rn_ipp_party_target_matches','rn_ipp_party_pinned_rules'):
                answer=self.condition(TRIGGERS[key]) == (value=='yes')
            elif key in ('set_temp_variable','subtract_from_temp_variable'):
                # HOI4 allows temp-variable arithmetic inside triggers (vanilla ai_strategy/ENG.txt:1729).
                name,_,src=value[0]; prior=self.temp.get(name,Decimal(0)) if key.startswith('subtract') else Decimal(0)
                self.temp[name]=prior-self.value(src) if key.startswith('subtract') else self.value(src); answer=True
            elif key.startswith('rn_ip_cooldown_active_'):
                left=self.persistent.get('rn_ip_cd_'+key[len('rn_ip_cooldown_active_'):]+'_until',Decimal(0))-self.value('global.num_days')
                answer=(left>0)==(value=='yes')
            else: answer=super().condition([(key,op,value)])
            if not answer: return False
        return True

def main():
    global TRIGGERS
    protected=json.loads((HERE/'source-baseline.json').read_text(encoding='utf-8'))
    assert all((REPO/p).is_file() and sha(REPO/p)==h for p,h in protected.items()), 'protected source changed since candidate began'
    hashes={'rn_inline_payload.txt':'CD171D6203BD66DC7905C7C3D0E1A2750C4B8EABAB45F0540D75D3AF2CE10800','rn_inline_pair_payload.txt':'E278DFAC3A4E3AC5CCCA7D7CF74DA9D87F0DE728D30BCA875D543F24956F6FC7'}
    for name,h in hashes.items(): assert sha(HERE/'common/scripted_effects'/name)==h
    assert sha(HERE/'common/scripted_localisation/rn_inline_party_buffers.txt')==sha(BASE/'common/scripted_localisation/rn_inline_party_buffers.txt')
    effects=declarations(HERE/'common/scripted_effects')
    native_effects=declarations(REPO/'mod/common/scripted_effects')
    assert not effects.keys() & native_effects.keys(), 'main mod effect declaration collision'
    own_effects=set(effects)
    effects.update(native_effects)
    OVERRIDE='common/scripted_guis/rename_anything_scripted_gui.txt'
    models={name:body for p in (HERE/'common/scripted_guis').glob('*.txt') if p.name!='rename_anything_scripted_gui.txt' for _,_,outer in parse(p.read_text()) for name,_,body in outer}
    # Task 5: exactly one intentional same-path override of the dev mod: rn_entry_gui hidden, all other bytes equal.
    src=(REPO/'mod'/OVERRIDE).read_bytes(); cand=(HERE/OVERRIDE).read_bytes()
    i=src.index(b'rn_entry_gui = {'); j=src.index(b'visible = { always = yes }',i)
    assert src.count(b'rn_entry_gui = {')==1 and cand==src[:j]+b'visible = { always = no }'+src[j+len(b'visible = { always = yes }'):], 'override is not the exact rn_entry_gui visibility flip'
    assert 'dependencies={ "Rename Anything (dev)" }' in (HERE/'descriptor.template').read_text(encoding='utf-8'), 'override must load after the dev mod'
    gui=[n for p in (HERE/'interface').glob('*.gui') for n in parse(p.read_text())]
    TRIGGERS=declarations(HERE/'common/scripted_triggers')
    locs={get(body,'name'):body for p in (HERE/'common/scripted_localisation').glob('*.txt') for _,_,body in parse(p.read_text(encoding='utf-8-sig'))}
    structural({k:effects[k] for k in own_effects},models,gui,TRIGGERS,locs)
    for p in (HERE/'common').rglob('*.txt'): assert not re.search(r'\btag\s*=\s*POL\b',re.sub(r'#[^\n]*','',p.read_text(encoding='utf-8-sig')))
    # No virtual path, model, scripted-loc or trigger collisions with the main dev mod.
    gamefiles=[p for folder in ('common','interface','localisation') for p in (HERE/folder).rglob('*') if p.is_file()]
    assert [p.relative_to(HERE).as_posix() for p in gamefiles if (REPO/'mod'/p.relative_to(HERE)).exists()]==[OVERRIDE], 'only the declared override may share a dev-mod path'
    modmodels={name for p in (REPO/'mod/common/scripted_guis').glob('*.txt') for _,_,outer in parse(p.read_text(encoding='utf-8-sig')) for name,_,_ in outer}
    assert not models.keys() & modmodels
    mainlocs={get(body,'name') for p in (REPO/'mod/common/scripted_localisation').glob('*.txt') for _,_,body in parse(p.read_text(encoding='utf-8-sig'))}
    assert not locs.keys() & mainlocs
    assert not TRIGGERS.keys() & declarations(REPO/'mod/common/scripted_triggers').keys()
    locmap={name:[n for n in body if n[0]=='text'] for name,body in locs.items()}
    for path in (REPO/'mod/common/scripted_localisation').glob('*.txt'):
        for _,_,body in parse(path.read_text(encoding='utf-8-sig')):
            locmap[get(body,'name')]=[n for n in body if n[0]=='text']
    charsource=(REPO/'mod/localisation/english/rename_anything_chars_l_english.yml').read_text(encoding='utf-8-sig')
    chars={name:json.loads(literal) for name,literal in re.findall(r'^ (RN_CH_\d+):\s*(".*")\s*$',charsource,re.M)}
    assert len(chars)==85
    for lang in ('english','polish'):
        product=(HERE/f'localisation/{lang}/rn_inline_product_l_{lang}.yml').read_text(encoding='utf-8-sig')
        table={k:json.loads(v) for k,v in re.findall(r'^ (\w+):0 (".*")$',product,re.M)}
        assert table['RN_IPP_EMPTY']=='' and table['RN_IPP_TARGET_CHANGED']
        assert table['RN_IPP_PARTY_SHORT_CURRENT']=='[ROOT.GetRulingParty]' and table['RN_IPP_PARTY_LONG_CURRENT']=='[ROOT.GetRulingPartyLong]'
        if lang=='english':
            chars.update(table)
            ui=(HERE/'localisation/english/rn_in_place_ui_l_english.yml').read_text(encoding='utf-8-sig')
            chars.update({k:json.loads(v) for k,v in re.findall(r'^ (\w+):\d* (".*")$',ui,re.M)})
    cases=0
    # Execute the actual four literal branches for multiple own non-POL countries.
    for tag in ('GER','ENG','FRA'):
        for group,government in GROUPS:
            vm=ProductVM(effects,locmap,chars,'party',tag=tag)
            vm.government=government; vm.persistent['rn_ip_party_group']=Decimal(group)
            vm.run('rn_inline_pair_apply_party')
            assert len(vm.requests)==1 and vm.pair_count==1 and vm.guard_count==2
            request=get(vm.requests[0],'set_party_name')
            assert get(request,'ideology')==government and len(get(request,'name'))==1 and len(get(request,'long_name'))==32
            assert vm.persistent['rn_ip_epoch']==8 and 'rn_ip_party_neutrality_open' not in vm.flags
            cases+=1
            # Iteration 4: every pinned group is renamed under any government (non-ruling parties too).
            pre=ProductVM(effects,locmap,chars,'party',tag=tag); pre.government=government; pre.persistent['rn_ip_party_group']=Decimal(group)
            assert pre.localized('RN_IPP_PARTY_SHORT')==chars['RN_IPP_PARTY_SHORT_CURRENT'] and pre.localized('RN_IPP_PARTY_LONG')==chars['RN_IPP_PARTY_LONG_CURRENT'] and pre.localized('RN_IPP_PARTY_STATUS')==chars['RN_IP_LONG_NAME']
            for other in [g for _,g in GROUPS if g!=government]+['custom_ideology']:
                nr=ProductVM(effects,locmap,chars,'party',tag=tag)
                nr.government=other; nr.persistent['rn_ip_party_group']=Decimal(group)
                assert nr.condition(TRIGGERS['rn_ipp_party_target_matches'])
                gk='RN_IPP_PARTY_SHORT_'+['DEMOCRATIC','COMMUNISM','FASCISM','NEUTRALITY'][group-1]
                assert nr.localized('RN_IPP_PARTY_SHORT')==chars[gk] and nr.localized('RN_IPP_PARTY_LONG')==chars[gk]
                assert nr.localized('RN_IPP_PARTY_STATUS')==chars['RN_IPP_LONG_UNKNOWN']
                nr.run('rn_inline_pair_apply_party')
                assert len(nr.requests)==1 and get(get(nr.requests[0],'set_party_name'),'ideology')==government, ('non-ruling group apply',group,other)
                cases+=1
            # Out-of-range group pin is refused before any write and blanks the carriers.
            bad=ProductVM(effects,locmap,chars,'party',tag=tag); bad.persistent['rn_ip_party_group']=Decimal(5)
            state=bad.state(); bad.run('rn_inline_pair_apply_party')
            assert bad.state()==state and not bad.requests and bad.temp['rn_pair_err']==9
            assert bad.localized('RN_IPP_PARTY_SHORT')=='' and bad.localized('RN_IPP_PARTY_STATUS')==chars['RN_IPP_TARGET_CHANGED']
            bad.enforce=False; bad.run('rn_inline_pair_cancel_party')
            assert 'rn_ip_party_neutrality_open' not in bad.flags and bad.arrays['rn_ip_party_target']==[]
            cases+=1
    # Tabs: switching re-pins and advances the epoch only; same tab, closed editor and cooldown are no-ops.
    tab_cases=0
    for start in range(1,5):
        for tab in range(1,5):
            vm=ProductVM(effects,locmap,chars,'party',tag='FRA'); vm.enforce=False; vm.persistent['rn_ip_party_group']=Decimal(start)
            vm.arrays['rn_ip_party_target']=[Country('FRA')]; before=vm.state(); vm.temp['rn_ip_party_tab']=Decimal(tab)
            vm.run('rn_inline_pair_switch_party')
            if tab==start: assert vm.state()==before
            else:
                assert vm.persistent['rn_ip_party_group']==tab and vm.persistent['rn_ip_epoch']==8 and vm.arrays['rn_ip_party_target']==[Country('FRA')]
                assert not vm.requests and not any(k.startswith('rn_ip_cd_') for k in vm.persistent)
                # The next Apply (fresh epoch from the carrier) renames the newly pinned group.
                vm.enforce=True; vm.pair_count=vm.guard_count=0; vm.temp['rn_ip_cmd_epoch']=Decimal(8)
                vm.run('rn_inline_pair_apply_party'); assert len(vm.requests)==1 and get(get(vm.requests[0],'set_party_name'),'ideology')==GROUPS[tab-1][1]
            tab_cases+=1
    for blocker in ('closed','cooldown','bad tab'):
        vm=ProductVM(effects,locmap,chars,'party',tag='FRA'); vm.enforce=False; vm.temp['rn_ip_party_tab']=Decimal(5 if blocker=='bad tab' else 2)
        if blocker=='closed': vm.flags.clear()
        if blocker=='cooldown': vm.persistent['rn_ip_cd_party_until']=Decimal(1003)
        before=vm.state(); vm.run('rn_inline_pair_switch_party'); assert vm.state()==before, blocker
        tab_cases+=1
    cases+=tab_cases
    # Cooldown (iteration 3): starts only after success, blocks only its own type, survives as variables.
    cooldown_cases=0
    for kind in ('party','country'):
        other='country' if kind=='party' else 'party'
        ok=ProductVM(effects,locmap,chars,kind,tag='FRA'); ok.run('rn_inline_pair_apply_'+kind)
        assert len(ok.requests)==1 and ok.persistent['rn_ip_cd_'+kind+'_until']==Decimal(1005), ('start after success',kind)
        assert 'rn_ip_cd_'+other+'_until' not in ok.persistent and 'rn_ip_cd_leader_until' not in ok.persistent, 'cross-type start'
        assert ok.condition([('rn_ip_cooldown_active_'+kind,'=','yes')]) and not ok.condition([('rn_ip_cooldown_active_'+other,'=','yes')])
        cooldown_cases+=1
        rej=ProductVM(effects,locmap,chars,kind,tag='FRA'); rej.temp['rn_ip_cmd_epoch']=Decimal(6)
        before=rej.state(); rej.run('rn_inline_pair_apply_'+kind)
        assert rej.state()==before and 'rn_ip_cd_'+kind+'_until' not in rej.persistent, ('rejected Apply must not start cooldown',kind)
        cooldown_cases+=1
        for until,blocked in ((1001,True),(1005,True),(1000,False),(999,False)):
            vm=ProductVM(effects,locmap,chars,kind,tag='FRA'); vm.persistent['rn_ip_cd_'+kind+'_until']=Decimal(until)
            before=vm.state(); vm.run('rn_inline_pair_apply_'+kind)
            if blocked: assert vm.state()==before and not vm.requests and vm.temp['rn_pair_err']==11, ('cooldown guard',kind,until)
            else: assert len(vm.requests)==1 and vm.persistent['rn_ip_cd_'+kind+'_until']==Decimal(1005), ('expired cooldown',kind,until)
            cooldown_cases+=1
        # Independence: the OTHER type's and the leader's active cooldown do not block this type.
        vm=ProductVM(effects,locmap,chars,kind,tag='FRA'); vm.persistent['rn_ip_cd_'+other+'_until']=Decimal(1003); vm.persistent['rn_ip_cd_leader_until']=Decimal(1003)
        vm.run('rn_inline_pair_apply_'+kind); assert len(vm.requests)==1 and vm.temp['rn_pair_err']==0, ('types independent',kind)
        cooldown_cases+=1
        # Late cooldown (queued command after another success): second guard round rejects without writes.
        vm=ProductVM(effects,locmap,chars,kind,tag='FRA'); observed=[]
        def late(v,k=kind): v.persistent['rn_ip_cd_'+k+'_until']=Decimal(1002); observed.append(v.state())
        vm.late_mutation=late; vm.run('rn_inline_pair_apply_'+kind)
        assert vm.state()==observed[0] and not vm.requests and vm.temp['rn_pair_err']==11, ('late cooldown',kind)
        cooldown_cases+=1
    # Open is refused during the cooldown of the same type only.
    for blocked_kind,until in (('party',1003),('country',1003)):
        vm=ProductVM(effects,locmap,chars,'party',tag='FRA'); vm.flags.clear(); vm.enforce=False
        vm.persistent['rn_ip_cd_'+blocked_kind+'_until']=Decimal(until); before=vm.state(); vm.run('rn_inline_pair_open_party')
        assert (vm.state()==before) if blocked_kind=='party' else ('rn_ip_party_neutrality_open' in vm.flags)
        cooldown_cases+=1
    for k in ('country','leader','party'):
        vm=ProductVM(effects,locmap,chars,'party',tag='FRA'); vm.persistent['rn_ip_cd_'+k+'_until']=Decimal(1003)
        assert vm.localized('RN_IP_CD_LEFT_'+k.upper())==chars['RN_IP_CD_DAYS_3'] and vm.localized('RN_IP_CD_'+k.upper())==chars['RN_IP_CD_'+k.upper()+'_ACTIVE']
        vm.persistent['rn_ip_cd_'+k+'_until']=Decimal(1000); assert vm.localized('RN_IP_CD_'+k.upper())==''
        vm.persistent['rn_ip_cd_'+k+'_until']=Decimal(1045); assert vm.localized('RN_IP_CD_LEFT_'+k.upper())==chars['RN_IP_CD_DAYS_MORE']
        cooldown_cases+=1
    cases+=cooldown_cases
    # Source-driven rejection barrier, before and after validation; zero writes on each.
    mutations=[('epoch',lambda v:v.temp.update(rn_ip_cmd_epoch=Decimal(6)),8),('fractional epoch',lambda v:v.persistent.update(rn_ip_epoch=Decimal('7.25')),8),('root mismatch',lambda v:setattr(v,'root_tag','GER'),7),('foreign pin',lambda v:v.arrays.update(rn_ip_party_target=[Country('GER')]),9),('duplicate pin',lambda v:v.arrays.update(rn_ip_party_target=[Country('FRA'),Country('FRA')]),9),('legacy',lambda v:v.flags.add('rn_input'),7),('legacy-open',lambda v:v.flags.add('rn_open'),7),('group out of range',lambda v:v.persistent.update(rn_ip_party_group=Decimal(0)),9),('invalid B',lambda v:v.temp.update(rn_nativeb_31=Decimal('1.5')),5)]
    for late in (False,True):
        for label,mutate,want in mutations:
            vm=ProductVM(effects,locmap,chars,'party',tag='FRA')
            observed=[]
            if late:
                if label=='invalid B': continue
                def callback(v,fn=mutate): fn(v); observed.append(v.state())
                vm.late_mutation=callback
            else: mutate(vm)
            before=vm.state(); vm.run('rn_inline_pair_apply_party')
            assert vm.state()==(observed[0] if late else before) and not vm.requests and vm.temp['rn_pair_err']==want,(late,label)
            cases+=1
    # Generic own country branch still requires both inputs and a fresh capability.
    for cap,want in [(0,10),(2,10),(1,0)]:
        vm=ProductVM(effects,locmap,chars,'country',tag='FRA'); vm.temp['rn_native_cap']=Decimal(cap)
        before=vm.state(); vm.run('rn_inline_pair_apply_country')
        assert vm.temp['rn_pair_err']==want
        assert (vm.state()==before and not vm.requests) if want else (len(vm.requests)==1 and vm.guard_count==2)
        cases+=1
    # Actual Open source pins each group; unsupported custom group cannot mutate.
    for group,government in GROUPS+[(0,'custom_ideology')]:
        vm=ProductVM(effects,locmap,chars,'party',tag='FRA'); vm.flags.clear();vm.government=government;vm.enforce=False
        before=vm.state();vm.run('rn_inline_pair_open_party')
        assert (vm.persistent['rn_ip_party_group']==group and vm.arrays['rn_ip_party_target']==[Country('FRA')] and vm.persistent['rn_ip_epoch']==8) if group else vm.state()==before
        cases+=1
    # Deliberate missing late guard must trip VM's write barrier, without editing files.
    broken=copy.deepcopy(effects)
    first=success_if(broken['rn_inline_pair_apply_party']); second=success_if(first)
    # success_if returns new list; locate/remove the actual nested list node instead.
    late=get(next(v for k,_,v in broken['rn_inline_pair_apply_party'] if k=='if'),'if')
    late.remove(('rn_inline_pair_guard_party','=','yes'))
    try: ProductVM(broken,locmap,chars,'party',tag='FRA').run('rn_inline_pair_apply_party')
    except AssertionError as exc: assert 'write before late guard' in str(exc)
    else: raise AssertionError('negative fixture missing late guard survived')
    # Other contract mutations are rejected by the independent structural checks.
    rejected=1
    for mutate in ('partial group gate','ctor temp enabled','country geometry','raw party carrier','unscaled icon','cancel under apply','missing enter','narrow field','status in guard','pencil ignores cooldown','cooldown on reject','escape back','government gate back','tab writes name'):
        ee,mm,gg,tt,ll=map(copy.deepcopy,( {k:effects[k] for k in own_effects},models,gui,TRIGGERS,locs))
        if mutate=='partial group gate': get(tt['rn_ipp_party_target_matches'],'OR').pop()
        elif mutate=='ctor temp enabled': get(get(mm['rn_ip_country_gui'],'triggers'),'rn_ip_country_apply_click_enabled').append(('check_variable','=',[('temp_var:rn_native_cap','=','1')]))
        elif mutate=='country geometry': node=named(gg)['rn_ip_country_window']; node[:]=[(k,op,[('width','=','420'),('height','=','40')] if k=='size' else v) for k,op,v in node]
        elif mutate=='cancel under apply': node=named(gg)['rn_ip_leader_cancel']; node[:]=[(k,op,[('x','=','380'),('y','=','5')] if k=='position' else v) for k,op,v in node]
        elif mutate=='missing enter': named(gg)['rn_ip_party_neutrality_apply'].remove(('shortcut','=','RETURN'))
        elif mutate=='narrow field': node=named(gg)['rn_ip_country_adj_edit']; node[:]=[(k,op,[('x','=','176'),('y','=','20')] if k=='size' else v) for k,op,v in node]
        elif mutate=='status in guard': tt['rn_ipp_party_target_matches'].append(('has_variable','=','rn_ip_status_err'))
        elif mutate=='pencil ignores cooldown': get(get(mm['rn_ip_party_neutrality_launcher_gui'],'triggers'),'rn_ip_party_neutrality_open_click_enabled').remove(('NOT','=',[('rn_ip_cooldown_active_party','=','yes')]))
        elif mutate=='escape back': named(gg)['rn_ip_leader_cancel'].append(('shortcut','=','ESCAPE'))
        elif mutate=='government gate back': tt['rn_ipp_party_target_matches'].append(('has_government','=','neutrality'))
        elif mutate=='tab writes name': get(ee['rn_inline_pair_switch_party'],'if').append(('rn_inline_party_finish','=','yes'))
        elif mutate=='cooldown on reject': ee['rn_inline_pair_cancel_party']=ee['rn_inline_pair_cancel_party']+[('rn_ip_cooldown_start_party','=','yes')]
        elif mutate=='unscaled icon': named(gg)['rn_ip_party_neutrality_open'].remove(('scale','=','0.67'))
        else:
            node=named(gg)['rn_ip_party_neutrality_prefill'];node[:]=[(k,op,'[ROOT.GetRulingParty]' if k=='text' else v) for k,op,v in node]
        try: structural(ee,mm,gg,tt,ll)
        except AssertionError: rejected+=1
        else: raise AssertionError(('negative contract mutation survived',mutate))
    files={p.relative_to(HERE).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='static-review.json'}
    report={'date':'2026-10-11','scope':'Inactive source-only product QA; limited VM records setter requests, no engine/UI/native/MP acceptance','activated':False,'blockers':[], 'protected_files_unchanged':len(protected),'game_files':len(gamefiles),'models':len(models),'native_fields':5,'actual_pair_source_cases':cases,'negative_contract_mutations_rejected':rejected,'pure_helpers_byte_identical':True,'iteration':4,'party_tabs':'4 base groups, tab = re-pin + group + new epoch (bridge re-prefills on epoch change), any government','tab_vm_cases':tab_cases,'escape':'removed; vanilla politics close_button owns Esc','country_launcher':'title line, name right-aligned (hoi_18mbs) ending at the 20px pencil','subjects':'hidden placeholder rn_ip_subject_gui (diplomacy_target_context), switches always=no','editors':'framed overlays 420px wide, five hoi_18 fields 356x20 (>=32x11px widest glyph), ignore_enter, Apply RETURN (no ESCAPE), status line; party editor 18,266 420x102 with 4 group tabs','leader_pencil':'154,242 20px above leader_name, outside its text box','party_pencil':'228,310 20px in ruling_party_info','country_editor':'18,28 420x74 two framed rows','global_entry_override':OVERRIDE,'shortcut_buttons':3,'cooldown':'5 game days per type (rn_ip_cooldown_days), expiry day = global.num_days+5 on success, error 11, pencils disabled with remaining-day tooltip','cooldown_vm_cases':cooldown_cases,'icon_buttons_scaled':sum(1 for kind,_,body in walk(gui) if kind=='buttonType' and any(k=='scale' for k,_,_ in body)),'party_base_groups':dict(GROUPS),'cancel_after_government_change':True,'empty_prefill_on_bad_pin':True,'runtime_open':['new 4-group script parser/branches and generic own-country leader guard','conditional empty carriers and target-mismatch label','Esc closes the politics panel: editor must hide with it (PID49352 left it on screen; parent_window_token=politics_tab is already set)','tab switch re-prefill while a field has focus (bridge skips focused drafts)','non-ruling party getters GetDemocraticParty/... and set_party_name on a non-ruling group','country name on the title line vs long names','subject placeholder position in the diplomacy view','CEditBox character capacity vs field width (PID42644: 19/16 chars)','editor overlays covering faction/pie/portrait while open','status line after rejected Apply','cooldown: subtract_from_temp_variable inside scripted trigger/loc, global.num_days/global.date, GetDateStringNoHourLong on a stored date, disabled-pencil tooltip; needs unpaused time','dependencies-based load order of the rn_entry_gui override','native vanilla leader/party caption refresh currently requires panel reopen','local player lifecycle/menu-load/draft/Enter/focus and multiplayer not accepted here'],'files':files}
    if '--write-report' in sys.argv: (HERE/'static-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except (AssertionError,KeyError,ValueError) as exc:
        print('FAIL:',repr(exc),file=sys.stderr);sys.exit(1)
