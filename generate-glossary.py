#!/usr/bin/env python3
"""
generate-glossary.py  –  music-website/
Reads music-dictionary.org and writes:
  glossary.yml           (Quarto glossary extension: slug: DEF_SHORT)
  resources/glossary.qmd (interactive glossary page)

Run from the music-website/ directory:
  python3 generate-glossary.py
"""

import re
import os
import html as html_lib

ORG_FILE = 'music-dictionary.org'
YML_OUT  = 'glossary.yml'
QMD_OUT  = 'resources/glossary.qmd'

# ── Importance ────────────────────────────────────────────────────────────────

CORE_SLUGS = {
    'a-cappella', 'accelerando', 'adagio', 'allegretto', 'allegro',
    'andante', 'aria', 'arpeggio', 'cadence', 'canon', 'cantata',
    'chord', 'chromatic', 'coda', 'concerto', 'consonance',
    'counterpoint', 'crescendo', 'da-capo', 'diminuendo', 'dissonance',
    'dominant', 'dynamics', 'fermata', 'forte', 'fortissimo', 'fugue',
    'grave', 'harmony', 'homophony', 'improvisation', 'interval',
    'key', 'largo', 'legato', 'lento', 'major', 'melody', 'meter',
    'minor', 'moderato', 'modulation', 'monophony', 'motif',
    'octave', 'opus', 'ornamentation', 'ostinato', 'pentatonic-scale',
    'piano', 'pianissimo', 'pitch', 'pizzicato', 'polyphony',
    'presto', 'rhythm', 'ritardando', 'rondo', 'rubato', 'scale',
    'sforzando', 'simple-time', 'sonata', 'staccato', 'subdominant',
    'symphony', 'tempo', 'tenuto', 'texture', 'timbre',
    'time-signature', 'tonality', 'tonic', 'transposition', 'vivace',
    '12-bar-blues', 'call-and-response',
    # roman numerals
    'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii',
}

EXPERT_SLUGS = {
    'adsr', 'additive-synthesis', 'bit-depth', 'convolution-reverb',
    'fm-synthesis', 'granular-synthesis', 'lfo', 'nyquist-theorem',
    'physical-modelling', 'sample-rate', 'sidechain-compression',
    'subtractive-synthesis', 'vocoder', 'wavetable-synthesis',
    'wave-shaping',
}

CAT_LABEL = {
    'roman-numeral': 'Roman Numerals',
    'italian':       'Italian',
    'harmony':       'Harmony',
    'technology':    'Technology',
    'non-western':   'Non-Western',
    'vocal':         'Vocal',
    'form':          'Form',
    'homograph':     'Homograph',
    'general':       'General',
}

# ── Slug helpers ──────────────────────────────────────────────────────────────

def slugify(name):
    """Convert a term name to a URL-safe slug."""
    s = name.lower()
    s = re.sub(r'[/()°\'"\\]', '-', s)
    s = re.sub(r'[^a-z0-9\-]', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s

def term_display(name):
    """Clean display name (strip org tags if any leaked through)."""
    return re.sub(r'\s*:[a-z_-]+:\s*$', '', name).strip()

# ── Org formatting → HTML ────────────────────────────────────────────────────

def org_to_html(text):
    """Convert a block of org-mode body text to HTML."""
    # Preserve existing HTML tags
    # Convert internal org links: [[*target][label]] → <a href="#slug">label</a>
    text = re.sub(
        r'\[\[\*([^\]]+)\]\[([^\]]+)\]\]',
        lambda m: '<a href="#%s">%s</a>' % (slugify(m.group(1)), m.group(2)),
        text
    )
    # Convert external links: [[url][label]] → <a href="url" target="_blank">label</a>
    text = re.sub(
        r'\[\[(?!\*)(https?://[^\]]+)\]\[([^\]]+)\]\]',
        lambda m: '<a href="%s" target="_blank">%s</a>' % (m.group(1), m.group(2)),
        text
    )
    # *See also:* → styled lead
    text = re.sub(r'\*See also:\*', '<em>See also:</em>', text)
    # *bold* → <strong> (conservative: only when surrounded by spaces/punctuation)
    text = re.sub(r'(?<![a-zA-Z])\*([^*\n]+)\*(?![a-zA-Z])', r'<strong>\1</strong>', text)
    return text.strip()

def body_to_paragraphs(raw_body):
    """Split a raw org body into HTML paragraph strings."""
    raw_body = raw_body.strip()
    if not raw_body:
        return ''
    # Split on blank lines
    blocks = re.split(r'\n{2,}', raw_body)
    result = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        converted = org_to_html(block)
        if converted:
            result.append('<p>%s</p>' % converted)
    return '\n    '.join(result)

# ── Org parser ────────────────────────────────────────────────────────────────

def parse_org(path):
    """
    Parse the org file and return a list of entry dicts:
      slug, display, ipa, def_short, tags, cats (list), body_html,
      sources (list of URLs), see_also_html, importance, section
    Roman Numerals section is tagged 'roman-numeral'.
    Bibliography section is skipped.
    """
    with open(path, encoding='utf-8') as f:
        raw = f.read()

    entries = []
    current_section = None  # top-level heading text

    # Split into level-1 sections
    l1_pattern = re.compile(r'^\* (.+)$', re.MULTILINE)
    l1_splits = list(l1_pattern.finditer(raw))

    for i, l1_match in enumerate(l1_splits):
        section_name = l1_match.group(1).strip()
        section_start = l1_match.end()
        section_end = l1_splits[i + 1].start() if i + 1 < len(l1_splits) else len(raw)
        section_body = raw[section_start:section_end]

        if section_name in ('Bibliography',):
            continue  # skip

        is_roman = (section_name == 'Roman Numerals')

        # Find level-2 entries
        l2_pattern = re.compile(
            r'^\*\* (.+?)\n'            # heading line (term + optional tags)
            r'((?::PROPERTIES:.*?:END:(?:\n|$))?)'  # optional PROPERTIES block
            r'(.*?)(?=^\*\* |\Z)',       # body until next ** or end
            re.MULTILINE | re.DOTALL
        )

        for m2 in l2_pattern.finditer(section_body):
            heading_line  = m2.group(1).strip()
            props_block   = m2.group(2)
            body_raw      = m2.group(3).strip()

            # Extract inline org tags from heading: :tag1:tag2:
            tag_match = re.search(r'\s+((?::[a-z_-]+:)+)\s*$', heading_line)
            if tag_match:
                raw_tags = re.findall(r':([a-z_-]+):', tag_match.group(1))
                display_name = heading_line[:tag_match.start()].strip()
            else:
                raw_tags = []
                display_name = heading_line.strip()

            # Category: use first org tag, or roman-numeral, or general
            if is_roman:
                cats = ['roman-numeral']
            elif raw_tags:
                cats = raw_tags
            else:
                cats = ['general']

            slug = slugify(display_name)

            # Parse PROPERTIES
            props = {}
            for prop_m in re.finditer(r':([A-Z_0-9]+):\s+(.+)', props_block):
                props[prop_m.group(1)] = prop_m.group(2).strip()

            ipa       = props.get('IPA', '')
            def_short = props.get('DEF_SHORT', '')
            sources   = [v for k, v in sorted(props.items()) if k.startswith('SOURCE_')]

            # Body: strip the PROPERTIES block from it (props_block may be in body)
            body_clean = re.sub(r':PROPERTIES:.*?:END:\n?', '', body_raw, flags=re.DOTALL).strip()

            # Extract "See also" line(s)
            see_also_match = re.search(r'\*See also:\*\s*(.+?)(?=\n\n|\Z)', body_clean, re.DOTALL)
            see_also_html = ''
            if see_also_match:
                sa_raw = see_also_match.group(1).replace('\n', ' ')
                sa_converted = org_to_html(sa_raw)
                see_also_html = sa_converted
                # Remove see-also from body
                body_clean = body_clean[:see_also_match.start()].strip()

            body_html = body_to_paragraphs(body_clean)

            # Importance
            if slug in CORE_SLUGS or (is_roman and slug in ('i','ii','iii','iv','v','vi','vii')):
                importance = 'core'
            elif slug in EXPERT_SLUGS:
                importance = 'expert'
            elif 'harmony' in cats or 'form' in cats:
                importance = 'core'
            else:
                importance = 'enriching'

            entries.append({
                'slug':        slug,
                'display':     term_display(display_name),
                'ipa':         ipa,
                'def_short':   def_short,
                'cats':        cats,
                'body_html':   body_html,
                'sources':     sources,
                'see_also_html': see_also_html,
                'importance':  importance,
                'section':     section_name,
            })

    return entries

# ── glossary.yml writer ───────────────────────────────────────────────────────

YML_HEADER = """\
# Music glossary — generated from music-dictionary.org
# Run generate-glossary.py to regenerate.
#
# Format: slug: |
#   One-sentence definition (used for inline popup tooltips)
"""

def write_yml(entries, path):
    lines = [YML_HEADER]
    current_section = None
    for e in entries:
        if e['section'] != current_section:
            current_section = e['section']
            lines.append('\n# ── %s %s\n' % (current_section, '─' * max(0, 58 - len(current_section))))
        if not e['def_short']:
            continue
        # Escape pipe chars in value
        val = e['def_short'].replace('|', '\\|')
        lines.append('%s: |\n  %s\n' % (e['slug'], val))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(''.join(lines))
    print('Wrote %s (%d entries)' % (path, sum(1 for e in entries if e['def_short'])))

# ── glossary.qmd writer ───────────────────────────────────────────────────────

CSS = """\
<style>
.gl-controls {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid #e8e0d4;
}
.gl-row { display: flex; align-items: flex-start; gap: 0.75rem; flex-wrap: wrap; }
.gl-label { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.07em; color: #888; padding-top: 0.35rem; min-width: 5.5rem; }
.cat-dropdown-wrap { position: relative; display: inline-block; }
.cat-trigger { font-size: 0.82rem; padding: 0.3rem 2rem 0.3rem 0.7rem; border: 1px solid #c8bfaf; border-radius: 3px; background: #faf8f5; color: #2c2416; cursor: pointer; min-width: 160px; text-align: left; position: relative; }
.cat-panel { display: none; position: absolute; top: calc(100% + 4px); left: 0; z-index: 100; background: #faf8f5; border: 1px solid #c8bfaf; border-radius: 3px; padding: 0.6rem 0.75rem; min-width: 220px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.cat-panel.open { display: block; }
.cat-panel label { display: flex; align-items: center; gap: 0.45rem; font-size: 0.82rem; color: #2c2416; padding: 0.25rem 0; cursor: pointer; }
.cat-panel hr { border: none; border-top: 1px solid #e8e0d4; margin: 0.4rem 0; }
.logic-toggle { display: flex; align-items: center; gap: 0.35rem; font-size: 0.78rem; color: #666; margin-top: 0.45rem; }
.logic-btn { font-size: 0.75rem; padding: 0.15rem 0.5rem; border: 1px solid #c8bfaf; border-radius: 2rem; background: transparent; color: #888; cursor: pointer; }
.logic-btn.active { background: #2c2416; color: #faf8f5; border-color: #2c2416; }
.sort-row { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.sort-btn { font-size: 0.78rem; padding: 0.22rem 0.6rem; border: 1px solid #c8bfaf; border-radius: 3px; background: transparent; color: #888; cursor: pointer; display: flex; align-items: center; gap: 0.25rem; }
.sort-btn.active { border-color: #2c2416; color: #2c2416; background: #f5f0e8; }
.sort-badge { display: inline-flex; align-items: center; justify-content: center; width: 14px; height: 14px; border-radius: 50%; background: #2c2416; color: #faf8f5; font-size: 0.6rem; font-weight: 600; line-height: 1; }
.sort-dir { font-size: 0.7rem; color: #aaa; margin-left: 1px; }
.view-toggle { display: flex; gap: 0.35rem; }
.view-btn { font-size: 0.78rem; padding: 0.25rem 0.65rem; border: 1px solid #c8bfaf; border-radius: 3px; background: transparent; color: #888; cursor: pointer; }
.view-btn.active { background: #2c2416; color: #faf8f5; border-color: #2c2416; }
.results-count { font-size: 0.8rem; color: #aaa; margin-bottom: 1rem; }
.imp-badge { font-size: 0.63rem; padding: 0.1rem 0.4rem; border-radius: 2rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; white-space: nowrap; }
.imp-core { background: #5a3a2a; color: #faf8f5; }
.imp-enriching { background: #2a5a48; color: #faf8f5; }
.imp-expert { background: #3a4a62; color: #faf8f5; }
.imp-filter { display: flex; gap: 0.35rem; flex-wrap: wrap; }
.imp-btn { font-size: 0.78rem; padding: 0.22rem 0.65rem; border: 1px solid #c8bfaf; border-radius: 3px; background: transparent; color: #888; cursor: pointer; }
.imp-btn.active.imp-core-btn  { background: #5a3a2a; color: #faf8f5; border-color: #5a3a2a; }
.imp-btn.active.imp-enrich-btn { background: #2a5a48; color: #faf8f5; border-color: #2a5a48; }
.imp-btn.active.imp-expert-btn { background: #3a4a62; color: #faf8f5; border-color: #3a4a62; }
.term-entry { border-top: 1px solid #e8e0d4; padding: 1.1rem 0; cursor: pointer; }
.term-entry:last-of-type { border-bottom: 1px solid #e8e0d4; }
.term-header { display: flex; align-items: baseline; flex-wrap: wrap; gap: 0.5rem; }
.term-title { font-size: 1.05rem; font-weight: 600; color: #2c2416; margin: 0; font-family: 'Playfair Display', Georgia, serif; }
.term-pronunciation { font-size: 0.8rem; color: #999; font-style: italic; }
.term-cats { display: flex; gap: 0.3rem; flex-wrap: wrap; margin-left: auto; }
.term-cat { font-size: 0.68rem; padding: 0.12rem 0.45rem; background: #f0ebe2; border-radius: 2rem; color: #5a4a30; text-transform: uppercase; letter-spacing: 0.04em; }
.term-short { margin: 0.35rem 0 0; font-size: 0.92rem; color: #444; }
.term-details { display: none; }
.term-details.open { display: block; }
.term-long { font-size: 0.88rem; color: #555; margin: 0.5rem 0 0.6rem; line-height: 1.65; }
.term-meta-row { display: flex; flex-wrap: wrap; gap: 1rem 2rem; font-size: 0.82rem; color: #777; margin-bottom: 0.5rem; }
.term-meta-row a { color: #5a4a30; }
.expand-hint { font-size: 0.72rem; color: #bbb; float: right; padding-top: 0.25rem; }
.no-results { font-size: 0.88rem; color: #aaa; font-style: italic; padding: 2rem 0; }
.condensed-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; display: none; }
.condensed-table.active { display: table; }
.condensed-table th { text-align: left; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.07em; color: #aaa; padding: 0.4rem 0.5rem; border-bottom: 1px solid #e8e0d4; font-weight: 400; }
.condensed-table td { padding: 0.55rem 0.5rem; border-bottom: 1px solid #f0ebe2; vertical-align: top; color: #2c2416; }
.condensed-table tr { cursor: pointer; }
.condensed-table tr:hover td { background: #faf6f0; }
.ct-term { font-weight: 600; font-family: 'Playfair Display', Georgia, serif; white-space: nowrap; padding-right: 1rem; }
.ct-def { color: #555; }
.condensed-expanded { display: none; background: #faf6f0; }
.condensed-expanded.open { display: table-row; }
.condensed-expanded td { padding: 0.75rem 0.5rem; border-bottom: 1px solid #e8e0d4; font-size: 0.86rem; }
</style>"""

CONTROLS = """\
<div class="gl-controls">
  <div class="gl-row">
    <span class="gl-label">Categories</span>
    <div class="cat-dropdown-wrap">
      <button class="cat-trigger" id="cat-trigger">All categories ▾</button>
      <div class="cat-panel" id="cat-panel">
        <label><input type="checkbox" id="cat-all" checked> All</label>
        <hr>
        <div id="cat-list"></div>
      </div>
    </div>
    <div class="logic-toggle">
      <span>Match:</span>
      <button class="logic-btn active" id="logic-or" data-logic="or">OR</button>
      <button class="logic-btn" id="logic-and" data-logic="and">AND</button>
    </div>
  </div>
  <div class="gl-row">
    <span class="gl-label">Importance</span>
    <div class="imp-filter">
      <button class="imp-btn imp-core-btn active" data-level="core">Core</button>
      <button class="imp-btn imp-enrich-btn active" data-level="enriching">Enriching</button>
      <button class="imp-btn imp-expert-btn active" data-level="expert">Expert</button>
    </div>
  </div>
  <div class="gl-row">
    <span class="gl-label">Sort</span>
    <div class="sort-row" id="sort-row">
      <button class="sort-btn" data-key="alpha">A–Z <span class="sort-dir">↑</span></button>
      <button class="sort-btn" data-key="category">Category <span class="sort-dir">↑</span></button>
      <button class="sort-btn" data-key="importance">Importance <span class="sort-dir">↑</span></button>
    </div>
  </div>
  <div class="gl-row">
    <span class="gl-label">View</span>
    <div class="view-toggle">
      <button class="view-btn active" id="view-full">Expanded</button>
      <button class="view-btn" id="view-expanded">Condensed</button>
      <button class="view-btn" id="view-condensed">Compact</button>
    </div>
  </div>
</div>

<div class="results-count" id="results-count"></div>"""

JS = """\
<script>
(function(){
  var terms = Array.from(document.querySelectorAll('.term-entry'));
  var catAllCb = document.getElementById('cat-all');
  var catChecks = [];
  var catTrigger = document.getElementById('cat-trigger');
  var catPanel = document.getElementById('cat-panel');
  var logicOr = document.getElementById('logic-or');
  var logicAnd = document.getElementById('logic-and');
  var noResults = document.getElementById('no-results');
  var resultsCount = document.getElementById('results-count');
  var expandedView = document.getElementById('expanded-view');
  var condensedView = document.getElementById('condensed-view');
  var condensedBody = document.getElementById('condensed-body');
  var viewExpanded = document.getElementById('view-expanded');
  var viewCondensed = document.getElementById('view-condensed');
  var viewFull = document.getElementById('view-full');
  var sortBtns = Array.from(document.querySelectorAll('.sort-btn'));

  (function buildCatList() {
    var catCounts = {};
    terms.forEach(function(t) {
      t.dataset.cats.split(' ').forEach(function(c) { catCounts[c] = (catCounts[c]||0)+1; });
    });
    var cats = Object.keys(catCounts).sort();
    var CAT_LABELS = {
      'roman-numeral':'Roman Numerals','italian':'Italian','harmony':'Harmony',
      'technology':'Technology','non-western':'Non-Western','vocal':'Vocal',
      'form':'Form','homograph':'Homograph','general':'General'
    };
    function toLabel(s){ return CAT_LABELS[s]||s.replace(/-/g,' ').replace(/^./,function(c){return c.toUpperCase();}); }
    var list = document.getElementById('cat-list');
    cats.forEach(function(cat){
      var label = document.createElement('label');
      label.innerHTML = '<input type="checkbox" class="cat-check" value="'+cat+'"> '
        +toLabel(cat)+' <span style="color:#aaa;font-size:0.78em;">('+catCounts[cat]+')</span>';
      list.appendChild(label);
    });
    catChecks = Array.from(document.querySelectorAll('.cat-check'));
    catChecks.forEach(function(c){
      c.addEventListener('change', function(){
        if(c.checked) catAllCb.checked=false;
        if(catChecks.every(function(x){return !x.checked;})) catAllCb.checked=true;
        applyFilters();
      });
    });
  })();

  var logic = 'or';
  var currentView = 'expanded';
  var sortStack = [];
  var impActive = {core:true,enriching:true,expert:true};
  var impOrder  = {core:1,enriching:2,expert:3};

  document.querySelectorAll('.imp-btn').forEach(function(btn){
    btn.addEventListener('click',function(){
      var level=btn.dataset.level;
      impActive[level]=!impActive[level];
      btn.classList.toggle('active',impActive[level]);
      applyFilters();
    });
  });

  function getTermValue(term,key){
    if(key==='alpha') return term.querySelector('.term-title').textContent.toLowerCase();
    if(key==='category') return term.dataset.cats.split(' ')[0];
    if(key==='importance') return String(impOrder[term.dataset.importance]||9);
    return '';
  }
  function sortedTerms(arr){
    if(!sortStack.length) return arr;
    return arr.slice().sort(function(a,b){
      for(var i=0;i<sortStack.length;i++){
        var s=sortStack[i]; var va=getTermValue(a,s.key); var vb=getTermValue(b,s.key);
        if(va<vb) return s.dir==='asc'?-1:1; if(va>vb) return s.dir==='asc'?1:-1;
      }
      return 0;
    });
  }
  function updateSortButtons(){
    sortBtns.forEach(function(btn){
      var key=btn.dataset.key; var idx=sortStack.findIndex(function(s){return s.key===key;});
      var dirSpan=btn.querySelector('.sort-dir'); var badge=btn.querySelector('.sort-badge');
      if(badge) btn.removeChild(badge);
      if(idx===-1){ btn.classList.remove('active'); dirSpan.textContent='↑'; dirSpan.style.color='#ddd'; }
      else{
        btn.classList.add('active'); dirSpan.textContent=sortStack[idx].dir==='asc'?'↑':'↓'; dirSpan.style.color='#2c2416';
        if(sortStack.length>1){ var b=document.createElement('span'); b.className='sort-badge'; b.textContent=idx+1; btn.insertBefore(b,btn.firstChild); }
      }
    });
  }
  sortBtns.forEach(function(btn){
    btn.addEventListener('click',function(){
      var key=btn.dataset.key; var idx=sortStack.findIndex(function(s){return s.key===key;});
      var def='asc';
      if(idx===-1){ sortStack.unshift({key:key,dir:def}); if(sortStack.length>4) sortStack.pop(); }
      else if(sortStack[idx].dir===def){ sortStack[idx].dir='desc'; var item=sortStack.splice(idx,1)[0]; sortStack.unshift(item); }
      else{ sortStack.splice(idx,1); }
      updateSortButtons(); applyFilters();
    });
  });

  catTrigger.addEventListener('click',function(e){ e.stopPropagation(); catPanel.classList.toggle('open'); });
  document.addEventListener('click',function(){ catPanel.classList.remove('open'); });
  catPanel.addEventListener('click',function(e){ e.stopPropagation(); });
  catAllCb.addEventListener('change',function(){ if(catAllCb.checked) catChecks.forEach(function(c){c.checked=false;}); applyFilters(); });
  [logicOr,logicAnd].forEach(function(btn){
    btn.addEventListener('click',function(){
      logic=btn.dataset.logic; logicOr.classList.toggle('active',logic==='or'); logicAnd.classList.toggle('active',logic==='and'); applyFilters();
    });
  });

  function setView(v){
    currentView=v;
    viewExpanded.classList.toggle('active',v==='expanded');
    viewCondensed.classList.toggle('active',v==='condensed');
    viewFull.classList.toggle('active',v==='compact');
    expandedView.style.display=(v==='condensed')?'none':'';
    condensedView.style.display=(v==='condensed')?'table':'none';
    condensedView.classList.toggle('active',v==='condensed');
    if(v==='compact'){ terms.forEach(function(t){ var d=t.querySelector('.term-details'); var h=t.querySelector('.expand-hint'); if(d) d.classList.add('open'); if(h) h.textContent='▾'; }); }
    else if(v==='expanded'){ terms.forEach(function(t){ var d=t.querySelector('.term-details'); var h=t.querySelector('.expand-hint'); if(d) d.classList.remove('open'); if(h) h.textContent='▸'; }); }
    applyFilters();
  }
  viewFull.addEventListener('click',function(){ setView('compact'); });
  viewExpanded.addEventListener('click',function(){ setView('expanded'); });
  viewCondensed.addEventListener('click',function(){ setView('condensed'); });

  terms.forEach(function(term){
    term.addEventListener('click',function(e){
      if(currentView==='compact') return;
      if(e.target.closest('select,a,input')) return;
      var details=term.querySelector('.term-details'); var hint=term.querySelector('.expand-hint');
      var open=details.classList.toggle('open'); if(hint) hint.textContent=open?'▾':'▸';
    });
  });

  function updateTriggerLabel(){
    var checked=catChecks.filter(function(c){return c.checked;}).map(function(c){return c.parentElement.textContent.trim();});
    catTrigger.textContent=checked.length===0?'All categories ▾':checked.length===1?checked[0]+' ▾':checked.length+' categories ▾';
  }
  function termVisible(term){
    var termCats=term.dataset.cats.split(' ');
    var selected=catChecks.filter(function(c){return c.checked;}).map(function(c){return c.value;});
    var catMatch;
    if(selected.length===0||catAllCb.checked){ catMatch=true; }
    else if(logic==='or'){ catMatch=selected.some(function(s){return termCats.indexOf(s)>-1;}); }
    else{ catMatch=selected.every(function(s){return termCats.indexOf(s)>-1;}); }
    var impLevel=term.dataset.importance||'enriching';
    return catMatch && impActive[impLevel]!==false;
  }
  function buildCondensed(visibleTerms){
    condensedBody.innerHTML='';
    visibleTerms.forEach(function(term){
      var titleEl=term.querySelector('.term-title'); var shortEl=term.querySelector('.term-short');
      if(!titleEl||!shortEl) return;
      var title=titleEl.textContent; var shortDef=shortEl.textContent;
      var cats=Array.from(term.querySelectorAll('.term-cat')).map(function(c){return c.textContent;}).join(', ');
      var longEl=term.querySelector('.term-long'); var long=longEl?longEl.innerHTML:'';
      var metaEl=term.querySelector('.term-meta-row'); var meta=metaEl?metaEl.outerHTML:'';
      var tr=document.createElement('tr');
      tr.innerHTML='<td class="ct-term">'+title+'</td><td class="ct-def">'+shortDef+'</td><td style="font-size:0.72rem;color:#888;white-space:nowrap;">'+cats+'</td>';
      var expTr=document.createElement('tr'); expTr.className='condensed-expanded';
      expTr.innerHTML='<td colspan="3"><p style="font-size:0.86rem;color:#555;margin:0 0 0.5rem;">'+long+'</p>'+meta+'</td>';
      tr.addEventListener('click',function(){ var wasOpen=expTr.classList.contains('open'); document.querySelectorAll('.condensed-expanded').forEach(function(r){r.classList.remove('open');}); if(!wasOpen) expTr.classList.add('open'); });
      condensedBody.appendChild(tr); condensedBody.appendChild(expTr);
    });
  }
  function applyFilters(){
    updateTriggerLabel();
    var visible=sortedTerms(terms.filter(function(t){return termVisible(t);}));
    var hiddenSet=terms.filter(function(t){return !termVisible(t);});
    var container=document.getElementById('expanded-view');
    visible.forEach(function(t){container.appendChild(t);}); hiddenSet.forEach(function(t){t.style.display='none';}); visible.forEach(function(t){t.style.display='';});
    noResults.style.display=visible.length===0?'':'none';
    resultsCount.textContent=visible.length===terms.length?terms.length+' terms':visible.length+' of '+terms.length+' terms';
    if(currentView==='condensed') buildCondensed(visible);
  }
  sortStack=[{key:'alpha',dir:'asc'}]; updateSortButtons(); setView('compact');
  if(window.location.hash){ var target=document.querySelector(window.location.hash); if(target) setTimeout(function(){ target.scrollIntoView({behavior:'smooth',block:'start'}); },80); }
})();
</script>"""

TABLE_HTML = """\

<table class="condensed-table" id="condensed-view">
  <thead>
    <tr>
      <th style="width:22%">Term</th>
      <th>Short definition</th>
      <th style="width:18%">Categories</th>
    </tr>
  </thead>
  <tbody id="condensed-body"></tbody>
</table>"""

def make_entry_html(e):
    slug      = e['slug']
    display   = html_lib.escape(e['display'])
    ipa       = html_lib.escape(e['ipa']) if e['ipa'] else ''
    def_short = html_lib.escape(e['def_short']) if e['def_short'] else ''
    cats_str  = ' '.join(e['cats'])
    imp       = e['importance']

    # Category badges
    cat_badges = ''.join('<span class="term-cat">%s</span>' % CAT_LABEL.get(c, c.replace('-',' ').title()) for c in e['cats'])
    imp_badge  = '<span class="imp-badge imp-%s">%s</span>' % (imp, imp.title())

    # Pronunciation
    pron_html = ('\n    <span class="term-pronunciation">[%s]</span>' % ipa) if ipa else ''

    # Sources
    sources_html = ''
    if e['sources']:
        links = ', '.join('<a href="%s" target="_blank">%d</a>' % (s, i+1) for i, s in enumerate(e['sources']))
        sources_html = '\n      <span>Sources: %s</span>' % links

    # See also
    seealso_html = ''
    if e['see_also_html']:
        seealso_html = '\n      <span>See also: %s</span>' % e['see_also_html']

    meta_content = (sources_html + seealso_html).strip()
    meta_block = ''
    if meta_content:
        meta_block = '\n    <div class="term-meta-row">%s\n    </div>' % (sources_html + seealso_html)

    body_block = ''
    if e['body_html']:
        body_block = '\n    <div class="term-long">%s</div>' % e['body_html']

    return """\
<div class="term-entry" data-cats="{cats}" data-importance="{imp}">
  <span class="expand-hint">▸</span>
  <div class="term-header">
    <h3 class="term-title" id="{slug}">{display}</h3>{pron}
    <div class="term-cats">{cat_badges}</div>
    {imp_badge}
  </div>
  <p class="term-short">{def_short}</p>
  <div class="term-details">{body}{meta}
  </div>
</div>""".format(
        cats=cats_str, imp=imp, slug=slug, display=display,
        pron=pron_html, cat_badges=cat_badges, imp_badge=imp_badge,
        def_short=def_short, body=body_block, meta=meta_block,
    )

QMD_HEADER = """\
---
title: "Music Glossary"
description: "IB Music key terms with definitions, IPA pronunciations, and categories."
categories: [Reference, Glossary]
---

```{=html}
""" + CSS + """

""" + CONTROLS + """

<div id="expanded-view">
"""

QMD_FOOTER = """\

<p class="no-results" id="no-results" style="display:none;">No terms match the current filters.</p>
</div>
""" + TABLE_HTML + """

```{=html}
""" + JS + """
```
"""

def write_qmd(entries, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(QMD_HEADER)
        # Roman numerals first (in their original order, not alphabetical)
        roman_entries = [e for e in entries if 'roman-numeral' in e['cats']]
        other_entries = [e for e in entries if 'roman-numeral' not in e['cats']]
        for e in roman_entries:
            f.write('\n<!-- ── Roman Numerals ── -->\n' if e == roman_entries[0] else '')
            f.write('\n' + make_entry_html(e) + '\n')
        for e in other_entries:
            f.write('\n' + make_entry_html(e) + '\n')
        f.write(QMD_FOOTER)
    print('Wrote %s (%d entries)' % (path, len(entries)))

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    entries = parse_org(ORG_FILE)
    print('Parsed %d entries from %s' % (len(entries), ORG_FILE))
    write_yml(entries, YML_OUT)
    write_qmd(entries, QMD_OUT)
    print('Done.')
