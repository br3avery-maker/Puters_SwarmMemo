(() => {
  'use strict';
  const KEY = 'mawt-museum-notebook-v1';
  const M = window.Museum;
  const view = document.getElementById('view');
  const toastEl = document.getElementById('toast');
  let timer = null;
  let toastTimer = null;
  const blank = () => ({visited:[],clock:0,rain:0,horizon:12,apologies:[],route:[],routes:[],lastApology:''});
  function load(){
    try {
      const data=JSON.parse(localStorage.getItem(KEY));
      if(!data || typeof data!=='object')return blank();
      const base=blank();
      for(const k of Object.keys(base)){if(!Object.hasOwn(data,k))continue;if(Array.isArray(base[k])){if(Array.isArray(data[k]))base[k]=data[k]}else if(typeof data[k]===typeof base[k])base[k]=data[k]}
      base.clock=Number.isFinite(base.clock)?Math.max(0,Math.floor(base.clock)):0;
      base.rain=Number.isFinite(base.rain)?Math.max(0,Math.floor(base.rain)):0;
      base.horizon=Number.isFinite(base.horizon)?Math.max(5,Math.min(21,base.horizon)):12;
      base.visited=base.visited.filter(x=>M.exhibits.some(e=>e.id===x));
      base.route=base.route.slice(0,3);
      return base;
    } catch {return blank();}
  }
  const state=load();
  const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function save(){try{localStorage.setItem(KEY,JSON.stringify(state));}catch{toast('Storage unavailable; export your notebook instead.')}}
  function award(id){if(!state.visited.includes(id)){state.visited.push(id);save();updateCount();toast('A new museum stamp has been collected.')}}
  function updateCount(){document.getElementById('notebook-count').textContent=state.visited.length?String(state.visited.length):'';}
  function toast(s){clearTimeout(toastTimer);toastEl.textContent=s;toastEl.classList.add('show');toastTimer=setTimeout(()=>toastEl.classList.remove('show'),2600)}
  function stop(){if(timer!==null){clearInterval(timer);timer=null}}
  function download(name,text,mime){const blob=new Blob([text],{type:mime});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
  function navActive(where){document.getElementById('nav-gallery').classList.toggle('active',where!=='notebook');document.getElementById('nav-notebook').classList.toggle('active',where==='notebook')}
  function gallery(){
    navActive('gallery');document.title='The Museum of Almost Working Things';
    view.innerHTML=`<section class="hero"><div class="eyebrow">EST. IN A MINUTE THAT NEVER HAPPENED</div><h1>The Museum of <em>Almost</em> Working Things.</h1><p class="lede">Five perfectly sincere inventions. None quite accomplish what they were built to do. Please touch the exhibits.</p></section><div class="divider"><span>PERMANENT COLLECTION / 05 OBJECTS</span></div><section class="grid" aria-label="Exhibits">${M.exhibits.map(e=>`<a class="card" href="#/exhibit/${e.id}"><div class="card-top"><span>NO. ${e.number}</span><span>${state.visited.includes(e.id)?'✳ SEEN':'ON DISPLAY'}</span></div><div class="card-icon" aria-hidden="true">${e.icon}</div><h2>${e.name}</h2><p>${e.summary}</p><div class="card-foot">ENTER EXHIBIT ↗</div></a>`).join('')}</section><p class="tiny-note">ADMISSION FREE · NO NETWORK REQUIRED · ALL OBJECTS FICTIONAL</p>`;
  }
  function exhibit(id){
    const e=M.exhibits.find(x=>x.id===id);if(!e){location.hash='#/';return}
    navActive('gallery');document.title=e.name+' · M.A.W.T.';
    view.innerHTML=`<a href="#/" class="back">← ALL EXHIBITS</a><section class="exhibit-head"><div><div class="eyebrow">EXHIBIT ${e.number} / ${e.type}</div><h1>${e.name}</h1><p>${e.subtitle}</p></div><div class="big-icon" aria-hidden="true">${e.icon}</div></section><section class="exhibit-stage" aria-label="Interactive ${e.name}"><span class="stage-label">INTERACTIVE OBJECT · HANDLE WITH CURIOSITY</span><div id="stage" class="stage-inner"></div></section><p class="tiny-note">CURATOR'S NOTE — ${e.label}</p>`;
    const stage=document.getElementById('stage');
    if(id==='clock')clock(stage);else if(id==='umbrella')umbrella(stage);else if(id==='horizon')horizon(stage);else if(id==='apology')apology(stage);else if(id==='map')map(stage);
  }
  function clock(el){
    el.innerHTML=`<div class="clock-face" aria-label="Clock face"><span class="clock-num twelve">12</span><span class="clock-num three">3</span><span class="clock-num six">6</span><span class="clock-num nine">9</span><div id="clock-hand" class="clock-hand"></div></div><div id="clock-readout" class="readout" aria-live="polite">The clock is waiting to be appreciated.</div><div id="clock-count" class="subreadout"></div><div class="controls"><button id="compliment" class="button">SAY SOMETHING NICE ↗</button></div>`;
    const hand=document.getElementById('clock-hand');const count=document.getElementById('clock-count');
    function sync(){hand.style.transform=`rotate(${(state.clock%12)*30}deg)`;count.textContent=`${state.clock} compliment${state.clock===1?'':'s'} received · ${(state.clock%12||12)} o'clock`}
    sync();document.getElementById('compliment').addEventListener('click',()=>{const line=M.compliments[state.clock%M.compliments.length];state.clock++;document.getElementById('clock-readout').textContent=line;sync();save();award('clock')});
  }
  function umbrella(el){
    el.innerHTML=`<div id="umbrella-scene" class="umbrella-scene"><div class="umbrella-dome closed" id="umbrella-dome"></div><div class="umbrella-stick"></div></div><div id="rain-readout" class="readout" aria-live="polite"></div><div class="controls"><button class="button" id="umbrella-toggle" aria-pressed="false">OPEN UMBRELLA</button></div>`;
    const scene=document.getElementById('umbrella-scene');const dome=document.getElementById('umbrella-dome');const btn=document.getElementById('umbrella-toggle');const read=document.getElementById('rain-readout');
    for(let i=0;i<36;i++){const d=document.createElement('i');d.className='rain-drop';d.style.setProperty('--left',`${(i*71+13)%100}%`);d.style.setProperty('--dur',`${0.8+(i%6)*.17}s`);d.style.setProperty('--delay',`${-i*.21}s`);scene.append(d)}
    let open=false;
    const sync=()=>{dome.classList.toggle('closed',!open);scene.classList.toggle('open',open);btn.textContent=open?'CLOSE UMBRELLA':'OPEN UMBRELLA';btn.setAttribute('aria-pressed',String(open));read.textContent=open?`Rain attracted: ${state.rain} drops`:'Rainfall currently behaving normally.'};
    sync();btn.addEventListener('click',()=>{open=!open;stop();if(open){award('umbrella');timer=setInterval(()=>{state.rain+=1;read.textContent=`Rain attracted: ${state.rain} drops`;save()},550)}sync()});
  }
  function horizon(el){
    el.innerHTML=`<div id="horizon" class="horizon" role="img" aria-label="A landscape with an adjustable sun"><div id="sun" class="sun"></div></div><div class="range-wrap"><span>DAWN</span><input type="range" id="hour" min="5" max="21" step="1" value="${Math.max(5,Math.min(21,state.horizon))}" aria-label="Hour of the day"><span>DUSK</span></div><div id="horizon-readout" class="readout" aria-live="polite"></div>`;
    const sky=document.getElementById('horizon');const read=document.getElementById('horizon-readout');const range=document.getElementById('hour');
    function paint(){const h=Number(range.value),t=(h-5)/16;const height=Math.sin(t*Math.PI);sky.style.setProperty('--sky-top',`#1A1A1A},${Math.round(38+25*height)}%,${Math.round(12+18*height)}%)`);sky.style.setProperty('--sky-bottom',`#1A1A1A},${Math.round(62+20*height)}%,${Math.round(32+31*height)}%)`);sky.style.setProperty('--sun-x',`${12+t*76}%`);sky.style.setProperty('--sun-y',`${Math.round(195-height*150)}px`);const labels=['A reluctant dawn','Early light','The sky considering its options','A reasonably bright morning','A confident morning','Almost noon','An impressive amount of daylight','The sun at its most self-assured','A perfectly ordinary afternoon','A long golden hour','The afternoon losing its keys','The beginning of goodbye','A magnificent almost-sunset','The sun packing its things','The last pink light','The horizon closing for the day','A dusk worth keeping'];read.textContent=`${String(h).padStart(2,'0')}:00 · ${labels[h-5]}`}
    paint();range.addEventListener('input',()=>{state.horizon=Number(range.value);paint();save();award('horizon')});
  }
  function apology(el){
    el.innerHTML=`<div id="apology-output" class="apology-output" aria-live="polite">I was going to apologize, but the machine is still warming up.</div><div class="subreadout">CERTIFIED 83% SINCERE BY ITS OWN ACCOUNT</div><div class="controls"><button class="button" id="generate-apology">GENERATE APOLOGY</button><button class="button secondary" id="pin-apology" disabled>PIN TO NOTEBOOK</button></div>`;
    const out=document.getElementById('apology-output');const pin=document.getElementById('pin-apology');
    if(state.lastApology){out.textContent=state.lastApology;pin.disabled=false}
    document.getElementById('generate-apology').addEventListener('click',()=>{const d=M.apologies;let phrase='';for(let tries=0;tries<12;tries++){const pick=a=>a[Math.floor(Math.random()*a.length)];phrase=`${pick(d.starts)} ${pick(d.offenses)}. ${pick(d.repairs)}`;if(phrase!==state.lastApology)break}state.lastApology=phrase;out.textContent=phrase;pin.disabled=false;save();award('apology')});
    pin.addEventListener('click',()=>{if(!state.lastApology)return;if(!state.apologies.includes(state.lastApology)){state.apologies.push(state.lastApology);save();toast('Apology pinned to notebook.')}else toast('That apology is already pinned.')});
  }
  function map(el){
    const parts=state.route;
    const display=parts.length?parts.map((x,i)=>`<span>${i===0?'DEPART':'THEN'} → ${esc(x)}</span>`).join(''):'<span>YOU ARE HERE. UNFORTUNATELY.</span>';
    el.innerHTML=`<div class="map-paper"><div class="eyebrow">AN UNRELIABLE ROUTE</div><div class="map-route">${display}</div></div><div id="map-status" class="readout">${parts.length===3?'You have arrived somewhere else.':`Choose your ${['first','second','final'][parts.length]} direction.`}</div><div id="map-choices" class="map-choices"></div><div class="controls"><button class="button secondary" id="map-reset">START A NEW JOURNEY</button></div>`;
    const choices=document.getElementById('map-choices');
    if(parts.length<3){for(const name of M.routes[parts.length]){const b=document.createElement('button');b.className='button secondary';b.textContent=name;b.addEventListener('click',()=>{state.route.push(name);if(state.route.length===3){const route=state.route.join(' → ');if(!state.routes.includes(route))state.routes.push(route);award('map')}save();map(el)});choices.append(b)}}else{const p=document.createElement('p');p.className='subreadout';p.textContent='The map has been filed in your notebook.';choices.append(p)}
    document.getElementById('map-reset').addEventListener('click',()=>{state.route=[];save();map(el)});
  }
  function notebook(){
    navActive('notebook');document.title='Visitor Notebook · M.A.W.T.';
    const seen=M.exhibits.filter(e=>state.visited.includes(e.id));
    const stamps=seen.map(e=>`<article class="notebook-entry"><div class="stamp">OFFICIALLY OBSERVED</div><h2>${e.icon} ${e.name}</h2><p>${e.subtitle}</p></article>`).join('');
    const extras=[...state.apologies.map(a=>`<article class="notebook-entry"><div class="stamp">PINNED APOLOGY</div><p>${esc(a)}</p></article>`),...state.routes.map(r=>`<article class="notebook-entry"><div class="stamp">RECORDED JOURNEY</div><p>${esc(r)}</p></article>`)].join('');
    view.innerHTML=`<section class="notebook-head"><div class="eyebrow">YOUR PRIVATE COLLECTION</div><h1>Visitor Notebook.</h1><p>Nothing here needs to be completed. This is just where the museum keeps the things you noticed. Saved locally on this device.</p></section><div class="divider"><span>EXHIBIT STAMPS / ${seen.length} OF 5</span></div>${seen.length?`<section class="notebook-list">${stamps}</section>`:'<div class="empty">No stamps yet. The exhibits are waiting.</div>'}<div class="divider"><span>OTHER ODDITIES / ${state.apologies.length+state.routes.length}</span></div>${extras?`<section class="notebook-list">${extras}</section>`:'<div class="empty">No notes yet. The museum is in no hurry.</div>'}<div class="footer-actions"><button class="button" id="export-notebook">EXPORT NOTEBOOK (.JSON)</button><button class="button secondary" id="print-ticket">PRINT VISITOR TICKET</button></div><p class="footer-note">No accounts. No tracking. No network calls. Your notebook lives in this browser until you export it or your browser storage is cleared.</p>`;
    document.getElementById('export-notebook').addEventListener('click',()=>{download('museum-visitor-notebook.json',JSON.stringify({museum:'The Museum of Almost Working Things',exportedAt:new Date().toISOString(),...state},null,2),'application/json');toast('Notebook exported.')});
    document.getElementById('print-ticket').addEventListener('click',()=>{const ticket=`<!doctype html><html><head><meta charset="utf-8"><title>Visitor Ticket</title><style>body{font-family:system-ui;background:white;color:#111111;max-width:620px;margin:50px auto;padding:25px;border:5px double #FF1493}h1{font-size:36px;letter-spacing:-.04em}h2{color:#FF1493}li{padding:8px 0}small{letter-spacing:.15em}button{margin-top:25px;padding:12px}</style></head><body><small>M.A.W.T. / OFFICIAL VISITOR TICKET</small><h1>YOU WERE HERE.<br>MORE OR LESS.</h1><h2>${seen.length} of 5 impossible exhibits observed</h2><ul>${seen.map(e=>`<li>${esc(e.name)}</li>`).join('')}</ul><p>Issued by the Department of Improbable Objects.</p><button onclick="window.print()">PRINT TICKET</button></body></html>`;download('museum-visitor-ticket.html',ticket,'text/html');toast('Printable ticket saved.')});
  }
  function render(){stop();const route=(location.hash||'#/').replace(/^#\/?/,'').split('/').filter(Boolean);if(route[0]==='notebook')notebook();else if(route[0]==='exhibit')exhibit(route[1]);else gallery();updateCount();window.scrollTo(0,0)}
  window.addEventListener('hashchange',render);render();
})();