"""Client.

The important part is `field()` and `formFor()`: controls are generated from
the registry declarations that arrive at /api/bootstrap. Nothing about any
individual test, plot or API source is written here. Adding a test to the
Python registry makes it appear in the UI with correct controls and no
JavaScript change at all.
"""

JS = r"""
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const el=(t,c,h)=>{const e=document.createElement(t); if(c)e.className=c;
  if(h!==undefined)e.innerHTML=h; return e;};
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const num=(v,d=3)=>v==null||v!==v?'—':(Math.abs(v)<0.0001&&v!==0?v.toExponential(2):Number(v).toFixed(d));


// ── stains ────────────────────────────────────────────────────────────
// Each family of content is bound to one real histology stain, so a colour
// on screen always means the same kind of thing. Statistics are hematoxylin
// violet; anything eosin pink concerns significance or effect size.
const STAIN={
  'Descriptives':'methylene', 'Assumption checks':'iodine',
  'Two groups':'haem', 'Three or more groups':'haem',
  'Post hoc and multiplicity':'eosin', 'Categorical and proportions':'safranin',
  'Correlation and agreement':'fastgreen', 'Regression':'crystal',
  'Survival':'congo', 'Diagnostic accuracy and prediction':'methylene',
  'Meta-analysis':'trypan', 'Epidemiology and causal':'silver',
  'Power and sample size':'iodine', 'Bench and omics':'pas',
  'Bayesian and equivalence':'eosin',
  'Group comparison':'haem', 'Distribution':'methylene', 'Relationships':'crystal',
  'Clinical':'congo', 'Bench':'pas', 'Reporting diagrams':'fastgreen',
  'Literature':'methylene', 'Trial registries':'trypan',
  'Drugs and safety':'safranin', 'Molecular':'pas', 'Population':'silver',
  'Workbench':'methylene', 'Evidence':'trypan', 'Output':'fastgreen',
  'Reference':'haem',
  'Start here':'haem', 'Doing a review':'trypan',
  'Choosing and running a test':'methylene', 'Reading what comes back':'eosin',
  'Producing the output':'fastgreen',
};
const stainOf=g=>STAIN[g]||'silver';

let BOOT=null, STATE={pane:'data', entry:null, dataset:null, dsMeta:null, test:null, plot:null,
  source:'pubmed', result:null, roles:{}, params:{}, plotParams:{}, stage:'title_abstract',
  reviewer:null, reviewers:[], blind:true, instrument:'rob2', form:'rct', queue:[], qi:0};

// ── plumbing ──────────────────────────────────────────────────────────
async function api(path, opts={}){
  const r=await fetch(path, {headers:{'Content-Type':'application/json'}, ...opts});
  let j; try{ j=await r.json(); }catch(e){ throw new Error('Bad response from '+path); }
  if(!r.ok && !j.errors && !j.error) throw new Error(j.message||('HTTP '+r.status));
  return j;
}
function toast(msg, kind=''){
  const t=el('div','toast '+kind, esc(msg)); document.body.appendChild(t);
  setTimeout(()=>t.remove(), kind==='err'?7000:3200);
}
function pval(p){ if(p==null)return '—';
  return p<0.001 ? 'p < .001' : 'p = '+p.toFixed(p<0.01?4:3).replace(/^0/,''); }
function starsFor(p){ if(p==null)return '';
  return p<0.001?'***':p<0.01?'**':p<0.05?'*':'ns'; }


// ── hover help ────────────────────────────────────────────────────────
// One floating tip serves every ? on the page, positioned against whichever
// one asked for it and clamped inside the viewport. Long explanations live
// behind the mark so a screen opens with controls, not prose.
function qmark(title, text, cls){
  const b=el('button','qmark'+(cls?' '+cls:''),'?');
  b.type='button';
  b.dataset.tipTitle=title||''; b.dataset.tip=text||'';
  b.setAttribute('aria-label', title?('About '+title):'Help');
  return b;
}
function showTip(src){
  const text=src.dataset.tip; if(!text) return;
  const t=$('#tip'); if(!t) return;
  t.innerHTML=(src.dataset.tipTitle?`<b>${esc(src.dataset.tipTitle)}</b>`:'')+
    esc(text).replace(/`([^`]+)`/g,'<code>$1</code>');
  t.hidden=false;
  const r=src.getBoundingClientRect(), tb=t.getBoundingClientRect();
  let left=r.left, top=r.bottom+7;
  if(left+tb.width>window.innerWidth-10) left=window.innerWidth-tb.width-10;
  if(top+tb.height>window.innerHeight-10) top=Math.max(10, r.top-tb.height-7);
  t.style.left=Math.max(10,left)+'px'; t.style.top=top+'px';
}
function hideTip(){ const t=$('#tip'); if(t) t.hidden=true; }
document.addEventListener('mouseover', e=>{ const q=e.target.closest('.qmark'); if(q) showTip(q); });
document.addEventListener('mouseout', e=>{ if(e.target.closest('.qmark')) hideTip(); });
document.addEventListener('focusin', e=>{ const q=e.target.closest('.qmark'); q?showTip(q):hideTip(); });
window.addEventListener('scroll', hideTip, true);
window.addEventListener('resize', hideTip);

// Anything longer than a glance goes behind the mark; short notes stay inline.
const HINT_THRESHOLD=64;

// Confirmation for anything that removes data. Honest about what goes and
// what survives, and never fires without an explicit yes.
async function confirmDestructive(what, detail){
  if(BOOT && BOOT.config.confirm_destructive===false) return true;
  return window.confirm(what+(detail?('\n\n'+detail):'')+'\n\nThis cannot be undone.');
}

// ── field generation ──────────────────────────────────────────────────
function columnsOfKind(kind){
  if(!STATE.dsMeta) return [];
  const d=STATE.dsMeta.dictionary||{};
  if(kind==='any') return Object.keys(d);
  const want={continuous:['continuous'],categorical:['categorical','binary','ordinal'],
    binary:['binary'],ordinal:['ordinal','binary'],id:['id','categorical','text'],
    time:['time','continuous'],event:['binary','ordinal']}[kind]||[kind];
  return Object.keys(d).filter(c=>want.includes(d[c].kind));
}

function field(p, value, onChange){
  const f=el('div','field'+(p.adv?' adv':''));
  if(p.depends){ f.dataset.dep=p.depends.param; f.dataset.depVal=String(p.depends.equals); }
  const lab=el('label',null, esc(p.label)+(p.unit?` <span class="unit">${esc(p.unit)}</span>`:''));
  f.appendChild(lab);
  let input;
  const set=v=>{ onChange(p.id, v); syncDeps(); };
  switch(p.type){
    case 'bool': {
      f.innerHTML='';
      const w=el('label','check'); const cb=el('input'); cb.type='checkbox';
      cb.checked=!!value; cb.onchange=()=>set(cb.checked);
      w.appendChild(cb); w.appendChild(el('span',null,esc(p.label))); f.appendChild(w);
      break; }
    case 'select': {
      input=el('select');
      (p.choices||[]).forEach(c=>{ const o=el('option',null,esc(c[1])); o.value=c[0];
        if(String(value)===String(c[0]))o.selected=true; input.appendChild(o); });
      input.onchange=()=>set(input.value); f.appendChild(input); break; }
    case 'multiselect': {
      const box=el('div','chips'); const cur=new Set(value||[]);
      (p.choices||[]).forEach(c=>{ const o=el('div','chip'+(cur.has(c[0])?' on':''),esc(c[1]));
        o.onclick=()=>{ cur.has(c[0])?cur.delete(c[0]):cur.add(c[0]);
          o.classList.toggle('on'); set([...cur]); };
        box.appendChild(o); });
      f.appendChild(box); break; }
    case 'column': case 'columns': {
      const cols=STATE.dsMeta?Object.keys(STATE.dsMeta.dictionary||{}):[];
      if(p.type==='column'){
        input=el('select'); input.appendChild(el('option',null,'—'));
        cols.forEach(c=>{ const o=el('option',null,esc(c)); o.value=c;
          if(value===c)o.selected=true; input.appendChild(o); });
        input.onchange=()=>set(input.value||null); f.appendChild(input);
      } else {
        const box=el('div','chips'); const cur=new Set(value||[]);
        cols.forEach(c=>{ const o=el('div','chip'+(cur.has(c)?' on':''),esc(c));
          o.onclick=()=>{ cur.has(c)?cur.delete(c):cur.add(c); o.classList.toggle('on');
            set([...cur]); }; box.appendChild(o); });
        f.appendChild(box);
      } break; }
    case 'textarea': {
      input=el('textarea'); input.value=value==null?'':value;
      if(p.placeholder)input.placeholder=p.placeholder;
      input.oninput=()=>set(input.value); f.appendChild(input); break; }
    default: {
      input=el('input');
      input.type=(p.type==='number'||p.type==='int')?'number':'text';
      if(p.step)input.step=p.step; else if(p.type==='number')input.step='any';
      if(p.min!=null)input.min=p.min; if(p.max!=null)input.max=p.max;
      if(p.placeholder)input.placeholder=p.placeholder;
      input.value=value==null?'':value;
      input.oninput=()=>set(input.value===''?null:
        (p.type==='int'?parseInt(input.value):p.type==='number'?parseFloat(input.value):input.value));
      f.appendChild(input);
    }
  }
  if(p.help){
    if(p.help.length>HINT_THRESHOLD){
      const lab=f.querySelector('label')||f.querySelector('.check');
      if(lab) lab.appendChild(qmark(p.label, p.help));
      else f.appendChild(el('div','help',esc(p.help)));
    } else {
      f.appendChild(el('div','help',esc(p.help)));
    }
  }
  return f;
}

function syncDeps(){
  $$('[data-dep]').forEach(f=>{
    const v=STATE.params[f.dataset.dep];
    f.style.display = String(v)===f.dataset.depVal ? '' : 'none';
  });
}

function roleField(r){
  const f=el('div','field');
  f.appendChild(el('label',null, esc(r.label)+
    ` <span class="unit">${esc(r.kind)}${r.max>1?' ×'+r.max:''}${r.optional?' · optional':''}</span>`));
  const cols=columnsOfKind(r.kind);
  const cur=new Set(STATE.roles[r.id]||[]);
  if(!cols.length){ f.appendChild(el('div','help','No '+esc(r.kind)+
    ' variables in this dataset. Adjust the variable dictionary in the Data pane.')); return f; }
  const box=el('div','chips');
  cols.forEach(c=>{ const o=el('div','chip'+(cur.has(c)?' on':''),esc(c));
    o.onclick=()=>{
      if(cur.has(c)) cur.delete(c);
      else { if(r.max===1) cur.clear(); cur.add(c); }
      STATE.roles[r.id]=[...cur]; renderPane(); preflight();
    }; box.appendChild(o); });
  f.appendChild(box);
  if(r.help){
    const lab=f.querySelector('label');
    if(r.help.length>HINT_THRESHOLD && lab) lab.appendChild(qmark(r.label, r.help));
    else f.appendChild(el('div','help',esc(r.help)));
  }
  return f;
}

function formFor(entry, target){
  (entry.roles||[]).forEach(r=>target.appendChild(roleField(r)));
  const groups={};
  (entry.params||[]).forEach(p=>{ (groups[p.group||'']=groups[p.group||'']||[]).push(p); });
  Object.entries(groups).forEach(([g,ps])=>{
    if(g) target.appendChild(el('div','rail-head',esc(g)));
    ps.forEach(p=>target.appendChild(field(p, STATE.params[p.id],
      (k,v)=>{ STATE.params[k]=v; })));
  });
  syncDeps();
}


// One explanation per screen, behind the ? beside its heading.
const PANE_TIP={
 data:["Data","Everything starts here. The inferred type of each variable decides which tests will accept it, so a 0/1 column read as continuous is the commonest silent error in the whole tool. Correct the dictionary before running anything."],
 stats:["Statistics","Pick a test, assign variables to its roles, and the assumption gate runs before anything touches the data. A red lozenge means the test is wrong for this data, and it names the test that is right. Every run is written to the ledger, including blocked ones."],
 figures:["Figures","Built from a result rather than from the data, so the annotation can never disagree with the statistics that produced it. Significance brackets stack themselves. Journal presets set real column widths: 89 mm single, 183 mm double."],
 harvest:["Harvest","Each source is a search against a live API. Results land in one shared corpus, deduplicated across sources by DOI and by fuzzy title. Trim the corpus below if a search came back wider than you wanted."],
 screen:["Screening","Keyboard-driven: `i` include, `e` exclude, `m` maybe, `u` undo. Undo genuinely deletes the last judgement rather than just stepping back. Screen under two different reviewer names to get a kappa."],
 synthesis:["Synthesis","Extraction forms, risk of bias, and the conversion from arm-level numbers into effect sizes and standard errors that the meta-analysis expects. Ratio measures come out on the log scale, which is what it wants."],
 report:["Report","The methods paragraph is assembled from the ledger, so it describes what was actually executed rather than what you meant to do. Read it before pasting it: it is a draft, not a fact."],
 runs:["Run ledger","Every test ever executed, with its data hash, spec, seed and package versions. This is what makes the multiplicity audit possible and what stops eight quiet attempts becoming one reported result. Deleting entries is allowed but it is the audit trail you are deleting."],
 library:["Handbook","Reference that travels with the tool. The review half explains the order the steps go in and why, and names the pane that handles each one. The statistics half covers choosing a test, what the numbers mean, and the ways results get misread. Links inside an article jump to the pane being described."],
 settings:["Settings","Statistical defaults live here rather than on each test, because an alpha you can change per test after seeing the result is not an alpha. The danger zone at the bottom is the only place that removes whole categories at once."],
};

// ── rail ──────────────────────────────────────────────────────────────
const PANES=[
  ['Workbench',[['data','Data','1'],['stats','Statistics','2'],['figures','Figures','3']]],
  ['Evidence',[['harvest','Harvest','4'],['screen','Screening','5'],['synthesis','Synthesis','6']]],
  ['Output',[['report','Report','7'],['runs','Run ledger','8']]],
  ['Reference',[['library','Handbook','0'],['settings','Settings','9']]],
];

function renderRail(){
  const rail=$('#rail'); rail.innerHTML='';
  PANES.forEach(([g,items])=>{
    const grp=el('div','rail-group');
    grp.appendChild(el('div','rail-head '+stainOf(g), esc(g)));
    items.forEach(([id,label,key])=>{
      const it=el('div','nav'+(STATE.pane===id?' on':''),
        `<span>${esc(label)}</span><span class="count">${key}</span>`);
      it.onclick=()=>{ STATE.pane=id; renderRail(); renderPane(); };
      grp.appendChild(it);
    });
    rail.appendChild(grp);
  });
  if(BOOT){
    const foot=el('div','rail-foot');
    foot.innerHTML=`<b>${BOOT.counts.tests_ready} of ${BOOT.counts.tests_total} tests</b>`+
      `${BOOT.counts.plots_total} figure types<br>${BOOT.counts.sources_total} sources`;
    rail.appendChild(foot);
  }
}

function panel(title, hint, stainClass, tip){
  const p=el('div','panel');
  const h=el('div','panel-head');
  h.appendChild(el('h3',null,esc(title)));
  if(tip) h.appendChild(qmark(title, tip));
  if(stainClass) h.appendChild(el('span','tool-tag '+stainClass, esc(stainClass)));
  if(hint) h.appendChild(el('div','hint',esc(hint)));
  const chev=el('span','chev','\u25be');
  if(!hint) chev.style.marginLeft='auto';
  h.appendChild(chev);
  const b=el('div','panel-body');
  p.append(h,b);
  h.onclick=e=>{ if(!['BUTTON','INPUT','SELECT','TEXTAREA','A','OPTION'].includes(e.target.tagName))
    p.classList.toggle('collapsed'); };
  return [p,b];
}


// ── the handbook ──────────────────────────────────────────────────────
// A small markdown subset, rendered inline. Deliberately small: headings,
// bold, code, lists, tables, callouts and two kinds of internal link. Links
// of the form #pane:stats jump to a pane; #entry:meta opens another article.
function md(src){
  const lines=String(src).split('\n');
  let out='', para=[], inTable=false, tHead=false, listType=null;
  const inline=t=>esc(t)
    .replace(/`([^`]+)`/g,'<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\(#pane:([a-z]+)\)/g,
      '<a class="xlink" data-pane="$2">$1</a>')
    .replace(/\[([^\]]+)\]\(#entry:([a-z-]+)\)/g,
      '<a class="xlink" data-entry="$2">$1</a>');
  const flush=()=>{ if(para.length){ out+='<p>'+inline(para.join(' '))+'</p>'; para=[]; } };
  const closeList=()=>{ if(listType){ out+='</'+listType+'>'; listType=null; } };
  for(let raw of lines){
    const l=raw.trimEnd();
    if(/^\s*$/.test(l)){ flush(); closeList(); if(inTable){out+='</tbody></table></div>';inTable=false;} continue; }
    if(/^```/.test(l)){
      flush(); closeList();
      if(out.endsWith('</pre>')) continue;
      const i=lines.indexOf(raw); let buf=[];
      for(let j=i+1;j<lines.length && !/^```/.test(lines[j]);j++){ buf.push(lines[j]); lines[j]='\u0000'; }
      out+='<pre class="term">'+esc(buf.join('\n'))+'</pre>'; continue;
    }
    if(l==='\u0000') continue;
    if(/^\|/.test(l)){
      flush(); closeList();
      const cells=l.split('|').slice(1,-1).map(c=>c.trim());
      if(/^[\s|:-]+$/.test(l)){ tHead=false; out+='</thead><tbody>'; continue; }
      if(!inTable){ inTable=true; tHead=true;
        out+='<div class="tablewrap"><table><thead><tr>'+
          cells.map(c=>'<th>'+inline(c)+'</th>').join('')+'</tr>'; continue; }
      out+='<tr>'+cells.map(c=>'<td>'+inline(c)+'</td>').join('')+'</tr>'; continue;
    } else if(inTable){ out+='</tbody></table></div>'; inTable=false; }
    let m;
    if(m=l.match(/^##\s+(.*)/)){ flush(); closeList(); out+='<h4>'+inline(m[1])+'</h4>'; continue; }
    if(m=l.match(/^>\s?(.*)/)){ flush(); closeList(); out+='<blockquote>'+inline(m[1])+'</blockquote>'; continue; }
    if(m=l.match(/^-\s+(.*)/)){
      flush(); if(listType&&listType!=='ul') closeList();
      if(!listType){ out+='<ul>'; listType='ul'; }
      out+='<li>'+inline(m[1])+'</li>'; continue; }
    if(m=l.match(/^\d+\.\s+(.*)/)){
      flush(); if(listType&&listType!=='ol') closeList();
      if(!listType){ out+='<ol>'; listType='ol'; }
      out+='<li>'+inline(m[1])+'</li>'; continue; }
    closeList(); para.push(l.trim());
  }
  flush(); closeList();
  if(inTable) out+='</tbody></table></div>';
  return out;
}

function paneLibrary(w){
  const [p,b]=panel('Contents', BOOT.library.reduce((n,s2)=>n+s2.items.length,0)+' articles');
  w.appendChild(p);
  const find=el('input'); find.type='text'; find.placeholder='search the handbook';
  b.appendChild(find);
  const toc=el('div'); toc.style.marginTop='8px'; b.appendChild(toc);
  const drawToc=filter=>{
    toc.innerHTML='';
    BOOT.library.forEach(sec=>{
      const items=sec.items.filter(i=>!filter ||
        (i.title+' '+i.summary).toLowerCase().includes(filter));
      if(!items.length) return;
      toc.appendChild(el('div','rail-head '+sec.stain, esc(sec.section)));
      items.forEach(i=>{
        const row=el('div','nav'+(STATE.entry===i.id?' on':''),
          `<span>${esc(i.title)}</span><span class="count">${esc(i.reading)}</span>`);
        row.onclick=()=>openEntry(i.id);
        toc.appendChild(row);
        if(!filter) toc.appendChild(el('div','help',esc(i.summary)))
          .style.padding='0 16px 7px 18px';
      });
    });
  };
  find.oninput=()=>drawToc(find.value.trim().toLowerCase());
  drawToc('');

  const holder=el('div'); holder.id='entry-holder'; w.appendChild(holder);
  if(STATE.entry) openEntry(STATE.entry, true);
  else{
    const [p2,b2]=panel('Where to begin'); holder.appendChild(p2);
    b2.innerHTML=md(
      'Two paths through this tool, and the handbook follows both.\n\n'+
      '- New to the program: read **How the pieces fit together**, then '+
      '**Your first analysis, end to end**\n'+
      '- Starting a review: read **A systematic review, start to finish**, '+
      'which names the pane that handles each step\n'+
      '- Stuck on a specific decision: the search box above matches article '+
      'text, not just titles\n\n'+
      '> Links inside an article are live. `Open the Data pane` moves you '+
      'there; a link to another article opens it here.');
  }
}

async function openEntry(id, keep){
  STATE.entry=id;
  const e=await api('/api/library/'+id);
  if(!keep) renderPane();
  const holder=$('#entry-holder'); if(!holder) return;
  holder.innerHTML='';
  const sec=BOOT.library.find(s2=>s2.items.some(i=>i.id===id));
  const [p,b]=panel(e.title, e.reading, sec?sec.stain:null);
  holder.appendChild(p);
  const art=el('div','article'); art.innerHTML=md(e.body); b.appendChild(art);
  art.querySelectorAll('.xlink').forEach(a=>{
    a.onclick=()=>{
      if(a.dataset.pane){ STATE.pane=a.dataset.pane; renderRail(); renderPane(); }
      else if(a.dataset.entry){ openEntry(a.dataset.entry); }
    };
  });
  if(e.panes && e.panes.length){
    const row=el('div','tool-row');
    e.panes.forEach(pn=>{
      const btn=el('button','','open '+pn);
      btn.onclick=()=>{ STATE.pane=pn; renderRail(); renderPane(); };
      row.appendChild(btn);
    });
    b.appendChild(row);
  }
  holder.scrollIntoView({behavior:'smooth', block:'start'});
}

// ── panes ─────────────────────────────────────────────────────────────
function paneHead(id, subtitle){
  const t=PANE_TIP[id]||[id,''];
  const h=el('div','view-head');
  const h1=el('h1',null,esc(t[0]));
  h1.appendChild(qmark(t[0], t[1]));
  h.appendChild(h1);
  if(subtitle) h.appendChild(el('p',null,esc(subtitle)));
  return h;
}

function renderPane(){
  const w=$('#work'); w.innerHTML='';
  hideTip();
  w.appendChild(paneHead(STATE.pane));
  ({data:paneData, stats:paneStats, figures:paneFigures, harvest:paneHarvest,
    screen:paneScreen, synthesis:paneSynthesis, report:paneReport, runs:paneRuns,
    library:paneLibrary, settings:paneSettings}[STATE.pane]||paneData)(w);
  renderInspector();
}

// Data ------------------------------------------------------------------
async function paneData(w){
  const [p,b]=panel('Datasets'); w.appendChild(p);
  const bar=el('div','inline');
  const inp=el('input'); inp.type='file'; inp.style.display='none';
  inp.onchange=async()=>{
    const fd=new FormData(); fd.append('file', inp.files[0]);
    const r=await fetch('/api/datasets/upload',{method:'POST',body:fd}).then(r=>r.json());
    if(r.error) return toast(r.error,'err');
    STATE.dataset=r.id; await loadDataset(); toast('Imported '+r.name,'ok');
  };
  const up=el('button','primary',' Import file'); up.onclick=()=>inp.click();
  const pathIn=el('input'); pathIn.type='text'; pathIn.placeholder='or a path on the server';
  pathIn.className='mono';
  const go=el('button',null,'Load path');
  go.onclick=async()=>{ const r=await api('/api/datasets/path',{method:'POST',
    body:JSON.stringify({path:pathIn.value})});
    if(r.error) return toast(r.error,'err');
    STATE.dataset=r.id; await loadDataset(); };
  bar.append(up,inp,pathIn,go); pathIn.classList.add('grow');
  b.appendChild(bar);

  const list=el('div'); list.style.marginTop='10px'; b.appendChild(list);
  const ds=await api('/api/datasets');
  if(!ds.length) list.appendChild(el('div','empty','No datasets yet.'));
  else{
    const t=el('table'); t.innerHTML='<tr><th>Name</th><th class="num">Rows</th>'+
      '<th class="num">Cols</th><th class="num">Runs</th><th>SHA</th><th></th></tr>';
    ds.forEach(d=>{
      const tr=el('tr',null,`<td>${esc(d.name)}</td><td class="num">${d.n_rows}</td>`+
        `<td class="num">${d.n_cols}</td><td class="num">${d.runs}</td>`+
        `<td class="mono" style="color:var(--faint);font-size:10px">${esc((d.sha256||'').slice(0,10))}</td>`+
        `<td></td>`);
      const btn=el('button','ghost', STATE.dataset===d.id?'active':'select');
      btn.onclick=async()=>{ STATE.dataset=d.id; await loadDataset(); };
      const del=el('button','ghost danger rowdel','remove');
      del.onclick=async(e)=>{
        e.stopPropagation();
        const alsoRuns=d.runs>0 && window.confirm(
          `${d.name} has ${d.runs} analyses in the ledger.\n\n`+
          'OK deletes those too. Cancel keeps the ledger entries and removes only the data.');
        if(!await confirmDestructive(`Remove ${d.name}?`,
            alsoRuns?`${d.runs} ledger entries go with it.`
                    :'The ledger entries for it are kept.')) return;
        const r=await api(`/api/datasets/${d.id}${alsoRuns?'?runs=1':''}`,{method:'DELETE'});
        if(STATE.dataset===d.id){ STATE.dataset=null; STATE.dsMeta=null; STATE.result=null;
          $('#ds-chip').textContent='no dataset'; }
        toast(`Removed ${d.name}`+(r.runs_deleted?`, ${r.runs_deleted} runs`:''),'ok');
        renderPane(); refreshChips();
      };
      tr.lastChild.append(btn,del); t.appendChild(tr);
    });
    list.appendChild(t);
  }

  if(!STATE.dsMeta) return;
  const [p2,b2]=panel('Variable dictionary',
    STATE.dsMeta.n_rows+' rows · '+STATE.dsMeta.n_cols+' columns'); w.appendChild(p2);
  b2.appendChild(el('div','hint','The inferred type drives which tests will accept a '+
    'variable. A 0/1 column read as continuous is the commonest silent error, so check '+
    'this before running anything.'));
  const wrap=el('div','tablewrap'); wrap.style.marginTop='8px';
  const t=el('table');
  t.innerHTML='<tr><th>Variable</th><th>Type</th><th class="num">n unique</th>'+
    '<th class="num">Missing</th><th>Summary</th></tr>';
  Object.entries(STATE.dsMeta.dictionary).forEach(([c,d])=>{
    const sel=el('select');
    ['continuous','ordinal','categorical','binary','time','id','text'].forEach(k=>{
      const o=el('option',null,k); o.value=k; if(d.kind===k)o.selected=true; sel.appendChild(o); });
    sel.onchange=async()=>{ STATE.dsMeta.dictionary[c].kind=sel.value;
      await api('/api/datasets/'+STATE.dataset+'/dictionary',
        {method:'POST',body:JSON.stringify(STATE.dsMeta.dictionary)}); renderPane(); };
    let summary='';
    if(d.summary) summary=`median ${num(d.summary.median,2)} (${num(d.summary.q1,2)}–${num(d.summary.q3,2)})`;
    else if(d.levels) summary=d.levels.slice(0,4).map(l=>`${esc(l[0])}: ${l[1]}`).join(', ');
    const tr=el('tr',null,`<td class="mono">${esc(c)}</td><td></td>`+
      `<td class="num">${d.n_unique}</td>`+
      `<td class="num" ${d.pct_missing>20?'style="color:var(--caution)"':''}>${d.pct_missing}%</td>`+
      `<td class="mono" style="font-size:10.5px;color:var(--dim)">${summary}</td>`);
    tr.children[1].appendChild(sel); t.appendChild(tr);
  });
  wrap.appendChild(t); b2.appendChild(wrap);

  const [p3,b3]=panel('Preview'); w.appendChild(p3); p3.classList.add('collapsed');
  const cols=Object.keys(STATE.dsMeta.dictionary);
  const pw=el('div','tablewrap'); const pt=el('table');
  pt.innerHTML='<tr>'+cols.map(c=>`<th>${esc(c)}</th>`).join('')+'</tr>';
  (STATE.dsMeta.preview||[]).slice(0,60).forEach(r=>{
    pt.appendChild(el('tr',null,'<tr>'+cols.map(c=>
      `<td class="mono" style="font-size:10.5px">${esc(r[c])}</td>`).join('')));
  });
  pw.appendChild(pt); b3.appendChild(pw);
}

async function loadDataset(){
  STATE.dsMeta=await api('/api/datasets/'+STATE.dataset);
  STATE.roles={}; STATE.result=null;
  $('#ds-chip').innerHTML='<b>'+esc(STATE.dsMeta.name)+'</b> '+STATE.dsMeta.n_rows+'\u00d7'+STATE.dsMeta.n_cols;
  renderPane(); refreshChips();
}

// Statistics ------------------------------------------------------------
function paneStats(w){
  if(!STATE.dataset && !['padjust','evalue','multiplicity_audit','power_ttest','power_prop',
      'power_anova','power_corr'].includes(STATE.test)){
    w.appendChild(el('div','note info','Import a dataset in the Data pane first. '+
      'The power and p-adjustment tools work without one.'));
  }
  const [p,b]=panel('Test library',
    BOOT.counts.tests_ready+' of '+BOOT.counts.tests_total+' implemented'); w.appendChild(p);
  const search=el('input'); search.type='text'; search.placeholder='filter tests';
  search.oninput=()=>{ $$('.nav',b).forEach(i=>{
    i.style.display=i.textContent.toLowerCase().includes(search.value.toLowerCase())?'':'none'; }); };
  b.appendChild(search);
  const holder=el('div'); holder.style.maxHeight='300px'; holder.style.overflowY='auto';
  holder.style.marginTop='6px'; b.appendChild(holder);
  BOOT.tests.groups.forEach(g=>{
    holder.appendChild(el('div','rail-head '+stainOf(g.group), esc(g.group)));
    g.items.forEach(it=>{
      const row=el('div','nav'+(STATE.test===it.id?' on':'')+
        (it.status==='stub'?' stub':''),
        `<span>${esc(it.label)}</span>`+(it.status==='stub'?'<span class="stub-flag">stub</span>':''));
      row.onclick=()=>{ selectTest(it.id); };
      holder.appendChild(row);
    });
  });

  if(!STATE.test) { w.appendChild(el('div','empty','Choose a test.')); return; }
  const entry=BOOT.tests.entries[STATE.test];
  const [p2,b2]=panel(entry.label, null, stainOf(entry.group)); w.appendChild(p2);
  if(entry.blurb) b2.appendChild(el('div','hint',esc(entry.blurb)));
  const form=el('div'); form.style.marginTop='8px'; b2.appendChild(form);
  formFor(entry, form);
  const gate=el('div'); gate.id='gate'; b2.appendChild(gate);
  const actions=el('div','inline'); actions.style.marginTop='9px';
  const run=el('button','primary','Run'); run.onclick=doRun;
  const pf=el('button',null,'Check assumptions'); pf.onclick=preflight;
  actions.append(run,pf);
  b2.appendChild(actions);
  if(entry.status==='stub')
    b2.appendChild(el('div','note','Declared but not implemented. Running it '+
      'will return the exact function signature to write.'));
  preflight();

  if(STATE.result) w.appendChild(renderResult(STATE.result));
}

function selectTest(id){
  STATE.test=id; STATE.result=null;
  const e=BOOT.tests.entries[id];
  STATE.params={}; (e.params||[]).forEach(p=>{ if(p.default!==undefined) STATE.params[p.id]=p.default; });
  renderPane();
}

async function preflight(){
  const g=$('#gate'); if(!g||!STATE.test) return;
  const r=await api('/api/preflight',{method:'POST',body:JSON.stringify(spec())});
  g.innerHTML='';
  if(r.errors&&r.errors.length)
    r.errors.forEach(e=>g.appendChild(el('div','note err',esc(e))));
  if(r.checks&&r.checks.length){
    const strip=el('div','gate');
    r.checks.forEach(c=>strip.appendChild(el('div','lozenge '+c.state,
      `<span class="dot"></span>${esc(c.label)}`)));
    g.appendChild(strip);
    r.checks.filter(c=>c.state!=='pass').forEach(c=>{
      const d=el('div','checkdetail '+c.state,
        `<b>${esc(c.label)}</b> — ${esc(c.detail)}`+
        (c.fix?`<span class="fix">→ ${esc(c.fix)}</span>`:''));
      g.appendChild(d);
    });
  }
  if(r.multiplicity_nag)
    g.appendChild(el('div','note',
      `${r.prior_runs} tests have already been run on this dataset. `+
      `At alpha ${BOOT.config.alpha} the chance of at least one false positive is now `+
      `${((1-Math.pow(1-BOOT.config.alpha,r.prior_runs))*100).toFixed(0)}%.`));
  if(r.code) STATE.code=r.code;
  renderInspector();
}

function spec(){
  return {test:STATE.test, dataset:STATE.dataset, roles:STATE.roles, params:STATE.params};
}

async function doRun(){
  const r=await api('/api/run',{method:'POST',body:JSON.stringify(spec())});
  if(r.job){ toast('Queued as a background job'); return; }
  if(r.ok===false){
    const w=$('#work');
    (r.errors||['Unknown error']).forEach(e=>{
      const n=el('div','note '+(r.not_implemented?'warn':'err'));
      n.innerHTML='<pre>'+esc(e)+'</pre>';
      w.appendChild(n);
    });
    if(r.fallback){
      const btn=el('button',null,'Switch to '+esc(BOOT.tests.entries[r.fallback].label));
      btn.onclick=()=>selectTest(r.fallback);
      w.appendChild(btn);
    }
    return;
  }
  STATE.result=r; refreshChips(); renderPane();
}

function renderResult(r){
  const [p,b]=panel('Result — '+(r.test||''), r.run_id||'');
  if(r.note) b.appendChild(el('div','note info',esc(r.note)));
  if(r.warning) b.appendChild(el('div','note',esc(r.warning)));
  if(r.caveat) b.appendChild(el('div','note info',esc(r.caveat)));

  const hero=el('div','hero');
  const add=(lab,val,sub,sig)=>{ hero.appendChild(el('div','item',
    `<div class="lab">${esc(lab)}</div><div class="val${sig?' sig':''}">${val}</div>`+
    (sub?`<div class="sub">${esc(sub)}</div>`:''))); };
  if(r.statistic!=null) add(r.df!=null?'statistic':'statistic', num(r.statistic,2),
    Array.isArray(r.df)?('df '+r.df.map(d=>num(d,1)).join(', ')):(r.df!=null?'df '+num(r.df,1):''));
  if(r.p!=null) add('p value', pval(r.p).replace('p ',''), starsFor(r.p), r.p<BOOT.config.alpha);
  if(r.auc!=null) add('AUC', num(r.auc,3), r.auc_ci?`${num(r.auc_ci[0],3)}–${num(r.auc_ci[1],3)}`:'');
  if(r.pooled!=null) add('pooled', num(r.pooled,2),
    `${num(r.pooled_ci[0],2)}–${num(r.pooled_ci[1],2)}`);
  if(r.heterogeneity) add('I²', num(r.heterogeneity.I2,0)+'%','τ² '+num(r.heterogeneity.tau2,3));
  if(r.effects) Object.entries(r.effects).forEach(([k,v])=>{
    if(typeof v==='number') add(k.replace(/_/g,' '), num(v,2)); });
  if(r.n_per_group) add('n per group', r.n_per_group, r.n_total?('total '+r.n_total):'');
  if(r.power!=null&&r.kind==='power') add('power', (r.power*100).toFixed(1)+'%');
  if(r.value!=null&&(r.kind==='icc'||r.kind==='kappa')) add(r.form||'kappa', num(r.value,3),
    r.interpretation||'');
  if(r.evalue_point!=null) add('E-value', num(r.evalue_point,2),
    r.evalue_ci?('CI limit '+num(r.evalue_ci,2)):'');
  if(hero.children.length) b.appendChild(hero);

  if(r.interpretation) b.appendChild(el('div','note ok',esc(r.interpretation)));

  // group summary table
  if(r.levels&&(r.mean||r.median)){
    const t=el('table');
    const hasMean=!!r.mean;
    t.innerHTML=`<tr><th>Group</th><th class="num">n</th>`+
      `<th class="num">${hasMean?'Mean':'Median'}</th>`+
      `<th class="num">${hasMean?'SD':'IQR'}</th></tr>`;
    r.levels.forEach((l,i)=>{
      const c=hasMean?r.mean[i]:(r.median||[])[i];
      const s=hasMean?(r.sd||[])[i]:((r.iqr||[])[i]?`${num(r.iqr[i][0],2)}–${num(r.iqr[i][1],2)}`:'');
      t.appendChild(el('tr',null,`<td>${esc(l)}</td><td class="num">${(r.n||[])[i]??''}</td>`+
        `<td class="num">${num(c,2)}</td><td class="num">${typeof s==='number'?num(s,2):esc(s)}</td>`));
    });
    b.appendChild(t);
  }

  if(r.comparisons&&r.comparisons.length>1){
    b.appendChild(el('div','rail-head eosin', esc(r.posthoc_label||'Comparisons')));
    const t=el('table');
    t.innerHTML='<tr><th>A</th><th>B</th><th class="num">Difference</th>'+
      '<th class="num">g</th><th class="num">p raw</th><th class="num">p adjusted</th><th></th></tr>';
    r.comparisons.forEach(c=>{
      t.appendChild(el('tr',null,`<td>${esc(c.a)}</td><td>${esc(c.b)}</td>`+
        `<td class="num">${num(c.mean_diff,2)}</td><td class="num">${num(c.hedges_g,2)}</td>`+
        `<td class="num">${num(c.p_raw,4)}</td>`+
        `<td class="num${c.p<BOOT.config.alpha?' sig':''}">${num(c.p,4)}</td>`+
        `<td class="sig">${starsFor(c.p)}</td>`));
    });
    b.appendChild(t);
  }

  if(r.coefficients){
    const t=el('table');
    t.innerHTML=`<tr><th>Term</th><th class="num">${esc(r.measure||'Estimate')}</th>`+
      '<th class="num">CI</th><th class="num">p</th><th></th></tr>';
    r.coefficients.forEach(c=>t.appendChild(el('tr',null,
      `<td class="mono">${esc(c.term)}</td><td class="num">${num(c.estimate,3)}</td>`+
      `<td class="num">${num(c.ci[0],3)} – ${num(c.ci[1],3)}</td>`+
      `<td class="num${c.p<BOOT.config.alpha?' sig':''}">${num(c.p,4)}</td>`+
      `<td class="sig">${starsFor(c.p)}</td>`)));
    b.appendChild(t);
  }

  if(r.kind==='table1') b.appendChild(renderTable1(r));
  if(r.kind==='meta') b.appendChild(renderMeta(r));
  if(r.rows&&['table','padjust','meta_sensitivity'].includes(r.kind))
    b.appendChild(renderGenericRows(r));
  if(r.metrics){
    const t=el('table'); t.innerHTML='<tr><th>Measure</th><th class="num">Value</th><th class="num">CI</th></tr>';
    r.metrics.forEach(m=>t.appendChild(el('tr',null,`<td>${esc(m.name)}</td>`+
      `<td class="num">${num(m.value,3)}</td>`+
      `<td class="num">${m.ci?num(m.ci[0],3)+' – '+num(m.ci[1],3):'—'}</td>`)));
    b.appendChild(t);
  }
  if(r.blocks&&r.kind==='audit'){
    const t=el('table'); t.innerHTML='<tr><th>Dataset</th><th class="num">Runs</th>'+
      '<th class="num">FWER</th><th class="num">Bonferroni alpha</th></tr>';
    r.blocks.forEach(bl=>t.appendChild(el('tr',null,`<td>${esc(bl.dataset)}</td>`+
      `<td class="num">${bl.n_runs}</td>`+
      `<td class="num${bl.fwer>0.3?' sig':''}">${(bl.fwer*100).toFixed(1)}%</td>`+
      `<td class="num">${bl.bonferroni_alpha??'—'}</td>`)));
    b.appendChild(t);
  }

  const sentence=el('div','readout', esc(r.sentence||''));
  if(r.sentence){
    b.appendChild(el('div','rail-head eosin','Reportable sentence'));
    sentence.onclick=()=>{navigator.clipboard.writeText(r.sentence); toast('Copied','ok');};
    b.appendChild(sentence);
  }
  api('/api/report/sentence',{method:'POST',body:JSON.stringify({result:r})})
    .then(x=>{ if(x.text&&x.text!==r.sentence){
      const s2=el('div','readout',esc(x.text)); s2.style.marginTop='6px';
      s2.onclick=()=>{navigator.clipboard.writeText(x.text); toast('Copied','ok');};
      b.appendChild(s2); }});
  return p;
}

function renderTable1(r){
  const wrap=el('div','tablewrap');
  const t=el('table');
  t.innerHTML='<tr><th>Characteristic</th>'+r.header.map(h=>
    `<th class="num">${esc(h)}<br><span style="font-weight:400;text-transform:none">n = ${r.n[h]}</span></th>`).join('')+
    '<th class="num">p</th><th class="num">SMD</th></tr>';
  r.rows.forEach(row=>{
    const cells=r.header.map(h=>`<td class="num">${esc(row.cells[h]||'')}</td>`).join('');
    t.appendChild(el('tr',null,`<td>${esc(row.variable)} <span style="color:var(--faint);font-size:10px">${esc(row.summary)}</span></td>`+
      cells+`<td class="num${row.p<BOOT.config.alpha?' sig':''}">${row.p!=null?num(row.p,3):''}</td>`+
      `<td class="num">${row.smd!=null?num(row.smd,2):''}</td>`));
    (row.sub_rows||[]).forEach(sr=>{
      t.appendChild(el('tr',null,`<td class="subrow">${esc(sr.level)}</td>`+
        r.header.map(h=>`<td class="num">${esc(sr.cells[h]||'')}</td>`).join('')+
        '<td></td><td></td>'));
    });
  });
  wrap.appendChild(t);
  const box=el('div'); box.appendChild(wrap);
  box.appendChild(el('div','hint',esc(r.footnote||'')));
  return box;
}

function renderMeta(r){
  const wrap=el('div','tablewrap'); const t=el('table');
  t.innerHTML='<tr><th>Study</th><th class="num">Effect</th><th class="num">CI</th>'+
    '<th class="num">Weight</th></tr>';
  r.studies.forEach(s=>t.appendChild(el('tr',null,`<td>${esc(s.label)}</td>`+
    `<td class="num">${num(s.effect,2)}</td>`+
    `<td class="num">${num(s.ci[0],2)} – ${num(s.ci[1],2)}</td>`+
    `<td class="num">${num(s.weight,1)}%</td>`)));
  t.appendChild(el('tr',null,`<td><b>Pooled (${esc(r.model)})</b></td>`+
    `<td class="num sig">${num(r.pooled,2)}</td>`+
    `<td class="num">${num(r.pooled_ci[0],2)} – ${num(r.pooled_ci[1],2)}</td><td></td>`));
  if(r.prediction_interval) t.appendChild(el('tr',null,'<td>Prediction interval</td><td></td>'+
    `<td class="num">${num(r.prediction_interval[0],2)} – ${num(r.prediction_interval[1],2)}</td><td></td>`));
  wrap.appendChild(t); return wrap;
}

function renderGenericRows(r){
  const rows=r.rows||[]; if(!rows.length) return el('div','empty','No rows.');
  const keys=Object.keys(rows[0]).filter(k=>!k.startsWith('_'));
  const wrap=el('div','tablewrap'); const t=el('table');
  t.innerHTML='<tr>'+keys.map(k=>`<th class="num">${esc(k.replace(/_/g,' '))}</th>`).join('')+'</tr>';
  rows.forEach(row=>t.appendChild(el('tr',null, keys.map(k=>{
    const v=row[k];
    return `<td class="num">${typeof v==='number'?num(v,3):esc(Array.isArray(v)?v.join(', '):v)}</td>`;
  }).join(''))));
  wrap.appendChild(t); return wrap;
}

// Figures ---------------------------------------------------------------
function paneFigures(w){
  if(!STATE.result){ w.appendChild(el('div','empty','Run a test first. '+
    'Figures are built from a result, so the annotation always matches the statistics.')); return; }
  const kind=STATE.result.kind;
  const avail=Object.values(BOOT.plots.entries).filter(p=>p.kinds.includes(kind));
  const [p,b]=panel('Figures for a '+kind+' result', avail.length+' available'); w.appendChild(p);
  const strip=el('div','chips');
  avail.forEach(pl=>{ const o=el('div','chip'+(STATE.plot===pl.id?' on':''),
    esc(pl.label)+(pl.status==='stub'?' ·':''));
    o.onclick=()=>{ STATE.plot=pl.id; STATE.plotParams={};
      (pl.params||[]).concat(BOOT.plots.common).forEach(q=>{
        if(q.default!==undefined) STATE.plotParams[q.id]=q.default; });
      renderPane(); }; strip.appendChild(o); });
  b.appendChild(strip);
  if(!STATE.plot) return;
  const entry=BOOT.plots.entries[STATE.plot];
  const [p2,b2]=panel(entry.label, null, stainOf(entry.group)); w.appendChild(p2);
  if(entry.blurb) b2.appendChild(el('div','hint',esc(entry.blurb)));
  const grid=el('div','cols');
  const left=el('div'), right=el('div');
  grid.append(left,right); b2.appendChild(grid);
  (entry.params||[]).forEach(q=>left.appendChild(
    field(q, STATE.plotParams[q.id], (k,v)=>{STATE.plotParams[k]=v;})));
  right.appendChild(el('div','rail-head fastgreen','Output'));
  BOOT.plots.common.forEach(q=>right.appendChild(
    field(q, STATE.plotParams[q.id], (k,v)=>{STATE.plotParams[k]=v;})));
  const draw=el('button','primary','Draw'); draw.style.marginTop='8px';
  const out=el('div'); out.style.marginTop='10px';
  draw.onclick=async()=>{
    out.innerHTML='';
    const r=await api('/api/plot',{method:'POST',body:JSON.stringify({
      plot:STATE.plot, run_id:STATE.result.run_id, result:STATE.result,
      spec:spec(), params:STATE.plotParams})});
    if(r.error){ out.appendChild(el('div','note '+(r.not_implemented?'warn':'err'),
      '<pre>'+esc(r.error)+'</pre>')); return; }
    const box=el('div','figbox');
    const img=el('img'); img.src=r.url+'&t='+Date.now(); box.appendChild(img);
    out.appendChild(box);
    const dl=el('a','btn','Download '+esc(r.name));
    dl.href='/api/download?path='+encodeURIComponent(r.path); dl.style.marginTop='8px';
    out.appendChild(dl);
  };
  b2.append(draw,out);
}

// Harvest ---------------------------------------------------------------
function paneHarvest(w){
  const [p,b]=panel('Sources', BOOT.counts.sources_total+' declared'); w.appendChild(p);
  const holder=el('div'); holder.style.maxHeight='240px'; holder.style.overflowY='auto';
  BOOT.sources.groups.forEach(g=>{
    holder.appendChild(el('div','rail-head '+stainOf(g.group), esc(g.group)));
    g.items.forEach(it=>{
      const row=el('div','nav'+(STATE.source===it.id?' on':'')+
        (it.status==='stub'?' stub':''),
        `<span>${esc(it.label)}</span>`+(it.status==='stub'?'<span class="stub-flag">stub</span>':''));
      row.onclick=()=>{ STATE.source=it.id; STATE.params={};
        const e=BOOT.sources.entries[it.id];
        (e.params||[]).forEach(q=>{ if(q.default!==undefined) STATE.params[q.id]=q.default; });
        renderPane(); };
      holder.appendChild(row);
    });
  });
  b.appendChild(holder);

  const e=BOOT.sources.entries[STATE.source]; if(!e) return;
  const [p2,b2]=panel(e.label, e.base, stainOf(e.group)); w.appendChild(p2);
  if(e.blurb) b2.appendChild(el('div','hint',esc(e.blurb)));
  const form=el('div'); form.style.marginTop='8px'; b2.appendChild(form);
  (e.params||[]).forEach(q=>form.appendChild(
    field(q, STATE.params[q.id], (k,v)=>{STATE.params[k]=v;})));
  const go=el('button','primary','Search');
  go.onclick=async()=>{
    const r=await api('/api/harvest',{method:'POST',
      body:JSON.stringify({source:STATE.source, params:STATE.params})});
    toast(r.job?'Search running':'Failed', r.job?'':'err');
  };
  b2.appendChild(go);
  if(e.docs) b2.appendChild(el('div','hint','Docs: '+esc(e.docs)));

  const [p3,b3]=panel('Corpus'); w.appendChild(p3);
  const bar=el('div','inline');
  const dd=el('button',null,'Deduplicate');
  dd.onclick=async()=>{ await api('/api/dedup',{method:'POST',body:'{}'});
    toast('Deduplicating'); };
  const rt=el('button',null,'Check retractions');
  rt.onclick=async()=>{ await api('/api/harvest',{method:'POST',
    body:JSON.stringify({source:'retraction',params:{scope:'corpus'}})}); toast('Checking'); };
  const oa=el('button',null,'Resolve open access');
  oa.onclick=async()=>{ await api('/api/harvest',{method:'POST',
    body:JSON.stringify({source:'unpaywall',params:{from_corpus:true}})}); toast('Resolving'); };
  bar.append(dd,rt,oa); b3.appendChild(bar);
  const list=el('div'); list.style.marginTop='9px'; b3.appendChild(list);
  const drawList=()=>api('/api/records').then(recs=>{
    list.innerHTML='';
    if(!recs.length){ list.appendChild(el('div','empty','Corpus is empty.')); return; }
    list.appendChild(el('div','hint',recs.length+' records shown.'));
    recs.slice(0,80).forEach(r=>{
      const act=el('div','inline'); act.style.marginTop='7px';
      const rm=el('button','ghost danger rowdel','remove');
      rm.onclick=async()=>{
        if(!await confirmDestructive('Remove this record?',
            'Any screening decision, extraction or risk-of-bias judgement on it goes too.')) return;
        await api('/api/records/'+r.id,{method:'DELETE'});
        drawList(); toast('Record removed','ok');
      };
      act.appendChild(rm);
      list.appendChild(recordCard(r, act));
    });
  });
  drawList();

  // ── trim ────────────────────────────────────────────────────────────
  const [p4,b4]=panel('Trim the corpus', null, null,
    'Narrowing a search after it has run is normal. Doing it blind is not, so every '+
    'filter here counts what it would remove and shows a sample before anything goes. '+
    'Deleting a record also deletes any screening decision, extraction or risk-of-bias '+
    'judgement attached to it.');
  w.appendChild(p4);
  const F={};
  const grid=el('div','cols');
  const left=el('div'), right=el('div'); grid.append(left,right);
  [
    {id:'query',label:'Keep only records matching',type:'text',
     placeholder:'olfactory ensheathing',
     help:'Records that do NOT contain this in the title or abstract are removed.'},
    {id:'not_query',label:'Remove records matching',type:'text',placeholder:'rat OR murine'},
    {id:'source',label:'Only from source',type:'select',
     choices:[['','any']].concat((BOOT.sources.groups||[]).flatMap(g=>g.items.map(i=>[i.id,i.label])))},
    {id:'year_before',label:'Published before',type:'int',placeholder:'2010'},
  ].forEach(q=>left.appendChild(field(q, F[q.id], (k,v)=>{F[k]=v;})));
  [
    {id:'retracted',label:'Retracted or flagged',type:'bool'},
    {id:'duplicates',label:'Duplicates',type:'bool'},
    {id:'no_abstract',label:'No abstract',type:'bool'},
    {id:'unscreened',label:'Never screened',type:'bool'},
    {id:'excluded',label:'Already excluded',type:'bool'},
  ].forEach(q=>right.appendChild(field(q, F[q.id], (k,v)=>{F[k]=v;})));
  b4.appendChild(grid);

  const out=el('div'); out.style.marginTop='9px';
  const prev=el('button','','preview');
  const kill=el('button','danger','delete matched'); kill.disabled=true;
  let matched=0;
  prev.onclick=async()=>{
    const spec=Object.fromEntries(Object.entries(F).filter(([,v])=>v!==null&&v!==''&&v!==false));
    // A filter that matches everything is almost never what was meant, so it
    // is called out rather than quietly armed.
    const r=await api('/api/records/preview',{method:'POST',body:JSON.stringify(spec)});
    matched=r.matched;
    out.innerHTML='';
    const cls=(!Object.keys(spec).length||r.matched===r.total)?'note':'note info';
    out.appendChild(el('div',cls,
      (!Object.keys(spec).length||r.matched===r.total)
        ? `This matches all ${r.total} records, which would empty the corpus. Add a filter first.`
        : `${r.matched} of ${r.total} records match. ${r.remaining} would remain.`));
    if(r.sample.length){
      const t=el('table');
      t.innerHTML='<tr><th>Would remove</th><th class="num">Year</th><th>Source</th></tr>';
      r.sample.forEach(x=>t.appendChild(el('tr',null,
        `<td>${esc((x.title||'').slice(0,90))}</td><td class="num">${x.year||''}</td>`+
        `<td class="mono">${esc(x.source)}</td>`)));
      const wr=el('div','tablewrap'); wr.appendChild(t); out.appendChild(wr);
    }
    kill.disabled = r.matched===0;
  };
  kill.onclick=async()=>{
    const spec=Object.fromEntries(Object.entries(F).filter(([,v])=>v!==null&&v!==''&&v!==false));
    if(!Object.keys(spec).length) return toast('Set at least one filter first.','err');
    if(!await confirmDestructive(`Delete ${matched} records?`,
        'Screening decisions and extractions on them go too.')) return;
    const r=await api('/api/records/delete',{method:'POST',body:JSON.stringify(spec)});
    toast(`${r.deleted} records removed`,'ok');
    kill.disabled=true; out.innerHTML=''; drawList();
  };
  const row=el('div','inline'); row.append(prev,kill);
  b4.append(row,out);
}

function recordCard(r, actions){
  const c=el('div','record'+(r.retracted?' retracted':''));
  c.appendChild(el('h4',null,esc(r.title||'(no title)')));
  c.appendChild(el('div','meta',
    `${esc((r.authors||'').split(';').slice(0,3).join('; '))}${(r.authors||'').split(';').length>3?' et al':''}`+
    ` · ${esc(r.journal||'')} · ${r.year||''}`));
  const tags=el('div');
  tags.innerHTML=`<span class="tagline">${esc(r.source)}</span>`+
    (r.doi?`<span class="tagline">${esc(r.doi)}</span>`:'')+
    (r.oa_url?'<span class="tagline oa">open access</span>':'')+
    (r.retracted==1?'<span class="tagline ret">retracted</span>':'')+
    (r.retracted==2?'<span class="tagline ret">expression of concern</span>':'');
  c.appendChild(tags);
  if(r.abstract) c.appendChild(el('div','abs',esc(r.abstract)));
  if(actions) c.appendChild(actions);
  return c;
}

// Screening -------------------------------------------------------------
function paneScreen(w){
  const [pr,br]=panel('Reviewers', null, null,
    'A reviewer is a stored identity, not a name typed into a box each visit, so '+
    'decisions attach to a stable id and a typo cannot silently create a third '+
    'person. Screening the same records twice under different reviewers is what '+
    'produces a kappa, and blind mode is what makes the second pass independent '+
    'rather than a repeat.');
  w.appendChild(pr);
  const revBar=el('div','chips'); br.appendChild(revBar);
  const revExtra=el('div','inline'); revExtra.style.marginTop='9px'; br.appendChild(revExtra);

  const drawReviewers=async()=>{
    const revs=await api('/api/reviewers');
    STATE.reviewers=revs;
    if(!STATE.reviewer || !revs.some(r=>r.id===STATE.reviewer))
      STATE.reviewer=revs[0] && revs[0].id;
    revBar.innerHTML='';
    revs.forEach(r=>{
      const on=STATE.reviewer===r.id;
      const c=el('div','chip'+(on?' on':''),
        `<span class="tool-tag ${r.colour}" style="border:0;background:none;padding:0;margin-right:6px">`+
        `${esc(r.initials)}</span>${esc(r.name)}`+
        `<span style="opacity:.6;margin-left:7px">${r.decisions}</span>`);
      c.onclick=()=>{ STATE.reviewer=r.id; drawReviewers(); loadQueue(); };
      c.ondblclick=async()=>{
        const name=window.prompt('Rename reviewer', r.name);
        if(name){ await api('/api/reviewers',{method:'POST',
          body:JSON.stringify({id:r.id, name})}); drawReviewers(); }
      };
      revBar.appendChild(c);
    });
    const add=el('div','chip','+ add');
    add.onclick=async()=>{
      const name=window.prompt('Reviewer name');
      if(!name) return;
      await api('/api/reviewers',{method:'POST',body:JSON.stringify({name})});
      drawReviewers();
    };
    revBar.appendChild(add);

    revExtra.innerHTML='';
    const cur=revs.find(r=>r.id===STATE.reviewer);
    if(cur){
      revExtra.appendChild(el('div','hint',
        `${esc(cur.name)} has judged ${cur.title_abstract} at title and abstract `+
        `and ${cur.full_text} at full text. Double-click a name to rename.`));
      if(revs.length>1){
        const rm=el('button','ghost danger','remove '+esc(cur.name));
        rm.onclick=async()=>{
          if(!await confirmDestructive(`Remove ${cur.name}?`,
              `Their ${cur.decisions} decisions are kept, so the counts stay intact.`)) return;
          await api('/api/reviewers/'+cur.id,{method:'DELETE'});
          STATE.reviewer=null; drawReviewers(); loadQueue();
        };
        revExtra.appendChild(rm);
      }
    }
  };

  const [p,b]=panel('Screening'); w.appendChild(p);
  const bar=el('div','inline');
  const st=el('select');
  [['title_abstract','Title and abstract'],['full_text','Full text']].forEach(o=>{
    const x=el('option',null,o[1]); x.value=o[0]; if(STATE.stage===o[0])x.selected=true;
    st.appendChild(x); });
  st.onchange=()=>{ STATE.stage=st.value; loadQueue(); };
  const blindWrap=el('label','check');
  const blind=el('input'); blind.type='checkbox'; blind.checked=STATE.blind!==false;
  blind.onchange=()=>{ STATE.blind=blind.checked; loadQueue(); };
  blindWrap.append(blind, el('span',null,'blind'));
  blindWrap.appendChild(qmark('Blind mode',
    'Hides what the other reviewers decided about a record. Screening twice is only '+
    'worth the effort if the second pass is independent, so this is on by default. '+
    'Turn it off when you are deliberately checking someone else rather than '+
    'duplicating them.'));
  const undo=el('button','','undo last'); undo.onclick=doUndo;
  const reset=el('button','danger','reset this stage');
  reset.onclick=async()=>{
    if(!await confirmDestructive('Clear every decision at this stage?',
        'The records themselves are kept, so you can screen them again from scratch.')) return;
    const r=await api('/api/screen/reset',{method:'POST',body:JSON.stringify(
      {scope:'stage', stage:STATE.stage, reviewer:STATE.reviewer})});
    toast(`${r.deleted} decisions cleared`,'ok'); loadQueue();
  };
  bar.append(st,blindWrap,undo,reset); b.appendChild(bar);
  b.appendChild(el('div','hint','Keys: <kbd>i</kbd> include, '+
    '<kbd>e</kbd> exclude, <kbd>m</kbd> maybe, '+
    '<kbd>u</kbd> undo, <kbd>s</kbd> skip.'));
  const area=el('div'); area.id='screen-area'; area.style.marginTop='9px'; b.appendChild(area);

  drawReviewers().then(loadQueue);

  // ── agreement and conflicts ─────────────────────────────────────────
  const [p2,b2]=panel('Agreement and conflicts', null, null,
    'Percentage agreement always looks good and means little: two reviewers who '+
    'exclude 95% of records agree 90% of the time by chance alone. Kappa corrects '+
    'for that. Below about 0.6 the usual cause is ambiguous inclusion criteria, not '+
    'a careless reviewer, so re-read the criteria together before re-screening.');
  w.appendChild(p2);
  api('/api/screen/agreement?stage='+STATE.stage).then(a=>{
    if(a.note && a.kappa==null) b2.appendChild(el('div','note info',esc(a.note)));
    if(a.kappa!=null){
      b2.appendChild(el('div','hint',
        `${esc(a.pair[0])} against ${esc(a.pair[1])}, ${a.n_overlap} records judged by both.`));
      const hero=el('div','hero');
      const item=(lab,val,sub,sig)=>`<div class="item"><div class="lab">${lab}</div>`+
        `<div class="val${sig?' sig':''}">${val}</div>`+
        (sub?`<div class="sub">${esc(sub)}</div>`:'')+`</div>`;
      hero.innerHTML=item('kappa',num(a.kappa,3),a.interpretation,a.kappa<0.6)+
        item('agreement',a.percent_agreement+'%','chance-inflated')+
        item('conflicts',(a.conflicts||[]).length,
             a.n_unresolved?`${a.n_unresolved} unresolved`:'all resolved',a.n_unresolved>0);
      b2.appendChild(hero);
    }
    (a.conflicts||[]).forEach(cf=>{
      const card=el('div','record');
      card.innerHTML=`<h4>${esc(cf.title||'')}</h4>`+
        `<div class="meta">${esc((cf.authors||'').split(';')[0])} · ${cf.year||''}</div>`+
        `<div><span class="tag haem">${esc(a.pair[0])}: ${esc(cf.d1)}</span>`+
        `<span class="tag eosin">${esc(a.pair[1])}: ${esc(cf.d2)}</span>`+
        (cf.resolved?`<span class="tag fastgreen">resolved: ${esc(cf.resolved)}</span>`:'')+
        `</div>`;
      if(!cf.resolved){
        const row=el('div','inline'); row.style.marginTop='8px';
        ['include','exclude'].forEach(d=>{
          const btn=el('button',d==='include'?'primary':'danger','resolve as '+d);
          btn.onclick=async()=>{
            const why=window.prompt('Rationale for the adjudicated decision (optional)','')||'';
            await api('/api/screen/resolve',{method:'POST',body:JSON.stringify(
              {record_id:cf.record_id, stage:STATE.stage, decision:d, rationale:why,
               by:STATE.reviewer})});
            toast('Resolved as '+d,'ok'); renderPane();
          };
          row.appendChild(btn);
        });
        card.appendChild(row);
      }
      b2.appendChild(card);
    });
  });

  // ── PRISMA ──────────────────────────────────────────────────────────
  const [p3,b3]=panel('PRISMA', null, null,
    'Every number is counted from the screening database rather than typed in, so '+
    'the diagram in the manuscript cannot drift out of step with what actually '+
    'happened. Adjudicated decisions override the individual votes.');
  w.appendChild(p3);
  api('/api/screen/prisma').then(pr=>{
    const t=el('table');
    Object.entries(pr.counts).forEach(([k,v])=>t.appendChild(el('tr',null,
      `<td>${esc(k.replace(/_/g,' '))}</td><td class="num">${v}</td>`)));
    b3.appendChild(t);
    if(pr.exclusion_reasons&&pr.exclusion_reasons.length){
      b3.appendChild(el('div','rail-head','Exclusion reasons at full text'));
      const t2=el('table');
      pr.exclusion_reasons.forEach(r=>t2.appendChild(el('tr',null,
        `<td>${esc(r.reason)}</td><td class="num">${r.n}</td>`)));
      b3.appendChild(t2);
    }
    const draw=el('button','','draw the diagram');
    draw.onclick=async()=>{
      const r=await api('/api/plot',{method:'POST',body:JSON.stringify(
        {plot:'prisma', result:pr, params:{}})});
      if(r.error) return toast(r.error,'err');
      const box=el('div','figbox'); const img=el('img'); img.src=r.url+'&t='+Date.now();
      box.appendChild(img); b3.appendChild(box);
    };
    b3.appendChild(draw);
  });
}

async function loadQueue(){
  if(!STATE.reviewer) return;
  const q=await api(`/api/screen/queue?stage=${STATE.stage}`+
    `&reviewer=${encodeURIComponent(STATE.reviewer)}&blind=${STATE.blind===false?0:1}`);
  STATE.queue=q.records; STATE.qi=0; STATE.reasons=q.reasons;
  const area=$('#screen-area'); if(!area) return;
  area.innerHTML='';
  area.appendChild(el('div','hint',`${q.done} judged, ${q.remaining} remaining of ${q.total}.`));
  showCurrent();
}

function showCurrent(){
  const area=$('#screen-area'); if(!area) return;
  $$('.record',area).forEach(n=>n.remove());
  $$('.note',area).forEach(n=>n.remove());
  const r=STATE.queue[STATE.qi];
  if(!r){ area.appendChild(el('div','note ok','Queue empty for this stage.')); return; }
  const actions=el('div','inline'); actions.style.marginTop='8px';
  [['include','i','primary'],['exclude','e','danger'],['maybe','m','']].forEach(([d,k,cls])=>{
    const btn=el('button',cls,`${d} `);
    btn.appendChild(el('kbd',null,k));
    btn.onclick=()=>judge(d); actions.appendChild(btn);
  });
  const skip=el('button','ghost','skip '); skip.appendChild(el('kbd',null,'s'));
  skip.onclick=()=>{ STATE.qi++; showCurrent(); };
  actions.appendChild(skip);
  const sel=el('select'); sel.appendChild(el('option',null,'reason (for exclusions)'));
  (STATE.reasons||[]).forEach(x=>{const o=el('option',null,x); o.value=x; sel.appendChild(o);});
  sel.onchange=()=>{ STATE.reason=sel.value; };
  actions.appendChild(sel);
  const card=recordCard(r, actions);
  // Outside blind mode, what the others said rides along with the record.
  if(r.others && r.others.length){
    const strip=el('div'); strip.style.marginTop='6px';
    r.others.forEach(o=>strip.appendChild(
      el('span','tag '+(o.colour||'silver'), esc(o.initials+': '+o.decision))));
    card.insertBefore(strip, card.querySelector('.abs')||null);
  }
  area.appendChild(card);
}

// Synthesis -------------------------------------------------------------
function paneSynthesis(w){
  const [p,b]=panel('Extraction'); w.appendChild(p);
  const sel=el('select');
  Object.entries(BOOT.forms).forEach(([k,v])=>{ const o=el('option',null,v.label); o.value=k;
    if(STATE.form===k)o.selected=true; sel.appendChild(o); });
  sel.onchange=()=>{ STATE.form=sel.value; renderPane(); };
  b.appendChild(sel);
  const tbl=el('div'); tbl.style.marginTop='9px'; b.appendChild(tbl);
  api('/api/extraction?form='+STATE.form).then(x=>{
    if(!x.rows.length){ tbl.appendChild(el('div','empty',
      'No extractions yet. Screen studies to full-text inclusion first, then extract.')); return; }
    const wrap=el('div','tablewrap'); const t=el('table');
    t.innerHTML='<tr><th>Study</th>'+x.fields.map(f=>`<th class="num">${esc(x.labels[f])}</th>`).join('')+'</tr>';
    x.rows.forEach(r=>t.appendChild(el('tr',null,`<td>${esc(r._study)}</td>`+
      x.fields.map(f=>`<td class="num">${esc(r[f]??'')}</td>`).join(''))));
    wrap.appendChild(t); tbl.appendChild(wrap);
  });

  const [p2,b2]=panel('Risk of bias'); w.appendChild(p2);
  const isel=el('select');
  Object.entries(BOOT.instruments).forEach(([k,v])=>{ const o=el('option',null,v.label); o.value=k;
    if(STATE.instrument===k)o.selected=true; isel.appendChild(o); });
  isel.onchange=()=>{ STATE.instrument=isel.value; renderPane(); };
  b2.appendChild(isel);
  const inst=BOOT.instruments[STATE.instrument];
  b2.appendChild(el('div','hint',esc(inst.rule)));
  const rb=el('div'); rb.style.marginTop='8px'; b2.appendChild(rb);
  api('/api/rob?instrument='+STATE.instrument).then(x=>{
    if(!x.rows.length){ rb.appendChild(el('div','empty','No judgements recorded.')); return; }
    const t=el('table');
    t.innerHTML='<tr><th>Study</th>'+x.domains.map(d=>`<th>${esc(d)}</th>`).join('')+'<th>Overall</th></tr>';
    x.rows.forEach(r=>t.appendChild(el('tr',null,`<td>${esc(r.study)}</td>`+
      x.domains.map(d=>`<td>${esc(r.judgements[d]||'—')}</td>`).join('')+
      `<td>${esc(r.overall||'')}</td>`)));
    rb.appendChild(t);
    const draw=el('button',null,'Traffic light plot');
    draw.onclick=async()=>{ const g=await api('/api/plot',{method:'POST',
      body:JSON.stringify({plot:'rob_traffic',result:x,params:{}})});
      if(g.error) return toast(g.error,'err');
      const box=el('div','figbox'); const img=el('img'); img.src=g.url+'&t='+Date.now();
      box.appendChild(img); rb.appendChild(box); };
    rb.appendChild(draw);
  });

  const [p3,b3]=panel('To meta-analysis'); w.appendChild(p3);
  b3.appendChild(el('div','hint','Converts extracted arm-level data into effect sizes '+
    'and standard errors, on the log scale for ratio measures.'));
  const msel=el('select');
  ['SMD','MD','OR','RR'].forEach(m=>{const o=el('option',null,m); o.value=m; msel.appendChild(o);});
  const conv=el('button',null,'Convert');
  const outp=el('div'); outp.style.marginTop='8px';
  conv.onclick=async()=>{
    const x=await api(`/api/extraction/meta?form=${STATE.form}&measure=${msel.value}`);
    outp.innerHTML='';
    outp.appendChild(el('div','note info',`${x.k} studies convertible. ${esc(x.note)}`));
    if(x.rows.length){
      const t=el('table'); t.innerHTML='<tr><th>Study</th><th class="num">Effect</th><th class="num">SE</th></tr>';
      x.rows.forEach(r=>t.appendChild(el('tr',null,`<td>${esc(r.study)}</td>`+
        `<td class="num">${num(r.effect,3)}</td><td class="num">${num(r.se,3)}</td>`)));
      outp.appendChild(t);
    }
  };
  b3.append(el('div','inline'), outp);
  b3.firstChild.append(msel,conv);
}

// Report ----------------------------------------------------------------
function paneReport(w){
  const [p,b]=panel('Methods paragraph'); w.appendChild(p);
  const gen=el('button','primary','Generate from the run ledger');
  const out=el('div'); out.style.marginTop='8px';
  gen.onclick=async()=>{ const m=await api('/api/report/methods');
    out.innerHTML='';
    const s=el('div','readout',esc(m.text));
    s.onclick=()=>{navigator.clipboard.writeText(m.text); toast('Copied','ok');};
    out.append(s, el('div','hint',esc(m.note||'')));
  };
  b.append(gen,out);

  const [p2,b2]=panel('Reporting checklist'); w.appendChild(p2);
  const sel=el('select');
  Object.entries(BOOT.checklists).forEach(([k,v])=>{const o=el('option',null,v); o.value=k; sel.appendChild(o);});
  const load=el('button',null,'Load');
  const cl=el('div'); cl.style.marginTop='8px';
  load.onclick=async()=>{ const c=await api('/api/report/checklist/'+sel.value);
    cl.innerHTML=''; cl.appendChild(el('div','rail-head',esc(c.label)));
    c.items.forEach(i=>{ const w2=el('label','check');
      const cb=el('input'); cb.type='checkbox';
      w2.append(cb, el('span',null,i.n+'. '+esc(i.text))); cl.appendChild(w2); }); };
  const row=el('div','inline'); row.append(sel,load); b2.append(row,cl);

  const [p3,b3]=panel('Pre-registration draft'); w.appendChild(p3);
  b3.appendChild(el('div','hint','Worth more than any correction applied afterwards.'));
  const q=el('input'); q.type='text'; q.placeholder='Research question (PICO)';
  const mk=el('button',null,'Draft');
  const po=el('div'); po.style.marginTop='8px';
  mk.onclick=async()=>{ const r=await api('/api/report/prereg',{method:'POST',
    body:JSON.stringify({question:q.value})});
    po.innerHTML=''; po.appendChild(el('pre','term',esc(r.text)));
    po.appendChild(el('div','hint',esc(r.note))); };
  b3.append(q,mk,po);

  const [p4,b4]=panel('Reproducibility bundle'); w.appendChild(p4);
  b4.appendChild(el('div','hint','Data hash, every spec and result, the assumption checks, '+
    'the figures, and generated Python and R that reruns all of it.'));
  const mkb=el('button','primary','Build bundle');
  const bo=el('div'); bo.style.marginTop='8px';
  mkb.onclick=async()=>{ const r=await api('/api/report/bundle',{method:'POST',
    body:JSON.stringify({dataset:STATE.dataset})});
    bo.innerHTML='';
    const a=el('a','btn',`Download (${r.n_runs} runs, ${r.size_kb} kB)`);
    a.href='/api/download?path='+encodeURIComponent(r.path); bo.appendChild(a); };
  b4.append(mkb,bo);
}

// Runs ------------------------------------------------------------------
function paneRuns(w){
  const [pm,bm]=panel('Ledger maintenance', null, null,
    'Clearing the ledger resets the multiplicity audit, which is the point, but it '+
    'also means the tests you ran before it are no longer recorded anywhere. Clearing '+
    'only the failed or blocked entries tidies the list without touching the audit.');
  w.appendChild(pm);
  const bar=el('div','inline');
  [['failed','clear failed'],['blocked','clear blocked'],['all','clear everything']]
    .forEach(([scope,label])=>{
      const btn=el('button',scope==='all'?'danger':'',label);
      btn.onclick=async()=>{
        if(!await confirmDestructive(`Clear ${scope==='all'?'the whole ledger':scope+' runs'}?`,
            scope==='all'?'The multiplicity audit restarts from zero.'
                         :'Successful runs are untouched.')) return;
        const r=await api('/api/runs/clear',{method:'POST',
          body:JSON.stringify({scope, dataset:STATE.dataset})});
        toast(`${r.deleted} entries cleared`,'ok');
        if(r.note) setTimeout(()=>toast(r.note),400);
        renderPane(); refreshChips();
      };
      bar.appendChild(btn);
    });
  const figs=el('button','','clear all figures');
  figs.onclick=async()=>{
    if(!await confirmDestructive('Delete every rendered figure?',
        'The runs that produced them are kept, so they can be redrawn.')) return;
    const r=await api('/api/figures/clear',{method:'POST',body:'{}'});
    toast(`${r.deleted} figures deleted`,'ok');
  };
  bar.appendChild(figs);
  bm.appendChild(bar);

  const [p,b]=panel('Run ledger'); w.appendChild(p);
  b.appendChild(el('div','hint','Every test that has been executed, with its spec, its '+
    'assumption checks and its result. This is what makes the multiplicity audit possible.'));
  const list=el('div'); list.style.marginTop='8px'; b.appendChild(list);
  api('/api/runs').then(rows=>{
    if(!rows.length){ list.appendChild(el('div','empty','No runs yet.')); return; }
    const t=el('table');
    t.innerHTML='<tr><th>When</th><th>Test</th><th>Status</th><th class="num">ms</th><th></th></tr>';
    rows.forEach(r=>{
      const tr=el('tr',null,
        `<td class="mono" style="font-size:10.5px">${new Date(r.created_at*1000).toLocaleString()}</td>`+
        `<td class="mono">${esc(r.test_id)}</td>`+
        `<td style="color:${r.status==='ok'?'var(--pass)':r.status==='blocked'?'var(--caution)':'var(--fault)'}">${esc(r.status)}</td>`+
        `<td class="num">${r.duration_ms??''}</td><td></td>`);
      const del=el('button','ghost danger rowdel','delete');
      del.onclick=async(e)=>{
        e.stopPropagation();
        if(!await confirmDestructive(`Delete this ${r.test_id} run?`,
            'Any figures drawn from it go too.')) return;
        const res=await api('/api/runs/'+r.id,{method:'DELETE'});
        toast('Run deleted'+(res.figures_deleted?`, ${res.figures_deleted} figures`:''),'ok');
        renderPane(); refreshChips();
      };
      const btn=el('button','ghost','open');
      btn.onclick=async()=>{ const d=await api('/api/runs/'+r.id);
        STATE.result=Object.assign({},d.result,{run_id:d.id, checks:d.assumptions});
        STATE.code={python:d.code_python,r:d.code_r};
        STATE.pane='stats'; STATE.test=d.test_id;
        STATE.roles=(d.spec||{}).roles||{}; STATE.params=(d.spec||{}).params||{};
        renderRail(); renderPane(); };
      tr.lastChild.append(btn,del); t.appendChild(tr);
    });
    list.appendChild(t);
  });
}

// Settings --------------------------------------------------------------
function paneSettings(w){
  const groups={
    'Statistical defaults':['alpha','ci_level','decimals','p_decimals','p_min_display',
      'multiplicity_default','error_bar_default','assumption_policy','seed',
      'multiplicity_nag_after','exact_p_in_plots','ns_label'],
    'Figures':['fig_dpi','fig_format','fig_width_mm','palette','greyscale_check'],
    'Reporting':['citation_style','stats_report_style','software_footer'],
    'Harvest':['ncbi_api_key','ncbi_email','semantic_scholar_key','harvest_cache_hours',
      'harvest_rate_limit'],
    'Runtime':['max_concurrent_jobs','keep_job_history','confirm_destructive',
      'provenance_strict'],
  };
  Object.entries(groups).forEach(([g,keys])=>{
    const [p,b]=panel(g); w.appendChild(p);
      const HELP={
        alpha:'The threshold everything is judged against. It lives here rather than on each test, because an alpha you can change per test after seeing the result is not an alpha.',
        assumption_policy:'What happens when a declared assumption fails. Blocking is the honest default if you are working alone; automatic fallback is faster but you must read the note it leaves on the result.',
        multiplicity_nag_after:'How many tests on one dataset before the interface starts saying so. The count comes from the ledger, so it survives restarts.',
        seed:'Fixed for every bootstrap, permutation and simulation, so a rerun gives the same numbers and the reproducibility bundle is worth something.',
        p_min_display:'Below this, p values are reported as a threshold rather than a figure. Reporting p = .0000034 implies a precision the test does not have.',
        error_bar_default:'SEM bars look tighter than SD bars and mean something different. Whichever you pick, the figure prints the answer in its corner.',
        confirm_destructive:'Turn this off and the delete buttons stop asking. The danger zone still requires typing the word.',
        provenance_strict:'Refuses to run anything without hashing the dataset first. Off means faster, and means the ledger can no longer prove which data a result came from.',
        ncbi_email:'Required by Unpaywall and puts OpenAlex requests in the polite pool. Without it you will be rate limited.',
        ncbi_api_key:'Raises the PubMed limit from 3 to 10 requests per second. Free from an NCBI account.',
        citation_style:'Affects generated reference lists only, not the statistics text.',
        stats_report_style:'APA drops the leading zero from p values and italicises statistics; Vancouver does not.',
      };
    keys.forEach(k=>{
      const v=BOOT.config[k];
      const type=typeof v==='boolean'?'bool':typeof v==='number'?'number':'text';
      let p2={id:k, label:k.replace(/_/g,' '), type, help:HELP[k]};
      if(k==='assumption_policy') p2={id:k,label:'When an assumption fails',type:'select',
        choices:[['warn','Warn and run anyway'],['block','Block and offer the fallback'],
                 ['auto_fallback','Switch to the fallback automatically']]};
      if(k==='stats_report_style') p2={id:k,label:'Results style',type:'select',
        choices:[['apa','APA'],['vancouver','Vancouver'],['plain','Plain']]};
      if(k==='error_bar_default') p2={id:k,label:'Default error bars',type:'select',
        choices:[['sd','Standard deviation'],['sem','Standard error'],['ci95','95% CI']]};
      b.appendChild(field(p2, v, async(key,val)=>{
        BOOT.config[key]=val;
        await api('/api/config',{method:'POST',body:JSON.stringify({[key]:val})});
        refreshChips();
      }));
    });
  });
  // ── interface scale ─────────────────────────────────────────────────
  const [ps,bs]=panel('Interface', null, null,
    'Scale drives one CSS variable on the root element, and every size in the '+
    'interface is expressed relative to it, so type, controls, rails and spacing '+
    'all move together. This is not the browser zoom; it survives a reload.');
  w.appendChild(ps);
  const cur=BOOT.config.ui_scale||110;
  const sf=el('div','field');
  sf.appendChild(el('label',null,'Scale <span class="unit">'+cur+'%</span>'));
  const sl=el('input'); sl.type='range'; sl.min=85; sl.max=160; sl.step=5; sl.value=cur;
  const readout=sf.querySelector('.unit');
  sl.oninput=()=>{ readout.textContent=sl.value+'%'; applyScale(sl.value); };
  sl.onchange=async()=>{
    BOOT.config.ui_scale=parseInt(sl.value);
    await api('/api/config',{method:'POST',body:JSON.stringify({ui_scale:BOOT.config.ui_scale})});
    toast('Scale saved at '+sl.value+'%','ok');
  };
  sf.appendChild(sl);
  const marks=el('div','inline'); marks.style.marginTop='6px';
  [90,100,110,125,140].forEach(v=>{ const c=el('div','chip mono'+(v==cur?' on':''),v+'%');
    c.onclick=()=>{ sl.value=v; sl.oninput(); sl.onchange();
      $$('.chip',marks).forEach(x=>x.classList.remove('on')); c.classList.add('on'); };
    marks.appendChild(c); });
  sf.appendChild(marks);
  bs.appendChild(sf);

  const [p,b]=panel('Dependencies'); w.appendChild(p);
  const t=el('table');
  t.innerHTML='<tr><th>Package</th><th>Purpose</th><th>Status</th><th>Install</th></tr>';
  BOOT.deps.forEach(d=>t.appendChild(el('tr',null,
    `<td class="mono">${esc(d.pip)}</td><td>${esc(d.why)}</td>`+
    `<td style="color:${d.ok?'var(--signal)':d.required?'var(--fault)':'var(--warn)'}">`+
    `${d.ok?esc(d.version):(d.required?'required, missing':'optional, missing')}</td>`+
    `<td class="mono" style="font-size:.66rem;color:var(--dim)">${d.ok?'':esc(d.install)}</td>`)));
  b.appendChild(t);

  // ── danger zone ─────────────────────────────────────────────────────
  const [pd,bd]=panel('Danger zone', null, null,
    'The only place that removes a whole category at once. Each row counts what it '+
    'holds before you touch it, and nothing fires without typing the word. Everything '+
    'here is local to this machine: the config folder holds all of it.');
  w.appendChild(pd);
  const zone=el('div','danger-zone'); bd.appendChild(zone);
  api('/api/reset/scopes').then(scopes=>{
    scopes.forEach(sc=>{
      const row=el('div','danger-row');
      row.innerHTML=`<div class="what"><b>${esc(sc.label)}</b>`+
        `<span>${esc(sc.description)}</span></div>`+
        `<div class="n">${sc.count}</div>`;
      const arm=el('div','arm');
      const word=sc.id==='everything'?'ERASE':'CLEAR';
      const inp=el('input'); inp.type='text'; inp.placeholder='type '+word;
      const go=el('button','danger','clear'); go.disabled=true;
      inp.oninput=()=>{ go.disabled = inp.value.trim().toUpperCase()!==word; };
      go.onclick=async()=>{
        if(!await confirmDestructive(`Clear ${sc.label.toLowerCase()}?`,
            sc.description+`\n\n${sc.count} items.`)) return;
        const r=await api('/api/reset',{method:'POST',
          body:JSON.stringify({scope:sc.id, confirm:true})});
        if(r.error) return toast(r.error,'err');
        toast(`${sc.label}: ${r.deleted} removed`,'ok');
        STATE.dataset=null; STATE.dsMeta=null; STATE.result=null;
        $('#ds-chip').textContent='no dataset';
        renderPane(); refreshChips();
      };
      arm.append(inp,go);
      row.appendChild(arm);
      zone.appendChild(row);
    });
  });
}

// ── inspector ─────────────────────────────────────────────────────────
function renderInspector(){
  const i=$('#inspector'); i.innerHTML='';
  if(STATE.code&&STATE.pane==='stats'){
    const [p,b]=panel('Generated code'); i.appendChild(p);
    const tabs=el('div','tabs');
    ['python','r'].forEach((k,n)=>{ const t=el('div','tab'+(n===0?' on':''),k==='r'?'R':'Python');
      t.onclick=()=>{ $$('.tab',tabs).forEach(x=>x.classList.remove('on')); t.classList.add('on');
        pre.textContent=STATE.code[k]||''; }; tabs.appendChild(t); });
    const pre=el('pre','term', esc(STATE.code.python||''));
    b.append(tabs,pre);
    const cp=el('button','ghost','copy');
    cp.onclick=()=>{navigator.clipboard.writeText(pre.textContent); toast('Copied','ok');};
    b.appendChild(cp);
  }
  const [p2,b2]=panel('Jobs'); i.appendChild(p2);
  const jl=el('div'); jl.id='job-list'; b2.appendChild(jl);
  const log=el('div','term'); log.id='joblog'; b2.appendChild(log);
  refreshJobs();
}

async function refreshJobs(){
  const jl=$('#job-list'); if(!jl) return;
  const jobs=await api('/api/jobs');
  jl.innerHTML='';
  if(!jobs.length){ jl.appendChild(el('div','hint','No jobs.')); return; }
  jobs.slice(0,8).forEach(j=>{
    const d=el('div'); d.style.marginBottom='7px';
    d.innerHTML=`<div style="font-size:11.5px">${esc(j.title)}</div>`+
      `<div class="hint mono">${esc(j.status)}${j.note?' · '+esc(j.note):''}</div>`+
      `<div class="progress"><div class="fill" style="width:${j.progress}%"></div></div>`;
    if(j.status==='running'){ const c=el('button','ghost','cancel');
      c.onclick=()=>api('/api/jobs/'+j.id+'/cancel',{method:'POST'}); d.appendChild(c); }
    if(j.error) d.appendChild(el('div','note err',esc(j.error)));
    jl.appendChild(d);
  });
  const running=jobs.filter(j=>j.status==='running').length;
  const failed=jobs.some(j=>j.status==='failed');
  $('#dock-jobs').textContent=running?`${running} running`:`${jobs.length} jobs`;
  // One lamp beside the wordmark, one dot in the dock, both driven from here.
  $('#lamp').className='tally-lamp'+(running?' live':failed?' fault':'');
  $('#dock-dot').className='dot'+(running?' live':failed?' fault':'');
  $('#dock-status').textContent=running?jobs.find(j=>j.status==='running').title:'idle';
}

// ── events ────────────────────────────────────────────────────────────
function connectEvents(){
  const es=new EventSource('/api/events');
  es.onmessage=e=>{
    const ev=JSON.parse(e.data);
    if(ev.type==='log'){ const l=$('#joblog');
      if(l){ l.textContent+=ev.line+'\n'; l.scrollTop=l.scrollHeight; } }
    if(['status','progress','finished'].includes(ev.type)) refreshJobs();
    if(ev.type==='finished'){
      toast(ev.title+': '+ev.status, ev.status==='done'?'ok':'err');
      if(STATE.pane==='harvest'||STATE.pane==='screen') renderPane();
      refreshChips();
    }
  };
  es.onerror=()=>{ setTimeout(connectEvents, 4000); es.close(); };
}

async function refreshChips(){
  $('#alpha-chip').innerHTML='alpha <b>'+BOOT.config.alpha+'</b>';
  const runs=await api('/api/runs');
  const rc=$('#runs-chip');
  rc.innerHTML='<b>'+runs.length+'</b> runs';
  // The ledger turns amber once enough tests have been run on one dataset
  // that the nominal alpha stops meaning what it says.
  rc.className='topbar-path'+(runs.length>=BOOT.config.multiplicity_nag_after?' warn':'');
  const missing=BOOT.deps.filter(d=>!d.ok);
  const c=$('#dep-chip');
  c.innerHTML=missing.length?('<b>'+missing.length+'</b> pkg missing'):'all pkg present';
  c.className='topbar-path'+(missing.some(m=>m.required)?' warn':'');
}

// ── keys ──────────────────────────────────────────────────────────────
document.addEventListener('keydown', e=>{
  if(['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)) return;
  const map={'1':'data','2':'stats','3':'figures','4':'harvest','5':'screen',
             '6':'synthesis','7':'report','8':'runs','9':'settings','0':'library'};
  if(map[e.key]){ STATE.pane=map[e.key]; renderRail(); renderPane(); return; }
  if(STATE.pane==='screen'){
    if(e.key==='i') judge('include');
    if(e.key==='e') judge('exclude');
    if(e.key==='m') judge('maybe');
    if(e.key==='u') doUndo();
    if(e.key==='s'){ STATE.qi++; showCurrent(); }
  }
  if(e.key==='Enter'&&e.metaKey&&STATE.pane==='stats') doRun();
});


function applyScale(pct){
  document.documentElement.style.setProperty('--fs', (Number(pct)||110)/100);
}

// ── boot ──────────────────────────────────────────────────────────────
(async function(){
  BOOT=await api('/api/bootstrap');
  $('#version').textContent='v'+BOOT.app.version;
  applyScale(BOOT.config.ui_scale);
  $('#adv-toggle').onclick=e=>{
    const on=document.body.classList.toggle('show-adv');
    e.target.classList.toggle('on', on);
  };
  $('#dock-clear').onclick=async()=>{ await api('/api/jobs/clear',{method:'POST'}); refreshJobs(); };
  renderRail(); renderPane(); refreshChips(); connectEvents();
  const ds=await api('/api/datasets');
  if(ds.length){ STATE.dataset=ds[0].id; await loadDataset(); }
})();
"""
