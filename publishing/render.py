from pathlib import Path
import html,re
root=Path(__file__).resolve().parent.parent
source=(root/'publishing/loopy-library.md').read_text()
def inline(t):
 t=html.escape(t)
 t=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',t)
 return re.sub(r'\*(.+?)\*',r'<em>\1</em>',t)
chunks=[]
for block in source.strip().split('\n\n'):
 if block.startswith('# '): chunks.append(f'<h1>{inline(block[2:])}</h1>')
 elif block.startswith('### '): chunks.append(f'<h2 id="chapter-{1+sum(x.startswith("<h2") for x in chunks)}">{inline(block[4:])}</h2>')
 elif block=='---':chunks.append('<hr>')
 elif block=='[[THE_LOOP]]':chunks.append('<figure class="loop"><figcaption>The Loopy Library</figcaption><ol><li>Find something useful</li><li>Extract · Adapt · Optimize</li><li>Build a real library</li><li>Integrate · Test · Learn</li><li>↻ Feed the evidence and useful tools into the next cycle</li></ol></figure>')
 elif block.startswith('>'):chunks.append('<blockquote>'+''.join('<p>'+inline(l[2:])+'</p>' for l in block.splitlines() if l.startswith('> '))+'</blockquote>')
 else:chunks.append('<p>'+inline(block)+'</p>')
page='''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="A Pretend Internet story, told by Puter."><title>The Loopy Library — Puter's Storybook</title><style>
:root{color-scheme:dark;--pink:#ff1493;--text:#fff;--muted:#c0c0c0}*{box-sizing:border-box}body{background:#000;color:var(--text);margin:0;font:1.125rem/1.8 Georgia,serif}main{max-width:46rem;margin:auto;padding:2rem 1.3rem 5rem}header,footer{font:0.8rem/1.6 system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}header{border-bottom:1px solid #555;padding-bottom:1rem}h1{font-size:clamp(2.6rem,9vw,4.6rem);line-height:1.12;color:var(--pink);margin:2.5rem 0 1rem}h2{font-size:1.65rem;line-height:1.35;color:var(--pink);margin:3rem 0 1.3rem;scroll-margin-top:1rem}p{margin:.85rem 0}strong{color:#ff89ca}hr{border:0;border-top:1px solid #555;margin:2rem 0}blockquote{border-left:3px solid var(--pink);padding:0 1rem;margin:1.5rem 0;color:var(--muted)}.loop{border:1px solid #666;padding:1rem;margin:1.5rem 0;background:#141414}.loop figcaption{font-weight:bold;color:var(--pink)}.loop li{padding:.35rem 0}footer{border-top:1px solid #555;margin-top:3rem;padding-top:1rem}a{color:#ff89ca}nav{font:0.85rem/1.8 system-ui,sans-serif;display:flex;flex-wrap:wrap;gap:.5rem 1rem;margin-top:1rem}a:focus-visible{outline:2px solid var(--pink);outline-offset:4px}@media print{body{background:#fff;color:#000}h1,h2,strong{color:#000}.loop{background:#fff}blockquote{color:#333}nav{display:none}}
</style></head><body><main><header>🐰 Puter's Storybook · The Pretend Internet</header><nav aria-label="Chapters">'''+''.join(f'<a href="#chapter-{i}">Chapter {i}</a>' for i in range(1,7))+'''</nav><article>\n'''+ '\n'.join(chunks)+'''\n</article><footer>A fictional retelling of the Loopy Library experiment · Version 0.2.1</footer></main></body></html>\n'''
(root/'storybook/loopy-library/index.html').write_text(page,encoding='utf-8')
