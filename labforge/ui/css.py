"""Stylesheet.

Structure is TubeForge's: the same void / rack / rail / raise / seam ladder,
the same mono uppercase letterspaced labels, the same inset inputs sitting on
--void inside panels that sit on --rack, the same 4px radius and 120ms easing.
Anyone who uses both should not have to relearn where anything is.

What changes is the accent family. TubeForge is lit by a single tally orange.
This is lit by the two dyes every histology slide in the world is stained
with: hematoxylin, the blue-violet that takes to nuclei, and eosin, the pink
that takes to cytoplasm. Hematoxylin is the interaction colour, so anything
active, selected or running is violet. Eosin is reserved for statistical
emphasis: a significant p value, a star above a bracket, a pooled diamond.

Every other tint is a real stain too, and each is bound to one family of
content, so colour carries meaning rather than decoration:

  hematoxylin   violet    core statistics, active state
  eosin         pink      significance, effect sizes
  methylene     blue      descriptives, information
  fast green    teal      agreement, reliability, pass
  safranin      orange    categorical data
  crystal viol. purple    regression and models
  congo red     red       survival, faults
  iodine        amber     planning, power, caution
  PAS           magenta   bench and omics
  trypan        indigo    evidence synthesis
  silver        grey      epidemiology, inert

Amber and red never appear except as caution and fault, so a warning colour
in this interface never means anything except that the statistics are unhappy.
"""

CSS = r"""
:root{
  /* Structural ladder, carried over unchanged. */
  --void:#0b0c0e; --rack:#121418; --rail:#171a1f; --raise:#1d2128;
  --seam:#272c34; --seam-hi:#343a44;
  --ink:#dfe3e8; --ink-dim:#98a1ad; --dim:#6d7682;

  /* The stains. */
  --haem:#6f7df2; --eosin:#f2568f;
  --methylene:#5aa9f8; --fastgreen:#35d6b0; --safranin:#ff7d4d;
  --crystal:#a97cf5; --congo:#ff5f6d; --iodine:#f5a623;
  --pas:#e05bc8; --trypan:#5c74e8; --silver:#9aa3af;

  /* Functional aliases. Only these are used for state. */
  --signal:#35d6b0; --warn:#f5a623; --fault:#ff4d5e; --info:#5aa9f8;

  --mono:ui-monospace,"JetBrains Mono","Fira Code","Cascadia Mono","SF Mono",Menlo,Consolas,monospace;
  --sans:ui-sans-serif,"Inter","Segoe UI",system-ui,-apple-system,"Helvetica Neue",sans-serif;
  --r:4px; --t:120ms cubic-bezier(.4,0,.2,1);
  /* Chrome widths are in rem so the scale slider moves the whole layout,
     not just the type. */
  --rail-w:13.5rem; --insp-w:21rem;
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{font-size:calc(16px * var(--fs,1.1))}
body{
  font-family:var(--sans); background:var(--void); color:var(--ink);
  line-height:1.5; -webkit-font-smoothing:antialiased;
  height:100vh; overflow:hidden;
}
::selection{background:var(--haem);color:#0b0c0e}
:focus-visible{outline:2px solid var(--haem);outline-offset:2px}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--seam);border-radius:5px;border:2px solid var(--void)}
::-webkit-scrollbar-thumb:hover{background:var(--seam-hi)}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}

/* ─── Shell ─────────────────────────────────────────────────────────── */
#app{display:grid;grid-template-rows:2.9rem 1fr 1.8rem;height:100vh}
#topbar{
  display:flex;align-items:center;gap:13px;padding:0 14px;
  background:var(--rack);border-bottom:1px solid var(--seam);
}
.wordmark{display:flex;align-items:center;gap:10px}
.wordmark b{
  font:600 1.02rem/1 var(--sans);letter-spacing:.11em;text-transform:uppercase;
  color:var(--ink);
}
.wordmark b em{font-style:normal;color:var(--haem)}
.wordmark .ver{font:500 .6rem/1 var(--mono);color:var(--dim);letter-spacing:.1em}
/* Sized to the cap height of the wordmark beside it. A running job should be
   visible from across the room, not a pinprick. */
.tally-lamp{
  width:14px;height:14px;border-radius:50%;background:var(--seam-hi);
  box-shadow:0 0 0 1px rgba(0,0,0,.5) inset;flex:none;transition:background var(--t);
}
.tally-lamp.live{
  background:var(--haem);
  box-shadow:0 0 0 1px rgba(0,0,0,.4) inset, 0 0 10px var(--haem),
             0 0 20px rgba(111,125,242,.45);
  animation:pulse 1.6s ease-in-out infinite;
}
.tally-lamp.fault{
  background:var(--fault);
  box-shadow:0 0 0 1px rgba(0,0,0,.4) inset, 0 0 10px var(--fault);
}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.45}}
.spacer{flex:1}

.topbar-path{
  font:400 .72rem/1 var(--mono);color:var(--ink-dim);
  padding:5px 9px;background:var(--void);border:1px solid var(--seam);
  border-radius:var(--r);max-width:34ch;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap;cursor:pointer;transition:var(--t);
}
.topbar-path:hover{border-color:var(--seam-hi);color:var(--ink)}
.topbar-path b{color:var(--ink);font-weight:600}
.topbar-path.warn{border-color:rgba(245,166,35,.35);color:var(--warn)}
.topbar-path.eosin b{color:var(--eosin)}
.topbar-btn{
  font:500 .7rem/1 var(--sans);color:var(--ink-dim);background:transparent;
  border:1px solid var(--seam);border-radius:var(--r);padding:6px 10px;
  cursor:pointer;transition:var(--t);white-space:nowrap;
}
.topbar-btn:hover{color:var(--ink);border-color:var(--seam-hi);background:var(--rail)}
.topbar-btn.on{background:var(--haem);color:#0b0c0e;border-color:var(--haem);font-weight:600}
kbd{
  font:500 .62rem/1 var(--mono);background:var(--void);border:1px solid var(--seam);
  border-bottom-width:2px;border-radius:3px;padding:2px 4px;color:var(--dim);
}

/* ─── Layout ────────────────────────────────────────────────────────── */
#body{display:grid;grid-template-columns:var(--rail-w) minmax(0,1fr) var(--insp-w);
      overflow:hidden;min-height:0}
#rail{grid-column:1;background:var(--rack);border-right:1px solid var(--seam);
      overflow-y:auto;padding:10px 0 20px}
#work{grid-column:2;overflow-y:auto;padding:18px 20px 40px;min-width:0}
#inspector{grid-column:3;background:var(--rack);border-left:1px solid var(--seam);
           overflow-y:auto;padding:10px 12px 20px}

.rail-group{margin-bottom:6px}
.rail-head{
  font:600 .58rem/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;
  color:var(--dim);padding:12px 16px 6px;display:flex;align-items:center;gap:7px;
}
/* The same header inside a panel body needs no rail indent. */
.panel-body .rail-head{padding:13px 0 6px}
.rail-head::before{content:"";width:5px;height:5px;border-radius:50%;
                   background:currentColor;opacity:.85;flex:none}
.nav{
  display:flex;align-items:center;gap:10px;width:100%;
  padding:7px 16px;background:none;border:0;border-left:2px solid transparent;
  color:var(--ink-dim);font:500 .82rem/1.2 var(--sans);cursor:pointer;
  text-align:left;transition:var(--t);
}
.nav:hover{color:var(--ink);background:var(--rail)}
.nav.on{color:var(--ink);background:var(--rail);border-left-color:var(--haem)}
.nav .count{margin-left:auto;font:600 .6rem/1 var(--mono);background:var(--seam);
            color:var(--ink-dim);padding:2px 5px;border-radius:3px}
.nav.on .count{background:rgba(111,125,242,.2);color:var(--haem)}
.nav.stub{opacity:.55}
.rail-foot{
  margin-top:14px;padding:12px 16px 0;border-top:1px solid var(--seam);
  font:400 .66rem/1.5 var(--mono);color:var(--dim);
}
.rail-foot b{display:block;color:var(--ink-dim);font-weight:600;margin-bottom:3px}

/* ─── Panels ────────────────────────────────────────────────────────── */
.view-head{margin-bottom:13px;padding-bottom:9px;border-bottom:1px solid var(--seam)}
.view-head h1{font-size:1.12rem;font-weight:650;letter-spacing:-.01em;
              display:flex;align-items:center;gap:11px;flex-wrap:wrap}
.view-head p{color:var(--dim);font-size:.75rem;margin-top:3px;max-width:88ch}

.panel{background:var(--rack);border:1px solid var(--seam);border-radius:var(--r);
       margin-bottom:14px;overflow:hidden}
.panel-head{display:flex;align-items:center;gap:10px;padding:9px 13px;
            background:var(--rail);border-bottom:1px solid var(--seam);
            cursor:pointer;user-select:none;flex-wrap:wrap;row-gap:7px}
.panel-head:hover{background:var(--raise)}
.panel-head h3{font:600 .63rem/1 var(--mono);letter-spacing:.15em;
               text-transform:uppercase;color:var(--ink-dim)}
.hint{font:400 .73rem/1.5 var(--sans);color:var(--dim)}
.panel-head .hint{font:400 .68rem/1 var(--mono);margin-left:auto}
.panel-body{padding:14px 13px}
.panel.collapsed .panel-body{display:none}
.chev{transition:transform var(--t);color:var(--dim);font-size:.7rem}
.panel.collapsed .chev{transform:rotate(-90deg)}

.cols{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px}
@media (max-width:1420px){.cols{grid-template-columns:1fr}}
.inline{display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.inline > *{margin-bottom:0}
.inline .grow{flex:1;min-width:0}

/* ─── Controls ──────────────────────────────────────────────────────── */
.field{margin-bottom:11px}
.field:last-child{margin-bottom:0}
.field.adv{display:none}
body.show-adv .field.adv{display:block}
label,.lbl{
  display:block;font:600 .6rem/1.4 var(--mono);letter-spacing:.1em;
  text-transform:uppercase;color:var(--dim);margin-bottom:5px;
}
label .unit{color:var(--seam-hi);letter-spacing:.06em}
.help{font:400 .71rem/1.45 var(--sans);color:var(--dim);margin-top:4px;
      text-transform:none;letter-spacing:0}
input[type=text],input[type=number],input[type=password],select,textarea{
  width:100%;padding:7px 9px;background:var(--void);color:var(--ink);
  border:1px solid var(--seam);border-radius:var(--r);
  font:400 .8rem/1.35 var(--sans);transition:border-color var(--t),background var(--t);
}
input[type=text],textarea,input[type=password]{font-family:var(--mono);font-size:.76rem}
select{font-family:var(--sans);cursor:pointer}
input:hover,select:hover,textarea:hover{border-color:var(--seam-hi)}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--haem);
                                        background:var(--rack)}
input::placeholder,textarea::placeholder{color:#4d545e}
textarea{resize:vertical;min-height:62px}
input[type=range]{width:100%;accent-color:var(--haem)}

.check{display:flex;align-items:flex-start;gap:8px;cursor:pointer;padding:5px 0;
       font-size:.8rem;color:var(--ink-dim);line-height:1.35}
.check:hover{color:var(--ink)}
.check input{margin-top:2px;accent-color:var(--haem);flex:none;width:14px;height:14px;
             cursor:pointer}

.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{
  padding:4px 9px;background:var(--void);border:1px solid var(--seam);
  border-radius:var(--r);font:500 .71rem/1 var(--sans);color:var(--ink-dim);
  cursor:pointer;transition:var(--t);
}
.chip:hover{border-color:var(--haem);color:var(--ink)}
.chip.on{background:var(--haem);color:#0b0c0e;border-color:var(--haem);font-weight:600}
.chip.mono{font-family:var(--mono);font-size:.68rem}

.btn,button{
  font:500 .74rem/1 var(--sans);color:var(--ink-dim);background:var(--rail);
  border:1px solid var(--seam);border-radius:var(--r);padding:7px 12px;
  cursor:pointer;transition:var(--t);display:inline-flex;align-items:center;gap:7px;
  text-decoration:none;
}
.btn:hover,button:hover{color:var(--ink);border-color:var(--seam-hi);background:var(--raise)}
button:disabled{opacity:.4;cursor:not-allowed}
button.primary{background:var(--haem);border-color:var(--haem);color:#0b0c0e;font-weight:600}
button.primary:hover{background:#5f6de6;border-color:#5f6de6;color:#0b0c0e}
button.danger{color:var(--eosin);border-color:rgba(242,86,143,.35)}
button.danger:hover{background:rgba(242,86,143,.1);border-color:var(--eosin);color:var(--eosin)}
button.ghost{background:transparent;border-color:transparent;color:var(--dim);padding:5px 7px}
button.ghost:hover{color:var(--ink);background:var(--rail)}

/* ─── Stain tags ────────────────────────────────────────────────────── */
.tag{display:inline-block;padding:2px 6px;border-radius:3px;margin:0 4px 3px 0;
     font:600 .6rem/1.5 var(--mono);letter-spacing:.06em;text-transform:uppercase}
.tag.haem{background:rgba(111,125,242,.16);color:var(--haem)}
.tag.eosin{background:rgba(242,86,143,.16);color:var(--eosin)}
.tag.methylene{background:rgba(90,169,248,.16);color:var(--methylene)}
.tag.fastgreen{background:rgba(53,214,176,.16);color:var(--fastgreen)}
.tag.safranin{background:rgba(255,125,77,.16);color:var(--safranin)}
.tag.crystal{background:rgba(169,124,245,.16);color:var(--crystal)}
.tag.congo{background:rgba(255,95,109,.16);color:var(--congo)}
.tag.iodine{background:rgba(245,166,35,.16);color:var(--iodine)}
.tag.pas{background:rgba(224,91,200,.16);color:var(--pas)}
.tag.trypan{background:rgba(92,116,232,.16);color:var(--trypan)}
.tag.silver,.tag.other{background:var(--seam);color:var(--ink-dim)}

/* Outlined variant, for inline labels beside a heading. */
.tool-tag{
  display:inline-flex;align-items:center;gap:5px;padding:3px 7px;border-radius:3px;
  font:600 .58rem/1 var(--mono);letter-spacing:.11em;text-transform:uppercase;
  background:var(--void);border:1px solid var(--seam);color:var(--dim);white-space:nowrap;
}
.tool-tag::before{content:"";width:5px;height:5px;border-radius:50%;background:currentColor}
.tool-tag.haem{color:var(--haem);border-color:rgba(111,125,242,.3)}
.tool-tag.eosin{color:var(--eosin);border-color:rgba(242,86,143,.3)}
.tool-tag.methylene{color:var(--methylene);border-color:rgba(90,169,248,.3)}
.tool-tag.fastgreen{color:var(--fastgreen);border-color:rgba(53,214,176,.3)}
.tool-tag.safranin{color:var(--safranin);border-color:rgba(255,125,77,.3)}
.tool-tag.crystal{color:var(--crystal);border-color:rgba(169,124,245,.3)}
.tool-tag.congo{color:var(--congo);border-color:rgba(255,95,109,.3)}
.tool-tag.iodine{color:var(--iodine);border-color:rgba(245,166,35,.3)}
.tool-tag.pas{color:var(--pas);border-color:rgba(224,91,200,.3)}
.tool-tag.trypan{color:var(--trypan);border-color:rgba(92,116,232,.3)}
.tool-tag.silver{color:var(--silver)}
.tool-row{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin-top:8px}

/* A group header takes the stain of the family it holds. */
.rail-head.haem{color:var(--haem)} .rail-head.eosin{color:var(--eosin)}
.rail-head.methylene{color:var(--methylene)} .rail-head.fastgreen{color:var(--fastgreen)}
.rail-head.safranin{color:var(--safranin)} .rail-head.crystal{color:var(--crystal)}
.rail-head.congo{color:var(--congo)} .rail-head.iodine{color:var(--iodine)}
.rail-head.pas{color:var(--pas)} .rail-head.trypan{color:var(--trypan)}
.rail-head.silver{color:var(--silver)}

/* ─── Hover help ────────────────────────────────────────────────────── */
/* The long explanation moves behind this, so a screen opens with controls
   rather than three lines of prose. One floating tip serves every ? on the
   page, positioned against whichever one asked for it. */
.qmark{
  display:inline-flex;align-items:center;justify-content:center;
  width:.95rem;height:.95rem;flex:none;border-radius:50%;
  border:1px solid var(--seam-hi);background:var(--rack);
  color:var(--dim);font:700 .62rem/1 var(--sans);cursor:help;padding:0;
  transition:var(--t);vertical-align:middle;
}
.qmark:hover,.qmark:focus-visible{border-color:var(--haem);color:var(--haem);
                                  background:var(--rail)}
label .qmark{margin-left:5px;vertical-align:-1px}
.panel-head .qmark{margin-left:-2px}
.view-head .qmark{width:1.05rem;height:1.05rem;font-size:.7rem}
#tip{
  position:fixed;z-index:600;max-width:22rem;padding:9px 11px;
  background:var(--raise);border:1px solid var(--seam-hi);border-radius:6px;
  box-shadow:0 14px 36px rgba(0,0,0,.5);
  font:400 .74rem/1.55 var(--sans);color:var(--ink-dim);
}
#tip[hidden]{display:none}
#tip b{color:var(--ink);display:block;margin-bottom:3px;font-size:.76rem;
       font-weight:600}
#tip code{font-family:var(--mono);font-size:.7rem;color:var(--haem)}

/* ─── Assumption gate ───────────────────────────────────────────────── */
.gate{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 4px}
.lozenge{
  display:inline-flex;align-items:center;gap:6px;padding:4px 9px;border-radius:11px;
  font:500 .65rem/1 var(--mono);letter-spacing:.04em;
  background:var(--void);border:1px solid var(--seam);color:var(--ink-dim);
}
.lozenge .dot{width:6px;height:6px;border-radius:50%;flex:none}
.lozenge.pass{border-color:rgba(53,214,176,.32)}
.lozenge.pass .dot{background:var(--signal)}
.lozenge.caution{border-color:rgba(245,166,35,.38);color:var(--warn)}
.lozenge.caution .dot{background:var(--warn)}
.lozenge.fail{border-color:rgba(255,77,94,.45);color:var(--fault)}
.lozenge.fail .dot{background:var(--fault)}
.lozenge.skip{opacity:.55} .lozenge.skip .dot{background:var(--dim)}

.checkdetail{
  border-left:2px solid var(--seam);padding:6px 0 6px 10px;margin:7px 0;
  font-size:.74rem;line-height:1.5;color:var(--ink-dim);
}
.checkdetail.fail{border-left-color:var(--fault)}
.checkdetail.caution{border-left-color:var(--warn)}
.checkdetail.pass{border-left-color:var(--signal)}
.checkdetail b{color:var(--ink);font:600 .58rem/1.4 var(--mono);letter-spacing:.12em;
               text-transform:uppercase;display:block;margin-bottom:3px}
.checkdetail .fix{color:var(--haem);margin-top:4px;display:block}

/* ─── Notes ─────────────────────────────────────────────────────────── */
.note{
  background:rgba(245,166,35,.07);border:1px solid rgba(245,166,35,.25);
  border-radius:var(--r);padding:9px 11px;font-size:.72rem;line-height:1.5;
  color:var(--warn);margin:9px 0;
}
.note b{font-size:.73rem;display:block;margin-bottom:2px}
.note.info{background:rgba(90,169,248,.07);border-color:rgba(90,169,248,.25);color:var(--info)}
.note.ok{background:rgba(53,214,176,.07);border-color:rgba(53,214,176,.25);color:var(--signal)}
.note.err{background:rgba(255,77,94,.08);border-color:rgba(255,77,94,.3);color:#ff8f99}
.note pre{font:400 .71rem/1.6 var(--mono);white-space:pre-wrap;color:inherit;
          background:none;border:0;padding:0;margin:0}

/* ─── Readouts ──────────────────────────────────────────────────────── */
.readout{
  background:var(--void);border:1px solid var(--seam);border-left:2px solid var(--haem);
  border-radius:var(--r);padding:11px 12px;
  font:400 .73rem/1.65 var(--mono);color:var(--ink-dim);
  white-space:pre-wrap;word-break:break-word;overflow-x:auto;position:relative;
}
.readout.eosin{border-left-color:var(--eosin)}
.readout:hover{border-color:var(--seam-hi)}
.readout-stage{font:600 .58rem/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;
               color:var(--dim);margin-bottom:6px;display:block}
.copy-btn{
  position:absolute;top:6px;right:6px;opacity:0;transition:var(--t);
  background:var(--rail);border:1px solid var(--seam);color:var(--ink-dim);
  border-radius:3px;padding:3px 7px;font:500 .62rem/1 var(--sans);cursor:pointer;
}
.readout:hover .copy-btn{opacity:1}
.copy-btn:hover{color:var(--ink);border-color:var(--seam-hi)}
.term{
  background:#08090b;border:1px solid var(--seam);border-radius:var(--r);
  padding:10px 12px;font:400 .72rem/1.55 var(--mono);
  max-height:200px;overflow-y:auto;white-space:pre-wrap;word-break:break-word;color:#a8b0ba;
}

/* ─── Numeric readouts ──────────────────────────────────────────────── */
.kv{display:grid;grid-template-columns:auto 1fr;gap:4px 14px;font-size:.76rem}
.kv dt{font:600 .6rem/1.6 var(--mono);letter-spacing:.08em;text-transform:uppercase;
       color:var(--dim)}
.kv dd{font-family:var(--mono);font-size:.73rem;color:var(--ink);word-break:break-word}

.hero{display:flex;gap:26px;flex-wrap:wrap;padding:4px 0 12px}
.hero .item{min-width:82px}
.hero .lab{font:600 .58rem/1.4 var(--mono);letter-spacing:.14em;text-transform:uppercase;
           color:var(--dim)}
.hero .val{font:500 1.42rem/1.25 var(--mono);font-variant-numeric:tabular-nums;
           letter-spacing:-.02em;color:var(--ink)}
.hero .val.sig{color:var(--eosin)}
.hero .sub{font:400 .66rem/1.4 var(--mono);color:var(--dim)}

/* ─── Tables ────────────────────────────────────────────────────────── */
.tablewrap{max-height:460px;overflow:auto;border:1px solid var(--seam);
           border-radius:var(--r);background:var(--void)}
table{width:100%;border-collapse:collapse;font-size:.75rem}
th{
  text-align:left;font:600 .58rem/1.5 var(--mono);letter-spacing:.12em;
  text-transform:uppercase;color:var(--dim);padding:7px 9px;white-space:nowrap;
  border-bottom:1px solid var(--seam);position:sticky;top:0;background:var(--rail);z-index:2;
}
td{padding:5px 9px;border-bottom:1px solid rgba(39,44,52,.6);vertical-align:top;
   color:var(--ink-dim)}
td.num,th.num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums}
tr:hover td{background:rgba(111,125,242,.055);color:var(--ink)}
td.subrow{padding-left:22px;color:var(--dim)}
.sig{color:var(--eosin);font-weight:600}

/* ─── Records ───────────────────────────────────────────────────────── */
.record{background:var(--rack);border:1px solid var(--seam);border-radius:var(--r);
        padding:11px 12px;margin-bottom:8px;transition:var(--t)}
.record:hover{border-color:var(--seam-hi)}
.record.retracted{border-color:rgba(255,95,109,.4)}
.record h4{font:600 .84rem/1.4 var(--sans);color:var(--ink);margin-bottom:4px}
.record .meta{font:400 .68rem/1.5 var(--mono);color:var(--dim);margin-bottom:7px}
.record .abs{font-size:.74rem;color:var(--ink-dim);max-height:96px;overflow:hidden;
             line-height:1.55}

/* ─── Misc ──────────────────────────────────────────────────────────── */
.empty{padding:34px 18px;text-align:center;color:var(--dim);font-size:.82rem;
       border:1px dashed var(--seam);border-radius:var(--r)}
.empty b{display:block;color:var(--ink-dim);font-size:.9rem;margin-bottom:5px;font-weight:600}
.tabs{display:flex;gap:2px;border-bottom:1px solid var(--seam);margin-bottom:11px}
.tabs .tab{padding:6px 12px;font:500 .7rem/1 var(--sans);color:var(--dim);cursor:pointer;
           border-bottom:2px solid transparent;margin-bottom:-1px;transition:var(--t)}
.tabs .tab:hover{color:var(--ink)}
.tabs .tab.on{color:var(--ink);border-bottom-color:var(--haem)}
.figbox{border:1px solid var(--seam);border-radius:var(--r);background:#fff;padding:9px;
        text-align:center}
.figbox img{max-width:100%;border-radius:2px;display:block;margin:0 auto}
.progress{height:3px;background:var(--seam);border-radius:2px;overflow:hidden;margin:6px 0}
.progress .fill{height:100%;background:var(--haem);transition:width .2s}
.stub-flag{font:600 .55rem/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;
           color:var(--warn);border:1px solid rgba(245,166,35,.3);border-radius:3px;
           padding:2px 4px;margin-left:auto}

/* ─── Handbook ──────────────────────────────────────────────────────── */
/* Reading width capped, because a 1400px line of prose is unreadable and the
   rest of the interface is not prose. */
.article{max-width:74ch;font-size:.82rem;line-height:1.65;color:var(--ink-dim)}
.article p{margin:0 0 .85rem}
.article h4{font:600 .68rem/1.4 var(--mono);letter-spacing:.13em;text-transform:uppercase;
            color:var(--haem);margin:1.5rem 0 .55rem}
.article h4:first-child{margin-top:0}
.article strong{color:var(--ink);font-weight:600}
.article code{font-family:var(--mono);font-size:.76rem;color:var(--eosin);
              background:var(--void);border:1px solid var(--seam);border-radius:3px;
              padding:1px 4px}
.article ul,.article ol{margin:0 0 .9rem 1.15rem}
.article li{margin-bottom:.3rem}
.article li::marker{color:var(--haem)}
.article blockquote{border-left:2px solid var(--eosin);border-radius:0;
                    background:rgba(242,86,143,.05);padding:9px 12px;margin:0 0 1rem;
                    color:var(--ink-dim);font-style:normal}
.article pre.term{margin:0 0 1rem;font-size:.73rem}
.article .tablewrap{margin:0 0 1.1rem;max-height:none}
.article table{font-size:.76rem}
.article th{background:var(--rail)}
.article a.xlink{color:var(--haem);cursor:pointer;border-bottom:1px solid rgba(111,125,242,.35)}
.article a.xlink:hover{color:var(--eosin);border-bottom-color:var(--eosin)}

/* ─── Destructive controls ──────────────────────────────────────────── */
/* Congo red, and nowhere else. If something on screen is this colour it
   removes data. */
.danger-zone{border:1px solid rgba(255,95,109,.28);border-radius:var(--r);
             background:rgba(255,95,109,.035);padding:11px 12px}
.danger-row{display:flex;align-items:center;gap:11px;padding:8px 0;
            border-bottom:1px solid rgba(39,44,52,.7)}
.danger-row:last-child{border-bottom:0}
.danger-row .what{flex:1;min-width:0}
.danger-row .what b{display:block;font:600 .74rem/1.3 var(--sans);color:var(--ink)}
.danger-row .what span{font:400 .69rem/1.4 var(--sans);color:var(--dim)}
.danger-row .n{font:500 .8rem/1 var(--mono);color:var(--congo);
               font-variant-numeric:tabular-nums;min-width:3.2rem;text-align:right}
.arm{display:flex;align-items:center;gap:8px}
.arm input[type=text]{width:9rem;font-size:.7rem}

.rowdel{opacity:0;transition:var(--t)}
tr:hover .rowdel,.record:hover .rowdel{opacity:1}

/* ─── Dock ──────────────────────────────────────────────────────────── */
#dock{
  display:flex;align-items:center;gap:11px;padding:0 13px;background:var(--rack);
  border-top:1px solid var(--seam);font:400 .66rem/1 var(--mono);color:var(--dim);
}
#dock .dot{width:6px;height:6px;border-radius:50%;background:var(--seam-hi);flex:none}
#dock .dot.live{background:var(--haem);animation:pulse 1.6s ease-in-out infinite}
#dock .dot.fault{background:var(--fault)}
#dock a{color:var(--dim);cursor:pointer;text-decoration:none;transition:var(--t)}
#dock a:hover{color:var(--haem)}

.toast{
  position:fixed;bottom:40px;right:16px;z-index:500;max-width:420px;
  background:var(--raise);border:1px solid var(--seam-hi);border-left:2px solid var(--haem);
  border-radius:var(--r);padding:10px 13px;font-size:.76rem;color:var(--ink-dim);
  box-shadow:0 14px 36px rgba(0,0,0,.55);animation:slidein var(--t);
}
@keyframes slidein{from{opacity:0;transform:translateX(8px)}to{opacity:1;transform:none}}
.toast.err{border-left-color:var(--fault);color:#ff8f99}
.toast.ok{border-left-color:var(--signal)}
"""
