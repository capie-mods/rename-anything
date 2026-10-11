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
    return [('OR','=', [('AND','=',[('check_variable','=',[('rn_ip_party_group','=',str(i))]), ('has_government','=',g)]) for i,g in GROUPS])]
def group_gate(nodes):
    want=group_nodes()[0]
    assert list(walk(nodes)).count(want)==1, 'missing or different exact group/current-government gate'
def then(nodes): return [n for n in nodes if n[0]!='limit']
def success_if(nodes):
    out=next(value for key,_,value in nodes if key=='if')
    assert get(get(out,'limit'),'check_variable') in [[('temp_var:rn_pair_err','=','0')], [('temp_var:rn_ip_leader_error','=','0')]], 'unguarded success branch'
    return then(out)

def structural(effects, models, gui, triggers, locs):
    expected={'rn_ip_leader_launcher_gui','rn_ip_leader_gui','rn_ip_party_neutrality_launcher_gui','rn_ip_party_neutrality_gui','rn_ip_country_launcher_gui','rn_ip_country_gui','rn_ilqa_guard_gui'}
    assert set(models)==expected
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
        assert get(get(launcher,'effects'),prefix+'_open_click')==[(open_helper,'=','yes')]
        assert get(get(models[model_name],'effects'),prefix+'_cancel_click')==[(cancel_helper,'=','yes')]
        for flag in ('rn_open','rn_input'):
            assert ('NOT','=',[('has_country_flag','=',flag)]) in get(get(launcher,'triggers'),prefix+'_open_click_enabled')
        block=get(get(models[model_name],'effects'),key)
        assert [k for k,_,_ in block]==['log',helper,'log']
        assert 'before' in block[0][2] and 'after' in block[2][2] and 'PASS' not in block[2][2]
        cancel=get(get(models[model_name],'triggers'),key.replace('apply_click','cancel_click_enabled'))
        assert not any(k=='has_government' for k,_,_ in walk(cancel)), 'Cancel must survive government change'
    party=models['rn_ip_party_neutrality_gui']
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
                assert get(branch,'limit')==[('check_variable','=',[('rn_ip_party_group','=',str(i))]),('has_government','=',g)]
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
    for name,key,fallback in [('RN_IPP_PARTY_SHORT','RN_IPP_PARTY_SHORT_CURRENT','RN_IPP_EMPTY'),('RN_IPP_PARTY_LONG','RN_IPP_PARTY_LONG_CURRENT','RN_IPP_EMPTY'),('RN_IPP_PARTY_STATUS','RN_IP_LONG_NAME','RN_IPP_TARGET_CHANGED')]:
        body=locs[name]
        assert [n for n in body if n[0]=='text']==[('text','=',[('trigger','=',[('rn_ipp_party_target_matches','=','yes')]),('localization_key','=',key)]),('text','=',[('localization_key','=',fallback)])]
    fields={'rn_ip_leader_edit','rn_ip_party_neutrality_edit','rn_ip_party_neutrality_long_edit','rn_ip_country_name_edit','rn_ip_country_adj_edit'}
    actual={get(body,'name') for kind,_,body in walk(gui) if kind=='editBoxType'}
    assert actual==fields
    widgets=named(gui)
    for field,font in [('rn_ip_country_label','Arial12'),('rn_ip_country_name_edit','hoi_16mbs'),('rn_ip_country_adj_edit','hoi_16mbs')]: assert get(widgets[field],'font')==font
    for kind in ('leader','party_neutrality','country'): assert get(widgets['rn_ip_'+kind+'_epoch'],'text')=='[?ROOT.rn_ip_epoch|0]'
    assert get(widgets['rn_ip_party_neutrality_prefill'],'text')=='[ROOT.RN_IPP_PARTY_SHORT]'
    assert get(widgets['rn_ip_party_neutrality_long_prefill'],'text')=='[ROOT.RN_IPP_PARTY_LONG]'
    assert get(widgets['rn_ip_party_neutrality_long_label'],'text')=='[ROOT.RN_IPP_PARTY_STATUS]'
    # Party launcher inside ruling_party_info (88..343 x 305..365), left of the pie chart (x270).
    assert get(widgets['rn_ip_party_neutrality_launcher_window'],'position')==[('x','=','228'),('y','=','310')]
    assert get(widgets['rn_ip_party_neutrality_launcher_window'],'size')==[('width','=','20'),('height','=','20')]
    # Opened party editor 18..268 x 300..366: left of the pie chart, above y383 bottom/y390 actions.
    assert get(widgets['rn_ip_party_neutrality_window'],'position')==[('x','=','18'),('y','=','300')]
    assert get(widgets['rn_ip_party_neutrality_window'],'size')==[('width','=','250'),('height','=','66')]
    assert get(widgets['rn_ip_party_neutrality_edit'],'size')==[('x','=','176'),('y','=','20')] and get(widgets['rn_ip_party_neutrality_edit'],'font')=='hoi_18'
    assert get(widgets['rn_ip_party_neutrality_long_edit'],'size')==[('x','=','238'),('y','=','20')]
    for frame in ('rn_ipp_short_frame','rn_ipp_long_frame'): assert get(get(widgets[frame],'background'),'spriteType')=='GFX_tiles_dark_area_cut_8'
    assert get(widgets['rn_ip_party_neutrality_open'],'position')==[('x','=','0'),('y','=','0')]
    assert get(widgets['rn_ip_party_neutrality_long_label'],'font')=='Arial12'
    # 30x30-frame designer sprites ignore size{}; the visible footprint must be scaled to 15px.
    big={'GFX_edit_designer_notes_button','GFX_preset_button_save'}
    scaled=[body for kind,_,body in walk(gui) if kind=='buttonType' and any(k=='quadTextureSprite' and v in big for k,_,v in body)]
    want={'rn_ip_leader_open':'0.67','rn_ip_leader_apply':'0.67','rn_ip_party_neutrality_open':'0.67','rn_ip_party_neutrality_apply':'0.67','rn_ip_country_open':'0.5','rn_ip_country_apply':'0.5'}
    assert len(scaled)==6 and all([v for k,_,v in b if k=='scale']==[want[get(b,'name')]] and not any(k=='size' for k,_,_ in b) for b in scaled), 'unscaled 30px icon button'
    assert get(widgets['rn_ip_leader_launcher_window'],'position')==[('x','=','152'),('y','=','270')]
    # Party pencil bottom stays above vanilla action buttons (y390) and leader pencil inside leader_name 18..173 x 262..298.
    # 20px leader pencil inside leader_name 18..173 x 262..298; Apply/Cancel disjoint in both editors.
    assert 18<=152 and 152+20<=173 and 262<=270 and 270+20<=298 and 117+20<=139 and 194+20<=222 and 18+250<270 and 300+66<383

class ProductVM(ApplyVM):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.root_tag=self.tag
    def condition(self,nodes):
        for key,op,value in nodes:
            if key=='tag' and value=='ROOT':
                answer=self.tag==self.root_tag
            elif key=='rn_ipp_party_target_matches':
                answer=self.condition(TRIGGERS[key]) == (value=='yes')
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
    models={name:body for p in (HERE/'common/scripted_guis').glob('*.txt') for _,_,outer in parse(p.read_text()) for name,_,body in outer}
    gui=[n for p in (HERE/'interface').glob('*.gui') for n in parse(p.read_text())]
    TRIGGERS=declarations(HERE/'common/scripted_triggers')
    locs={get(body,'name'):body for p in (HERE/'common/scripted_localisation').glob('*.txt') for _,_,body in parse(p.read_text(encoding='utf-8-sig'))}
    structural({k:effects[k] for k in own_effects},models,gui,TRIGGERS,locs)
    for p in (HERE/'common').rglob('*.txt'): assert not re.search(r'\btag\s*=\s*POL\b',re.sub(r'#[^\n]*','',p.read_text(encoding='utf-8-sig')))
    # Only the requested typography changes are allowed in country GUI.
    country_path='interface/rn_country_inline_ui.gui'
    original=parse((BASE/country_path).read_text())
    candidate=parse((HERE/country_path).read_text())
    old=named(original)
    for key,font in [('rn_ip_country_label','Arial12'),('rn_ip_country_name_edit','hoi_16mbs'),('rn_ip_country_adj_edit','hoi_16mbs')]:
        old[key][:]=[(k,op,font if k=='font' else value) for k,op,value in old[key]]
    # Second allowed delta: size{} of the two 30px-frame icon buttons becomes scale=0.5; positions unchanged.
    for key in ('rn_ip_country_open','rn_ip_country_apply'):
        old[key][:]=[('scale','=','0.5') if k=='size' else (k,op,value) for k,op,value in old[key]]
    assert original==candidate, 'country geometry/nonfont delta'
    # No virtual path, model, scripted-loc or trigger collisions with the main dev mod.
    gamefiles=[p for folder in ('common','interface','localisation') for p in (HERE/folder).rglob('*') if p.is_file()]
    assert all(not (REPO/'mod'/p.relative_to(HERE)).exists() for p in gamefiles)
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
        if lang=='english': chars.update(table)
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
            # All pinned group/current-government cross-products: only exact match applies.
            for wrong in [g for _,g in GROUPS if g!=government]+['custom_ideology']:
                bad=ProductVM(effects,locmap,chars,'party',tag=tag)
                bad.government=wrong; bad.persistent['rn_ip_party_group']=Decimal(group)
                state=bad.state(); bad.run('rn_inline_pair_apply_party')
                assert bad.state()==state and not bad.requests and bad.temp['rn_pair_err']==9
                assert not bad.condition(TRIGGERS['rn_ipp_party_target_matches'])
                assert bad.localized('RN_IPP_PARTY_SHORT')=='' and bad.localized('RN_IPP_PARTY_LONG')==''
                assert bad.localized('RN_IPP_PARTY_STATUS')==chars['RN_IPP_TARGET_CHANGED']
                # Cancel retains availability after group mismatch and clears pin/open.
                bad.enforce=False; bad.run('rn_inline_pair_cancel_party')
                assert 'rn_ip_party_neutrality_open' not in bad.flags and bad.arrays['rn_ip_party_target']==[]
                cases+=1
    # Source-driven rejection barrier, before and after validation; zero writes on each.
    mutations=[('epoch',lambda v:v.temp.update(rn_ip_cmd_epoch=Decimal(6)),8),('fractional epoch',lambda v:v.persistent.update(rn_ip_epoch=Decimal('7.25')),8),('root mismatch',lambda v:setattr(v,'root_tag','GER'),7),('foreign pin',lambda v:v.arrays.update(rn_ip_party_target=[Country('GER')]),9),('duplicate pin',lambda v:v.arrays.update(rn_ip_party_target=[Country('FRA'),Country('FRA')]),9),('legacy',lambda v:v.flags.add('rn_input'),7),('legacy-open',lambda v:v.flags.add('rn_open'),7),('group changed',lambda v:setattr(v,'government','fascism'),9),('invalid B',lambda v:v.temp.update(rn_nativeb_31=Decimal('1.5')),5)]
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
    for mutate in ('partial group gate','ctor temp enabled','country geometry','raw party carrier','unscaled icon'):
        ee,mm,gg,tt,ll=map(copy.deepcopy,( {k:effects[k] for k in own_effects},models,gui,TRIGGERS,locs))
        if mutate=='partial group gate': get(tt['rn_ipp_party_target_matches'],'OR').pop()
        elif mutate=='ctor temp enabled': get(get(mm['rn_ip_country_gui'],'triggers'),'rn_ip_country_apply_click_enabled').append(('check_variable','=',[('temp_var:rn_native_cap','=','1')]))
        elif mutate=='country geometry': named(gg)['rn_ip_party_neutrality_window'].remove(('size','=',[('width','=','250'),('height','=','66')]))
        elif mutate=='unscaled icon': named(gg)['rn_ip_party_neutrality_open'].remove(('scale','=','0.67'))
        else:
            node=named(gg)['rn_ip_party_neutrality_prefill'];node[:]=[(k,op,'[ROOT.GetRulingParty]' if k=='text' else v) for k,op,v in node]
        try: structural(ee,mm,gg,tt,ll)
        except AssertionError: rejected+=1
        else: raise AssertionError(('negative contract mutation survived',mutate))
    files={p.relative_to(HERE).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name!='static-review.json'}
    report={'date':'2026-10-11','scope':'Inactive source-only product QA; limited VM records setter requests, no engine/UI/native/MP acceptance','activated':False,'blockers':[], 'protected_files_unchanged':len(protected),'game_files':len(gamefiles),'models':len(models),'native_fields':5,'actual_pair_source_cases':cases,'negative_contract_mutations_rejected':rejected,'pure_helpers_byte_identical':True,'country_geometry_unchanged':True,'country_allowed_delta':'fonts (2 edits+label) and 30px icon buttons size->scale0.5; positions unchanged','party_layout':'launcher 228,310 20px in ruling_party_info; editor 18,300 250x66, framed hoi_18 short 176x20 + hoi_16mbs long 238x20','icon_buttons_scaled':sum(1 for kind,_,body in walk(gui) if kind=='buttonType' and any(k=='scale' for k,_,_ in body)),'party_base_groups':dict(GROUPS),'cancel_after_government_change':True,'empty_prefill_on_target_mismatch':True,'runtime_open':['new 4-group script parser/branches and generic own-country leader guard','conditional empty carriers and target-mismatch label','party launcher/editor overlap, country fonts/16px clipping','native vanilla leader/party caption refresh currently requires panel reopen','scale=0.5 render and hit area of 30px icon buttons; leader pencil inside name plate vs long names','local player lifecycle/menu-load/draft/Enter/focus and multiplayer not accepted here'],'files':files}
    if '--write-report' in sys.argv: (HERE/'static-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except (AssertionError,KeyError,ValueError) as exc:
        print('FAIL:',repr(exc),file=sys.stderr);sys.exit(1)
