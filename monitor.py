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

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Law Alert — 法改正情報モニタリング</title>
  <style>
    *,*::before,*::after{box-sizing:border-box;}
    body{margin:0;font-family:'Helvetica Neue',Arial,'Hiragino Kaku Gothic ProN','Meiryo',sans-serif;background:#f0f4f8;color:#2d3748;}
    .hd{background:#1a365d;color:#fff;padding:1.2rem 2rem;}
    .hd h1{margin:0;font-size:1.4rem;font-weight:700;}
    .hd .sub{font-size:.8rem;opacity:.75;margin:.2rem 0 0;}
    .hd .stats{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.8rem;}
    .stat{background:rgba(255,255,255,.15);border-radius:5px;padding:.2rem .65rem;font-size:.78rem;}
    .stat-kw{background:rgba(217,119,6,.4);}
    .stat-ok{background:rgba(56,178,172,.28);}
    .stat-bad{background:rgba(220,38,38,.4);font-weight:600;}
    .run-err{margin:0 2rem 1rem;font-size:.76rem;color:#fecaca;background:rgba(0,0,0,.2);border-radius:6px;padding:.5rem .75rem;max-width:960px;}
    .run-err summary{cursor:pointer;font-weight:600;}
    .wl-toolbar{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin:0 auto 1rem;padding:0 1rem;max-width:960px;}
    .tabs{background:#162e50;display:flex;gap:0;padding:0 2rem;}
    .tab{padding:.6rem 1.4rem;font-size:.88rem;font-weight:600;color:rgba(255,255,255,.65);cursor:pointer;border:none;background:none;border-bottom:3px solid transparent;transition:all .15s;}
    .tab:hover{color:#fff;}
    .tab.act{color:#fff;border-bottom-color:#63b3ed;}
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
    .wl-wrap{max-width:960px;margin:1.2rem auto 3rem;padding:0 1rem;}
    .wl-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1rem;}
    .wlc{background:#fff;border-radius:10px;padding:1rem 1.2rem;border:1px solid #e2e8f0;border-top:4px solid #cbd5e0;transition:box-shadow .15s;}
    .wlc:hover{box-shadow:0 4px 14px rgba(0,0,0,.08);}
    .wlc.hot{border-top-color:#dd6b20;}
    .wlc.warm{border-top-color:#38a169;}
    .wlc.cool{border-top-color:#4299e1;}
    .wl-name{font-size:.95rem;font-weight:700;color:#2d3748;margin-bottom:.3rem;}
    .wl-desc{font-size:.74rem;color:#718096;margin-bottom:.7rem;line-height:1.5;}
    .wl-nums{display:flex;gap:.6rem;margin-bottom:.75rem;}
    .wl-num{text-align:center;flex:1;background:#f7fafc;border-radius:6px;padding:.4rem .3rem;}
    .wl-num .n{font-size:1.35rem;font-weight:800;line-height:1;}
    .wl-num .n.hot{color:#dd6b20;}
    .wl-num .n.warm{color:#38a169;}
    .wl-num .lbl{font-size:.65rem;color:#718096;margin-top:.15rem;}
    .wl-items{margin-bottom:.75rem;}
    .wl-item{font-size:.74rem;padding:.28rem 0;border-bottom:1px solid #f0f4f8;line-height:1.45;}
    .wl-item:last-child{border-bottom:none;}
    .wl-item a{color:#2b6cb0;text-decoration:none;}
    .wl-item a:hover{text-decoration:underline;}
    .wl-item .wi-src{font-size:.65rem;color:#a0aec0;margin-right:.3rem;}
    .wl-item .wi-date{font-size:.65rem;color:#a0aec0;float:right;}
    .wl-none{font-size:.78rem;color:#a0aec0;text-align:center;padding:.6rem 0;}
    .wl-more{display:block;width:100%;text-align:center;font-size:.76rem;padding:.35rem;background:#ebf8ff;color:#2b6cb0;border:1px solid #bee3f8;border-radius:6px;cursor:pointer;margin-top:.1rem;}
    .wl-more:hover{background:#bee3f8;}
    @media(max-width:640px){.hd,.filters,.tabs{padding-left:1rem;padding-right:1rem;}.wl-grid{grid-template-columns:1fr;}.run-err{margin-left:1rem;margin-right:1rem;}}
  </style>
</head>
<body>
<div class="hd">
  <h1>Law Alert — 法改正情報モニタリング</h1>
  <p class="sub">法改正・官報・パブリックコメント 自動収集</p>
  <div class="stats">
    <span class="stat" id="st-total">読み込み中...</span>
    <span class="stat stat-kw" id="st-kw"></span>
    <span class="stat" id="st-upd"></span>
    <span class="stat stat-ok" id="st-run">モニタ: …</span>
  </div>
  <div id="runErrBox" class="run-err" style="display:none"></div>
</div>
<div class="tabs">
  <button class="tab act" id="tab-wl" onclick="showTab('wl')">重点ウォッチリスト</button>
  <button class="tab" id="tab-db" onclick="showTab('db')">全件データベース</button>
</div>
<div id="pane-wl">
  <div class="wl-toolbar">
    <label class="dr" style="margin:0"><span>テーマ</span>
      <select class="ss" id="wlTheme" onchange="buildWL()">
        <option value="">すべて</option>
      </select>
    </label>
  </div>
  <div class="wl-wrap">
    <div class="wl-grid" id="wlGrid"><p class="msg">読み込み中...</p></div>
  </div>
</div>
<div id="pane-db" style="display:none">
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
      <label class="dr" style="margin:0"><span>テーマ</span>
        <select class="ss" id="dbTheme" onchange="af()">
          <option value="">（絞らない）</option>
        </select>
      </label>
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
</div>
<script>
var PG=30,all=[],wl=[],fil=[],cur=1,dbt=null,_wlFilter=null,_lastRun=null;
function themeKeywords(theme){
  if(!theme||!wl.length)return[];
  var ks=[];
  wl.forEach(function(l){if((l.theme||'')===theme)(l.keywords||[]).forEach(function(k){if(k)ks.push(k);});});
  return ks;
}
function fillThemeSelects(){
  var themes=[...new Set(wl.map(function(l){return l.theme||'';}).filter(Boolean))].sort();
  var ws=document.getElementById('wlTheme');
  var ds=document.getElementById('dbTheme');
  var v1=ws?ws.value:'',v2=ds?ds.value:'';
  if(ws){
    ws.innerHTML='<option value="">すべて</option>'+themes.map(function(t){return '<option value="'+e(t)+'">'+e(t)+'</option>';}).join('');
    if(v1&&themes.indexOf(v1)>=0)ws.value=v1;
  }
  if(ds){
    ds.innerHTML='<option value="">（絞らない）</option>'+themes.map(function(t){return '<option value="'+e(t)+'">'+e(t)+'</option>';}).join('');
    if(v2&&themes.indexOf(v2)>=0)ds.value=v2;
  }
}
function assetUrl(name){
  var p=window.location.pathname;
  if(p.endsWith('/'))return p+name;
  if(/\\.html$/i.test(p))return p.replace(/[^/]+$/,name);
  return p+'/'+name;
}
function e(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function deb(){clearTimeout(dbt);dbt=setTimeout(af,250);}
function showTab(t){
  document.getElementById('tab-wl').classList.toggle('act',t==='wl');
  document.getElementById('tab-db').classList.toggle('act',t==='db');
  document.getElementById('pane-wl').style.display=t==='wl'?'':'none';
  document.getElementById('pane-db').style.display=t==='db'?'':'none';
}
function gotoLaw(idx){
  var law=wl[idx];if(!law)return;
  _wlFilter=law.keywords||[];
  showTab('db');
  document.getElementById('q').value='';
  document.getElementById('kwOnly').checked=false;
  document.getElementById('df').value='';
  document.getElementById('dt').value='';
  sp(null);af();
}
function buildWL(){
  var grid=document.getElementById('wlGrid');
  if(!wl.length){grid.innerHTML='<p class="msg">watchlist.json が読み込めませんでした。</p>';return;}
  var tsel=(document.getElementById('wlTheme')||{}).value||'';
  var now=new Date(),d30=new Date(now);
  d30.setDate(d30.getDate()-30);
  var d30str=fmt(d30);
  var parts=[];
  wl.forEach(function(law,idx){
    if(tsel && (law.theme||'')!==tsel)return;
    var kws=law.keywords||[];
    var re=new RegExp(kws.map(function(k){return k.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&');}).join('|'),'i');
    var hits=all.filter(function(i){return re.test(i.title+' '+(i.source_name||''));});
    var hits30=hits.filter(function(i){return(i.detected_at||'').slice(0,10)>=d30str;});
    hits.sort(function(a,b){return(b.detected_at||'').localeCompare(a.detected_at||'');});
    var recent=hits.slice(0,3);
    var cls='wlc'+(hits30.length>0?' hot':hits.length>0?' warm':' cool');
    var nc=hits30.length>0?'hot':'warm';
    var itemsHtml=recent.length?recent.map(function(i){
      var dt=(i.detected_at||'').slice(0,10);
      return '<div class="wl-item"><span class="wi-src">'+e(i.source_name)+'</span>'+
        '<a href="'+e(i.link)+'" target="_blank" rel="noopener">'+e(i.title)+'</a>'+
        '<span class="wi-date">'+e(dt)+'</span></div>';
    }).join(''):'<div class="wl-none">— 関連情報なし —</div>';
    var moreBtn=hits.length>3?'<button class="wl-more" onclick="gotoLaw('+idx+')">すべて '+hits.length+' 件をデータベースで見る →</button>':'';
    var th=(law.theme)?'<span class="bsrc" style="margin-left:.35rem">'+e(law.theme)+'</span>':'';
    parts.push('<div class="'+cls+'">'+
      '<div class="wl-name">'+e(law.name)+th+'</div>'+
      (law.description?'<div class="wl-desc">'+e(law.description)+'</div>':'')+
      '<div class="wl-nums">'+
        '<div class="wl-num"><div class="n '+(hits.length>0?nc:'')+'">'+(hits.length)+'</div><div class="lbl">累計ヒット</div></div>'+
        '<div class="wl-num"><div class="n '+(hits30.length>0?nc:'')+'">'+(hits30.length)+'</div><div class="lbl">直近30日</div></div>'+
      '</div>'+
      '<div class="wl-items">'+itemsHtml+'</div>'+
      moreBtn+
      '</div>');
  });
  grid.innerHTML=parts.length?parts.join(''):'<p class="msg">このテーマに該当するカードがありません。</p>';
}
async function init(){
  try{
    var results=await Promise.all([
      fetch(assetUrl('history.json')).then(function(r){if(!r.ok)throw new Error('history.json が見つかりません');return r.json();}),
      fetch(assetUrl('watchlist.json')).then(function(r){return r.ok?r.json():[];}).catch(function(){return[];})
    ]);
    var d=results[0];
    wl=Array.isArray(results[1])?results[1]:[];
    all=d.items||[];
    _lastRun=d.last_run||null;
    var kw=all.filter(function(i){return i.matched;}).length;
    document.getElementById('st-total').textContent='総件数: '+all.length+' 件';
    document.getElementById('st-kw').textContent='★ キーワード一致: '+kw+' 件';
    document.getElementById('st-upd').textContent='データ更新: '+(d.last_updated||'不明');
    var lr=_lastRun||{};
    var stR=document.getElementById('st-run');
    if(stR){
      stR.className='stat '+(lr.had_errors?'stat-bad':'stat-ok');
      stR.textContent=lr.finished_at?('最終モニタ: '+lr.finished_at+(lr.had_errors?' · 取得エラー '+((lr.errors||[]).length)+'件':' · 取得正常')):'最終モニタ: （未記録）';
    }
    var errBox=document.getElementById('runErrBox');
    if(errBox){
      if(lr.had_errors&&(lr.errors||[]).length){
        errBox.style.display='block';
        errBox.innerHTML='<details><summary>取得エラー詳細（'+lr.errors.length+'件）</summary><pre style="white-space:pre-wrap;margin:.5rem 0 0;font-size:.72rem;opacity:.95">'+lr.errors.map(function(x){return e(x);}).join(String.fromCharCode(10))+'</pre></details>';
      }else{errBox.style.display='none';errBox.innerHTML='';}
    }
    var srcs=[...new Set(all.map(function(i){return i.source_name;}))];
    var row=document.getElementById('srcRow');
    srcs.forEach(function(sn){
      var l=document.createElement('label');
      l.className='scb on';
      l.innerHTML='<input type="checkbox" class="sci" value="'+e(sn)+'" checked onchange="af()"> '+e(sn);
      row.appendChild(l);
    });
    fillThemeSelects();
    buildWL();
    af();
  }catch(err){
    var em=(err&&err.message)||String(err);
    document.getElementById('st-total').textContent='読み込み失敗';
    document.getElementById('st-kw').textContent='';
    document.getElementById('st-upd').textContent=em;
    var stR=document.getElementById('st-run');if(stR){stR.className='stat stat-bad';stR.textContent='モニタ: 不明';}
    var errBox=document.getElementById('runErrBox');if(errBox){errBox.style.display='none';errBox.innerHTML='';}
    document.getElementById('wlGrid').innerHTML='<p class="msg">読み込み失敗: '+e(em)+'</p>';
    document.getElementById('cards').innerHTML='<p class="msg">読み込み失敗: '+e(em)+'</p>';
  }
}
function af(){
  var q=document.getElementById('q').value.trim().toLowerCase();
  var kw=document.getElementById('kwOnly').checked;
  var df=document.getElementById('df').value;
  var dt=document.getElementById('dt').value;
  var sb=document.getElementById('sb').value;
  var dbTheme=(document.getElementById('dbTheme')||{}).value||'';
  var ck=new Set(Array.from(document.querySelectorAll('.sci:checked')).map(function(c){return c.value;}));
  document.querySelectorAll('label.scb').forEach(function(l){
    l.classList.toggle('on',l.querySelector('input').checked);
  });
  var wf=_wlFilter;_wlFilter=null;
  var tkw=dbTheme?themeKeywords(dbTheme):[];
  var tre=tkw.length?new RegExp(tkw.map(function(k){return k.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&');}).join('|'),'i'):null;
  fil=all.filter(function(i){
    if(wf){
      var re=new RegExp(wf.map(function(k){return k.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&');}).join('|'),'i');
      if(!re.test(i.title+' '+(i.source_name||'')))return false;
    }else{
      if(q&&i.title.toLowerCase().indexOf(q)===-1)return false;
    }
    if(tre&&!tre.test(i.title+' '+(i.source_name||'')))return false;
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
  var body=[hd].concat(rows).map(function(r){return r.map(function(v){return'"'+String(v).replace(/"/g,'""')+'"';}).join(',');}).join('\\r\\n');
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
init();
</script>
</body>
</html>"""


@dataclass
class Item:
    source_id: str
    source_name: str
    item_id: str
    title: str
    link: str
    published: Optional[str] = None


def _is_excluded(it: Item, exclude_cfg: Any) -> bool:
    if not exclude_cfg or not isinstance(exclude_cfg, dict):
        return False
    title = it.title or ""
    link = it.link or ""
    hay = f"{title}\n{link}"
    for sub in exclude_cfg.get("title_substrings", []) or []:
        s = str(sub).strip()
        if s and s in title:
            return True
    for sub in exclude_cfg.get("title_or_link_substrings", []) or []:
        s = str(sub).strip()
        if s and s in hay:
            return True
    for sid in exclude_cfg.get("source_ids", []) or []:
        if sid and it.source_id == str(sid).strip():
            return True
    for pat in exclude_cfg.get("title_regex", []) or []:
        p = str(pat).strip()
        if not p:
            continue
        try:
            if re.search(p, title, re.IGNORECASE | re.DOTALL):
                return True
        except re.error:
            continue
    return False


def _save_history(
    history_path: str,
    new_items: List[Item],
    matched_ids: set,
    max_items: Optional[int] = None,
    run_errors: Optional[List[str]] = None,
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
    if max_items is None or max_items <= 0:
        data["items"] = combined
    else:
        data["items"] = combined[:max_items]
    data["last_updated"] = now
    errs = list(run_errors or [])[:30]
    data["last_run"] = {
        "finished_at": now,
        "had_errors": len(errs) > 0,
        "errors": errs,
    }
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
    exclude_cfg = config.get("exclude", {}) or {}

    max_items = int(run_cfg.get("max_items_per_source", 30))
    history_max_items = int(run_cfg.get("history_max_items", 0))
    max_toast_lines = int(run_cfg.get("max_toast_lines", 6))
    notify_on_no_updates = bool(run_cfg.get("notify_on_no_updates", True))

    kw_re = _compile_keywords(keywords)

    state: Dict[str, Any] = _load_json(state_path, {})
    seen_by_source: Dict[str, List[str]] = state.get("seen_ids_by_source", {})
    if not isinstance(seen_by_source, dict):
        seen_by_source = {}

    history_snapshot: Dict[str, Any] = _load_json(history_path, {"items": []})
    history_seen_ids = {
        str(r.get("item_id", "")).strip()
        for r in history_snapshot.get("items", [])
        if isinstance(r, dict) and str(r.get("item_id", "")).strip()
    }

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
        newly = [it for it in items if it.item_id not in prev_seen and it.item_id not in history_seen_ids]
        newly = [it for it in newly if not _is_excluded(it, exclude_cfg)]
        if newly:
            new_items_all.extend(newly)
            history_seen_ids.update(it.item_id for it in newly)
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
        _save_history(
            history_path,
            new_items_all,
            matched_ids,
            max_items=history_max_items,
            run_errors=errors,
        )
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
