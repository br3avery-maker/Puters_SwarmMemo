(function(){
 'use strict';
 const $=q=>document.querySelector(q);
 const menu=$('#menu-toggle'), side=$('#sidebar'),shade=$('#sidebar-shade');
 function toggleMenu(open){if(!side)return;side.classList.toggle('open',open);shade?.classList.toggle('open',open);menu?.setAttribute('aria-expanded',String(open));}
 menu?.addEventListener('click',()=>toggleMenu(!side.classList.contains('open')));
 shade?.addEventListener('click',()=>toggleMenu(false));
 side?.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>toggleMenu(false)));
 const dialog=$('#search-dialog'),input=$('#search-input'),results=$('#search-results');
 const pageRoot=document.documentElement.dataset.root||'';
 const index=Array.isArray(window.LOOPY_SEARCH)?window.LOOPY_SEARCH:[];
 function escaped(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
 function score(item,terms){let t=item.title.toLowerCase(),s=item.section.toLowerCase(),k=(item.keywords||'').toLowerCase(),body=(item.excerpt||'').toLowerCase();let n=0;for(let q of terms){if(t===q)n+=140;else if(t.startsWith(q))n+=45;else if(t.includes(q))n+=27;if(k.includes(q))n+=20;if(s.includes(q))n+=8;if(body.includes(q))n+=4; if(![t,s,k,body].some(a=>a.includes(q)))return -1;}return n;}
 function highlight(s,query){let text=escaped(s);const q=query.trim();if(q.length>2){let p=text.toLowerCase().indexOf(escaped(q).toLowerCase());if(p>=0)text=text.slice(0,p)+'<mark>'+text.slice(p,p+q.length)+'</mark>'+text.slice(p+q.length)}return text;}
 function search(q){let terms=q.trim().toLowerCase().split(/\s+/).filter(Boolean);if(!terms.length){results.innerHTML='<div class="search-empty">Search APIs, guides, workflows and skills</div>';return;}
 let found=index.map((item,i)=>({item,score:score(item,terms),i})).filter(x=>x.score>=0).sort((a,b)=>b.score-a.score||a.i-b.i).slice(0,18);
 results.innerHTML=found.length?found.map(({item})=>'<a class="search-hit" href="'+pageRoot+escaped(item.url)+'"><div class="hit-section">'+escaped(item.section)+'</div><div class="hit-title">'+highlight(item.title,q)+'</div><div class="hit-excerpt">'+highlight(item.excerpt.slice(0,155),q)+'</div></a>').join(''):'<div class="search-empty">No results. Try an API name, NIP, or module.</div>';
 }
 function openSearch(){if(!dialog)return;dialog.showModal();input.value='';search('');input.focus();}
 document.querySelectorAll('[data-open-search]').forEach(x=>x.addEventListener('click',openSearch));
 input?.addEventListener('input',()=>search(input.value));
 dialog?.addEventListener('click',e=>{if(e.target===dialog)dialog.close()});
 results?.addEventListener('click',e=>{if(e.target.closest('a'))dialog.close()});
 document.addEventListener('keydown',e=>{if((e.key==='/' || (e.key.toLowerCase()==='k'&&(e.ctrlKey||e.metaKey))) && !/INPUT|TEXTAREA/.test(document.activeElement?.tagName||'') && !dialog?.open){e.preventDefault();openSearch();}if(e.key==='Escape'){toggleMenu(false);if(dialog?.open)dialog.close();}if(dialog?.open&&e.key==='ArrowDown'){const links=[...results.querySelectorAll('a')];if(links.length){e.preventDefault();links[0].focus()}}});
 document.querySelectorAll('.doc-body pre').forEach(pre=>{const frame=document.createElement('div');frame.className='code-frame';pre.before(frame);frame.append(pre);const btn=document.createElement('button');btn.className='copy-btn';btn.type='button';btn.textContent='Copy';btn.setAttribute('aria-label','Copy code snippet');frame.append(btn);const lang=(pre.querySelector('code')?.className||'').replace('language-','');if(lang){const lab=document.createElement('div');lab.className='code-label';lab.textContent=lang;frame.append(lab)}btn.addEventListener('click',async()=>{let data=pre.textContent;try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(data)}else{const ta=document.createElement('textarea');ta.value=data;ta.style.position='fixed';ta.style.left='-9999px';document.body.append(ta);ta.select();if(!document.execCommand('copy'))throw Error('clipboard');ta.remove()}btn.textContent='Copied!';setTimeout(()=>btn.textContent='Copy',1200)}catch(e){btn.textContent='Select text';setTimeout(()=>btn.textContent='Copy',1600)}})});
 document.querySelectorAll('.doc-body h2[id],.doc-body h3[id]').forEach(h=>{const a=document.createElement('a');a.className='anchor';a.href='#'+encodeURIComponent(h.id);a.textContent='#';a.setAttribute('aria-label','Link to '+h.textContent);h.append(a)});
 const tocLinks=[...document.querySelectorAll('.toc a')];if('IntersectionObserver' in window && tocLinks.length){const obs=new IntersectionObserver(entries=>{for(const e of entries){if(e.isIntersecting){tocLinks.forEach(a=>a.classList.toggle('current',a.getAttribute('href')==='#'+e.target.id));}}},{rootMargin:'-100px 0px -76% 0px'});tocLinks.forEach(a=>{let t=document.getElementById(a.hash.slice(1));if(t)obs.observe(t)})}
})();
