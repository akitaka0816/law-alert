import html
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import feedparser
import requests
from bs4 import BeautifulSoup


APP_NAME = "Law Alert"
DEFAULT_UA = "law-alert/1.0 (+local)"
HISTORY_MAX = 500  # history.json に保持する最大件数

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Law Alert — 法改正情報データベース</title>
  <style>
    *,*::before,*::after{box-sizing:border-box;}
    body{margin:0;font-family:'Helvetica Neue',Arial,'Hiragino Kaku Gothic ProN','Meiryo',sans-serif;background:#f0f4f8;color:#2d3748;}
    .hd{background:#1a365d;color:#fff;padding:1.2rem 2rem;}
    .hd h1{margin:0;font-size:1.4rem;font-weight:700;}
    .hd .sub{font-size:.8rem;opacity:.75;margin:.2rem 0 0;}
    .hd .stats{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.8rem;}
    .stat{background:rgba(255,255,255,.15);border-radius:5px;padding:.2rem .65rem;font-size:.78rem;}
    .stat-kw{background:rgba(217,119,6,.4);}
    .filters{background:#fff;border-bottom:2px solid #e2e8f0;padding:.75rem 2rem;position:sticky;top:0;z-index:100;}
    .frow{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin-bottom:.45rem;}
    .frow:last-child{margin-bottom:0;}
    .si{flex:1;min-width:180px;padding:.42rem .9rem;border:1.5px solid #cbd5e0;border-radius:20px;font-size:.88rem;outline:none;}
    .si:focus{border-color:#4299e1;box-shadow:0 0 0 3px rgba(66,153,225,.2);}
    .tog{display:flex;align-items:center;gap:.3rem;cursor:pointer;font-size:.82rem;color:#4a5568;white-space:nowrap;}
    .tog input{accent-color:#d97706;}
    .dr{display:flex;align-items:center;gap:.3rem;font-size:.82rem;color:#4a5568;}
    .dr input{padding:.32rem .6rem;border:1.5px solid #cbd5e0;border-radius:6px;font-size:.82rem;outline:none;}
    .dr input:focus{border-color:#4299e1;}
    select.ss{padding:.32rem .6rem;border:1.5px solid #cbd5e0;border-radius:6px;font-size:.82rem;background:#fff;outline:none;cursor:pointer;}
    .src-row{display:flex;flex-wrap:wrap;gap:.3rem;align-items:center;}
    .src-lbl{font-size:.74rem;color:#718096;white-space:nowrap;margin-right:.1rem;}
    label.scb{display:flex;align-items:center;gap:.2rem;cursor:pointer;font-size:.73rem;background:#f7fafc;border:1px solid #e2e8f0;border-radius:4px;padding:.12rem .45rem;white-space:nowrap;transition:all .1s;}
    label.scb:hover,label.scb.on{background:#ebf8ff;border-color:#90cdf4;color:#2b6cb0;}
    label.scb input{accent-color:#2b6cb0;}
    .sbtn{padding:.18rem .5rem;font-size:.7rem;border:1px solid #cbd5e0;border-radius:4px;background:#fff;cursor:pointer;color:#4a5568;}
    .sbtn:hover{background:#f7fafc;}
    .qb{padding:.22rem .55rem;font-size:.72rem;border:1px solid #cbd5e0;border-radius:4px;background:#fff;cursor:pointer;color:#4a5568;white-space:nowrap;}
    .qb:hover{background:#ebf8ff;border-color:#90cdf4;color:#2b6cb0;}
    .qb.act{background:#2b6cb0;color:#fff;border-color:#2b6cb0;}
    .rbar{max-width:900px;margin:.7rem auto 0;padding:0 1rem;display:flex;align-items:center;justify-content:space-between;gap:.5rem;}
    .rcnt{font-size:.84rem;color:#4a5568;}
    .rcnt strong{color:#2d3748;}
    .ebtn{padding:.28rem .75rem;background:#2b6cb0;color:#fff;border:none;border-radius:6px;font-size:.78rem;cursor:pointer;}
    .ebtn:hover{background:#2c5282;}
    .wrap{max-width:900px;margin:.5rem auto 0;padding:0 1rem 3rem;}
    .card{background:#fff;border-radius:8px;padding:.9rem 1.2rem;margin-bottom:.55rem;border:1px solid #e2e8f0;border-left:4px solid #cbd5e0;}
    .card:hover{box-shadow:0 2px 10px rgba(0,0,0,.06);}
    .card.matched{border-left-color:#d97706;background:#fffbeb;}
    .chd{display:flex;flex-wrap:wrap;gap:.3rem;align-items:center;margin-bottom:.35rem;}
    .bsrc{font-size:.7rem;background:#ebf8ff;color:#2b6cb0;border-radius:4px;padding:.1rem .45rem;font-weight:600;}
    .bkw{font-size:.7rem;background:#fef3c7;color:#92400e;border-radius:4px;padding:.1rem .45rem;font-weight:600;}
    .ctitle a{color:#2d3748;text-decoration:none;font-size:.92rem;font-weight:500;line-height:1.5;}
    .ctitle a:hover{color:#2b6cb0;text-decoration:underline;}
    .cmeta{margin-top:.35rem;font-size:.72rem;color:#718096;display:flex;flex-wrap:wrap;gap:.8rem;}
    .pgr{display:flex;justify-content:center;gap:.3rem;margin:1.2rem 0 2rem;flex-wrap:wrap;}
    .pb{padding:.28rem .65rem;border:1px solid #cbd5e0;border-radius:5px;background:#fff;cursor:pointer;font-size:.8rem;color:#4a5568;}
    .pb:hover{background:#ebf8ff;border-color:#90cdf4;}
    .pb.act{background:#2b6cb0;color:#fff;border-color:#2b6cb0;cursor:default;}
    .pb:disabled{opacity:.4;cursor:default;}
    .msg{text-align:center;padding:3rem 1rem;color:#718096;}
    @media(max-width:640px){.hd,.filters{padding-left:1rem;padding-right:1rem;}}
  </style>
</head>
<body>
<div class="hd">
  <h1>Law Alert — 法改正情報データベース</h1>
  <p class="sub">法改正・官報・パブリックコメント 自動収集</p>
  <div class="stats">
    <span class="stat" id="st-total">読み込み中...</span>
    <span class="stat stat-kw" id="st-kw"></span>
    <span class="stat" id="st-upd"></span>
  </div>
</div>
<div class="filters">
  <div class="frow">
    <input type="text" class="si" id="q" placeholder="タイトルで検索..." oninput="deb()">
    <label class="tog"><input type="checkbox" id="kwOnly" onchange="af()"> ★ キーワード一致のみ</label>
    <div class="dr">
      <span>期間</span>
      <input type="date" id="df" onchange="sp(null);af()">
      <span>〜</span>
      <input type="date" id="dt" onchange="sp(null);af()">
      <button class="qb" id="qb-0" onclick="pr(0)">今日</button>
      <button class="qb" id="qb-w" onclick="pr('w')">今週</button>
      <button class="qb" id="qb-m" onclick="pr('m')">今月</button>
      <button class="qb" id="qb-30" onclick="pr(30)">30日</button>
      <button class="qb" id="qb-x" onclick="pr('x')">✕ クリア</button>
    </div>
    <select class="ss" id="sb" onchange="af()">
      <option value="newest">新着順</option>
      <option value="oldest">古い順</option>
      <option value="source">ソース順</option>
    </select>
  </div>
  <div class="frow src-row" id="srcRow">
    <span class="src-lbl">ソース:</span>
    <button class="sbtn" onclick="ta(true)">全選択</button>
    <button class="sbtn" onclick="ta(false)">全解除</button>
  </div>
</div>
<div class="rbar">
  <span class="rcnt" id="rcnt"></span>
  <button class="ebtn" onclick="csv()">CSVダウンロード</button>
</div>
<div class="wrap">
  <div id="cards"><p class="msg">データを読み込み中...</p></div>
  <div class="pgr" id="pgr"></div>
</div>
<script>
var PG=30,all=[],fil=[],cur=1,dbt=null;
function deb(){clearTimeout(dbt);dbt=setTimeout(af,250);}
async function init(){
  try{
    var r=await fetch('./history.json');
    if(!r.ok)throw new Error('history.json が見つかりません');
    var d=await r.json();
    all=d.items||[];
    var kw=all.filter(function(i){return i.matched;}).length;
    document.getElementById('st-total').textContent='総件数: '+all.length+' 件';
    document.getElementById('st-kw').textContent='★ キーワード一致: '+kw+' 件';
    document.getElementById('st-upd').textContent='最終更新: '+(d.last_updated||'不明');
    var srcs=[...new Set(all.map(function(i){return i.source_name;}))];
    var row=document.getElementById('srcRow');
    srcs.forEach(function(sn){
      var l=document.createElement('label');
      l.className='scb on';
      l.innerHTML='<input type="checkbox" class="sci" value="'+e(sn)+'" checked onchange="af()"> '+e(sn);
      row.appendChild(l);
    });
    af();
  }catch(err){
    document.getElementById('cards').innerHTML='<p class="msg">読み込み失敗: '+err.message+'</p>';
  }
}
function af(){
  var q=document.getElementById('q').value.trim().toLowerCase();
  var kw=document.getElementById('kwOnly').checked;
  var df=document.getElementById('df').value;
  var dt=document.getElementById('dt').value;
  var sb=document.getElementById('sb').value;
  var ck=new Set(Array.from(document.querySelectorAll('.sci:checked')).map(function(c){return c.value;}));
  document.querySelectorAll('label.scb').forEach(function(l){
    l.classList.toggle('on',l.querySelector('input').checked);
  });
  fil=all.filter(function(i){
    if(q&&i.title.toLowerCase().indexOf(q)===-1)return false;
    if(kw&&!i.matched)return false;
    if(ck.size>0&&!ck.has(i.source_name))return false;
    var dt2=(i.detected_at||'').slice(0,10);
    if(df&&dt2<df)return false;
    if(dt&&dt2>dt)return false;
    return true;
  });
  if(sb==='newest')fil.sort(function(a,b){return(b.detected_at||'').localeCompare(a.detected_at||'');});
  else if(sb==='oldest')fil.sort(function(a,b){return(a.detected_at||'').localeCompare(b.detected_at||'');});
  else fil.sort(function(a,b){return a.source_name.localeCompare(b.source_name);});
  cur=1;render();
}
function render(){
  var tot=fil.length,pgs=Math.ceil(tot/PG)||1;
  if(cur>pgs)cur=pgs;
  document.getElementById('rcnt').innerHTML='<strong>'+tot+'</strong> 件ヒット';
  var sl=fil.slice((cur-1)*PG,cur*PG);
  var ce=document.getElementById('cards');
  if(sl.length===0){ce.innerHTML='<p class="msg">該当する項目がありません。</p>';document.getElementById('pgr').innerHTML='';return;}
  ce.innerHTML=sl.map(function(i){
    var kw=i.matched?'<span class="bkw">★ キーワード一致</span>':'';
    var cls=i.matched?'card matched':'card';
    var pub=i.published?'<span>公開: '+e(i.published)+'</span>':'';
    return '<div class="'+cls+'"><div class="chd"><span class="bsrc">'+e(i.source_name)+'</span>'+kw+'</div>'+
      '<div class="ctitle"><a href="'+e(i.link)+'" target="_blank" rel="noopener">'+e(i.title)+'</a></div>'+
      '<div class="cmeta">'+pub+'<span>検知: '+e(i.detected_at||'')+'</span></div></div>';
  }).join('');
  var pr=document.getElementById('pgr');
  if(pgs<=1){pr.innerHTML='';return;}
  var b='<button class="pb" onclick="gp('+(cur-1)+')" '+(cur<=1?'disabled':'')+'>‹</button>';
  pgRange(cur,pgs).forEach(function(p){
    if(p==='…')b+='<span style="padding:.3rem .4rem;color:#a0aec0">…</span>';
    else b+='<button class="pb'+(p===cur?' act':'')+'" onclick="gp('+p+')">'+ p+'</button>';
  });
  b+='<button class="pb" onclick="gp('+(cur+1)+')" '+(cur>=pgs?'disabled':'')+'>›</button>';
  pr.innerHTML=b;
}
function pgRange(c,t){
  if(t<=7)return Array.from({length:t},function(_,i){return i+1;});
  var r=[1];
  if(c>3)r.push('…');
  for(var p=Math.max(2,c-1);p<=Math.min(t-1,c+1);p++)r.push(p);
  if(c<t-2)r.push('…');
  r.push(t);return r;
}
function gp(p){var pgs=Math.ceil(fil.length/PG)||1;if(p<1||p>pgs)return;cur=p;render();window.scrollTo({top:0,behavior:'smooth'});}
function ta(v){document.querySelectorAll('.sci').forEach(function(c){c.checked=v;});af();}
function csv(){
  if(!fil.length)return;
  var hd=['タイトル','リンク','ソース','公開日時','検知日時','キーワード一致'];
  var rows=fil.map(function(i){return[i.title,i.link,i.source_name,i.published||'',i.detected_at||'',i.matched?'○':''];});
  var body=[hd].concat(rows).map(function(r){return r.map(function(v){return'"'+String(v).replace(/"/g,'""')+'"';}).join(',');}).join('\r\n');
  var blob=new Blob(['\uFEFF'+body],{type:'text/csv;charset=utf-8;'});
  var a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download='law-alert-'+new Date().toISOString().slice(0,10)+'.csv';
  a.click();
}
function fmt(d){var y=d.getFullYear(),m=String(d.getMonth()+1).padStart(2,'0'),dd=String(d.getDate()).padStart(2,'0');return y+'-'+m+'-'+dd;}
function sp(id){['0','w','m','30','x'].forEach(function(k){var b=document.getElementById('qb-'+k);if(b)b.classList.toggle('act',k===id);});}
function pr(key){
  var td=new Date(),to=fmt(td),from;
  if(key==='x'){document.getElementById('df').value='';document.getElementById('dt').value='';sp(null);af();return;}
  if(key===0){from=to;}
  else if(key==='w'){var d=new Date(td),day=d.getDay(),diff=day===0?6:day-1;d.setDate(d.getDate()-diff);from=fmt(d);}
  else if(key==='m'){from=fmt(new Date(td.getFullYear(),td.getMonth(),1));}
  else{var d=new Date(td);d.setDate(d.getDate()-key+1);from=fmt(d);}
  document.getElementById('df').value=from;
  document.getElementById('dt').value=to;
  sp(String(key));af();
}
function e(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
init();
</script>
</body>
</html>
"""


@dataclass
class Item:
    source_id: str
    source_name: str
    item_id: str
    title: str
    link: str
    published: Optional[str] = None


def _save_history(
    history_path: str,
    new_items: List[Item],
    matched_ids: set,
    max_items: int = HISTORY_MAX,
) -> None:
    data = _load_json(history_path, {"items": [], "last_updated": ""})
    existing: List[Dict[str, Any]] = data.get("items", [])
    existing_ids = {r["item_id"] for r in existing}
    now = _now_local_str()

    new_records = [
        {
            "source_id": it.source_id,
            "source_name": it.source_name,
            "item_id": it.item_id,
            "title": it.title,
            "link": it.link,
            "published": it.published,
            "detected_at": now,
            "matched": it.item_id in matched_ids,
        }
        for it in new_items
        if it.item_id not in existing_ids
    ]

    combined = new_records + existing
    data["items"] = combined[:max_items]
    data["last_updated"] = now
    _save_json(history_path, data)


def _generate_html(html_path: str) -> None:
    """静的HTMLシェルを生成する。データはブラウザがhistory.jsonをfetchして表示する。"""
    tmp = html_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(_HTML_TEMPLATE)
    os.replace(tmp, html_path)


def _load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def _save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _compile_keywords(keywords: List[str]) -> re.Pattern:
    escaped = [re.escape(k.strip()) for k in keywords if k and k.strip()]
    if not escaped:
        return re.compile(r"^$")  # matches nothing
    return re.compile("|".join(escaped), re.IGNORECASE)


def _now_local_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _toast(title: str, message: str) -> None:
    # トーストは見落としが起きやすいので、必ずログにも残す
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toast.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{_now_local_str()}] {title}\n{message}\n{'-'*60}\n")
    except Exception:
        # ログ失敗は通知本体を止めない（理由だけ表示）
        print(f"[toast.log write failed] {title}")

    # Windows toast via winotify; fallback to stdout.
    try:
        from winotify import Notification, audio  # type: ignore

        n = Notification(app_id=APP_NAME, title=title, msg=message, duration="short")
        n.set_audio(audio.Default, loop=False)
        n.show()
    except Exception:
        print(f"[{_now_local_str()}] {title}\n{message}\n")


def _request_get(url: str, timeout_s: int = 25) -> requests.Response:
    return requests.get(
        url,
        timeout=timeout_s,
        headers={"User-Agent": DEFAULT_UA, "Accept": "*/*"},
    )


def fetch_rss(source_id: str, source_name: str, url: str, max_items: int) -> List[Item]:
    resp = _request_get(url)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)

    items: List[Item] = []
    for e in feed.entries[:max_items]:
        title = (getattr(e, "title", "") or "").strip()
        link = (getattr(e, "link", "") or "").strip()
        published = (getattr(e, "published", None) or getattr(e, "updated", None) or None)
        raw_id = (getattr(e, "id", "") or "").strip()
        if not raw_id:
            raw_id = f"{link}::{published or ''}::{title}"
        item_id = raw_id

        if not title and not link:
            continue
        items.append(
            Item(
                source_id=source_id,
                source_name=source_name,
                item_id=item_id,
                title=title or "(no title)",
                link=link or url,
                published=published,
            )
        )
    return items


def fetch_html_links(
    source_id: str,
    source_name: str,
    url: str,
    max_items: int,
    selector: str = "a",
    base_url: str = "",
) -> List[Item]:
    """汎用HTMLリンク取得：指定セレクタに一致する<a>タグを収集する"""
    resp = _request_get(url)
    resp.raise_for_status()
    # resp.content（バイナリ）を渡すことでBS4がmetaタグからエンコーディングを自動検出する
    soup = BeautifulSoup(resp.content, "lxml")

    seen: set = set()
    items: List[Item] = []
    for a in soup.select(selector):
        href = (a.get("href", "") or "").strip()
        title = a.get_text(" ", strip=True)
        if not href or not title:
            continue
        if href.startswith("/"):
            href = base_url.rstrip("/") + href
        elif not href.startswith("http"):
            continue
        key = f"{href}::{title}"
        if key in seen:
            continue
        seen.add(key)
        items.append(
            Item(
                source_id=source_id,
                source_name=source_name,
                item_id=key,
                title=title,
                link=href,
            )
        )
        if len(items) >= max_items:
            break
    return items


def fetch_egov_law_updates_html(source_id: str, source_name: str, url: str, max_items: int) -> List[Item]:
    # Scrape titles/links from https://elaws.e-gov.go.jp/update/
    resp = _request_get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    anchors = soup.select("a[href^='/law/']")
    seen: set = set()
    items: List[Item] = []

    for a in anchors:
        href = a.get("href", "").strip()
        title = a.get_text(" ", strip=True)
        if not href or not title:
            continue
        full = f"https://elaws.e-gov.go.jp{href}"
        key = f"{full}::{title}"
        if key in seen:
            continue
        seen.add(key)
        items.append(
            Item(
                source_id=source_id,
                source_name=source_name,
                item_id=key,
                title=title,
                link=full,
            )
        )
        if len(items) >= max_items:
            break

    return items


def _truncate_lines(text: str, max_lines: int) -> str:
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines] + [f"...（他{len(lines) - max_lines}件）"])


def main() -> int:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "config.json")
    state_path = os.path.join(base_dir, "state.json")
    history_path = os.path.join(base_dir, "history.json")
    html_path = os.path.join(base_dir, "index.html")

    config = _load_json(config_path, {})
    run_cfg = config.get("run", {})
    sources = config.get("sources", [])
    keywords = config.get("keywords", [])

    max_items = int(run_cfg.get("max_items_per_source", 30))
    max_toast_lines = int(run_cfg.get("max_toast_lines", 6))
    notify_on_no_updates = bool(run_cfg.get("notify_on_no_updates", True))

    kw_re = _compile_keywords(keywords)

    state: Dict[str, Any] = _load_json(state_path, {})
    seen_by_source: Dict[str, List[str]] = state.get("seen_ids_by_source", {})
    if not isinstance(seen_by_source, dict):
        seen_by_source = {}

    errors: List[str] = []
    new_items_all: List[Item] = []
    new_items_matched: List[Item] = []

    for src in sources:
        if not src.get("enabled", True):
            continue
        sid = str(src.get("id", "")).strip()
        stype = str(src.get("type", "")).strip()
        name = str(src.get("name", sid)).strip() or sid
        url = str(src.get("url", "")).strip()
        if not sid or not stype or not url:
            continue

        try:
            if stype == "rss":
                items = fetch_rss(sid, name, url, max_items=max_items)
            elif stype == "html" and sid == "egov_law_updates":
                items = fetch_egov_law_updates_html(sid, name, url, max_items=max_items)
            elif stype == "html_links":
                selector = str(src.get("selector", "a")).strip() or "a"
                base_url = str(src.get("base_url", "")).strip()
                expanded_url = url.replace("{year}", str(datetime.now().year))
                items = fetch_html_links(sid, name, expanded_url, max_items=max_items, selector=selector, base_url=base_url)
            else:
                continue
        except Exception as e:
            errors.append(f"{name}: {e}")
            continue

        prev_seen = set(seen_by_source.get(sid, []) or [])
        now_ids = [it.item_id for it in items]

        # Identify truly new
        newly = [it for it in items if it.item_id not in prev_seen]
        if newly:
            new_items_all.extend(newly)
            for it in newly:
                hay = f"{it.title}\n{it.link}\n{it.published or ''}\n{it.source_name}"
                if kw_re.search(hay):
                    new_items_matched.append(it)

        # Update state with newest-first limited cache
        keep: List[str] = []
        for iid in now_ids + list(prev_seen):
            if iid not in keep:
                keep.append(iid)
            if len(keep) >= 400:
                break
        seen_by_source[sid] = keep

    state["seen_ids_by_source"] = seen_by_source
    state["last_run_at"] = _now_local_str()
    _save_json(state_path, state)

    # 履歴保存 & ウェブページ生成
    matched_ids = {it.item_id for it in new_items_matched}
    try:
        _save_history(history_path, new_items_all, matched_ids)
        _generate_html(html_path)
    except Exception as e:
        print(f"[html generation failed] {e}")

    if errors:
        msg = _truncate_lines("\n".join(errors), max_toast_lines)
        _toast(f"{APP_NAME}: 取得エラー", msg)

    if new_items_matched:
        lines = []
        for it in new_items_matched[:max_toast_lines]:
            lines.append(f"[{it.source_name}] {it.title}")
        msg = _truncate_lines("\n".join(lines), max_toast_lines)
        _toast(f"{APP_NAME}: 重要そうな更新 {len(new_items_matched)}件", msg)
        return 0

    if new_items_all:
        lines = []
        for it in new_items_all[:max_toast_lines]:
            lines.append(f"[{it.source_name}] {it.title}")
        msg = _truncate_lines("\n".join(lines), max_toast_lines)
        _toast(f"{APP_NAME}: 更新 {len(new_items_all)}件（キーワード該当なし）", msg)
        return 0

    if notify_on_no_updates:
        _toast(f"{APP_NAME}: 更新なし", "本日の更新は検知されませんでした。")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
