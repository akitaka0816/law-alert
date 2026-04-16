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
  <title>Law Alert — 法改正情報ダッシュボード</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; }
    body { margin: 0; font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', 'Meiryo', sans-serif; background: #f0f4f8; color: #2d3748; }
    .header { background: #1a365d; color: #fff; padding: 1.5rem 2rem; }
    .header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; }
    .header .sub { margin: 0.2rem 0 0; font-size: 0.82rem; opacity: 0.75; }
    .stats { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.9rem; }
    .stat { background: rgba(255,255,255,0.15); border-radius: 5px; padding: 0.25rem 0.7rem; font-size: 0.78rem; }
    .stat-kw { background: rgba(217,119,6,0.4); }
    .toolbar { background: #fff; border-bottom: 1px solid #e2e8f0; padding: 0.7rem 2rem; position: sticky; top: 0; z-index: 100; display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: flex-start; }
    .sw { flex: 1; min-width: 160px; }
    .sw input { width: 100%; padding: 0.4rem 0.9rem; border: 1px solid #cbd5e0; border-radius: 20px; font-size: 0.88rem; outline: none; }
    .sw input:focus { border-color: #4299e1; box-shadow: 0 0 0 3px rgba(66,153,225,0.2); }
    .fw { display: flex; flex-wrap: wrap; gap: 0.35rem; }
    .fb { padding: 0.25rem 0.65rem; border: 1px solid #cbd5e0; border-radius: 20px; background: #fff; cursor: pointer; font-size: 0.75rem; color: #4a5568; }
    .fb:hover { background: #ebf8ff; border-color: #90cdf4; color: #2b6cb0; }
    .fb.active { background: #2b6cb0; color: #fff; border-color: #2b6cb0; }
    .container { max-width: 900px; margin: 1.2rem auto; padding: 0 1rem 3rem; }
    .empty, .nores { text-align: center; padding: 3rem 1rem; color: #718096; }
    .card { background: #fff; border-radius: 8px; padding: 1rem 1.3rem; margin-bottom: 0.6rem; border: 1px solid #e2e8f0; border-left: 4px solid #cbd5e0; }
    .card:hover { box-shadow: 0 2px 10px rgba(0,0,0,0.06); }
    .card.matched { border-left-color: #d97706; background: #fffbeb; }
    .chd { display: flex; flex-wrap: wrap; gap: 0.3rem; align-items: center; margin-bottom: 0.4rem; }
    .bsrc { font-size: 0.7rem; background: #ebf8ff; color: #2b6cb0; border-radius: 4px; padding: 0.1rem 0.45rem; font-weight: 600; }
    .bkw { font-size: 0.7rem; background: #fef3c7; color: #92400e; border-radius: 4px; padding: 0.1rem 0.45rem; font-weight: 600; }
    .ctitle a { color: #2d3748; text-decoration: none; font-size: 0.92rem; font-weight: 500; line-height: 1.5; }
    .ctitle a:hover { color: #2b6cb0; text-decoration: underline; }
    .cmeta { margin-top: 0.4rem; font-size: 0.74rem; color: #718096; display: flex; flex-wrap: wrap; gap: 0.8rem; }
    @media (max-width: 600px) { .header, .toolbar { padding-left: 1rem; padding-right: 1rem; } }
  </style>
</head>
<body>
  <div class="header">
    <h1>Law Alert</h1>
    <p class="sub">法改正・官報・パブリックコメント 自動収集ダッシュボード</p>
    <div class="stats">
      <span class="stat">総件数: <!--TOTAL--> 件</span>
      <span class="stat stat-kw">キーワード一致: <!--MATCHED_COUNT--> 件</span>
      <span class="stat">最終更新: <!--LAST_UPDATED--></span>
    </div>
  </div>
  <div class="toolbar">
    <div class="sw"><input type="text" id="q" placeholder="タイトルで絞り込み..." oninput="af()"></div>
    <div class="fw">
      <button class="fb active" data-filter="all" onclick="sf(this)">すべて</button>
      <button class="fb" data-filter="__kw__" onclick="sf(this)">★ キーワード一致のみ</button>
      <!--SRC_BTNS-->
    </div>
  </div>
  <div class="container">
    <div id="cards"><!--CARDS--></div>
    <p id="nores" style="display:none" class="nores">該当する項目がありません。</p>
  </div>
  <script>
    var cur='all';
    function sf(b){
      cur=b.dataset.filter;
      document.querySelectorAll('.fb').forEach(function(x){x.classList.remove('active');});
      b.classList.add('active');
      af();
    }
    function af(){
      var q=document.getElementById('q').value.trim().toLowerCase();
      var cs=document.querySelectorAll('#cards .card');
      var v=0;
      cs.forEach(function(c){
        var ok=true;
        if(cur==='__kw__'&&!c.classList.contains('matched'))ok=false;
        if(cur!=='all'&&cur!=='__kw__'&&(c.dataset.source||'')!==cur)ok=false;
        if(q&&c.textContent.toLowerCase().indexOf(q)===-1)ok=false;
        c.style.display=ok?'':'none';
        if(ok)v++;
      });
      document.getElementById('nores').style.display=v===0?'':'none';
    }
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


def _generate_html(history_path: str, html_path: str) -> None:
    data = _load_json(history_path, {"items": [], "last_updated": ""})
    items: List[Dict[str, Any]] = data.get("items", [])
    last_updated = html.escape(data.get("last_updated") or "不明")

    total = len(items)
    matched_count = sum(1 for it in items if it.get("matched"))

    # ソース一覧（出現順）
    sources: List[str] = []
    seen_src: set = set()
    for it in items:
        sn = it.get("source_name", "")
        if sn and sn not in seen_src:
            sources.append(sn)
            seen_src.add(sn)

    # カード HTML
    cards_parts: List[str] = []
    for it in items:
        matched = bool(it.get("matched"))
        title = html.escape(it.get("title", "(no title)"))
        link = html.escape(it.get("link", "#"))
        sname = html.escape(it.get("source_name", ""))
        published = html.escape(it.get("published") or "")
        detected = html.escape(it.get("detected_at", ""))
        bkw = '<span class="bkw">★ キーワード一致</span>' if matched else ""
        cls = "card matched" if matched else "card"
        pub_span = f'<span>公開: {published}</span>' if published else ""
        cards_parts.append(
            f'<div class="{cls}" data-source="{sname}">'
            f'<div class="chd"><span class="bsrc">{sname}</span>{bkw}</div>'
            f'<div class="ctitle"><a href="{link}" target="_blank" rel="noopener">{title}</a></div>'
            f'<div class="cmeta">{pub_span}<span>検知: {detected}</span></div>'
            f"</div>"
        )

    cards_html = (
        "\n".join(cards_parts)
        if cards_parts
        else '<p class="empty">まだ記録がありません。monitor.py を実行すると更新が蓄積されます。</p>'
    )

    src_btns = "\n".join(
        f'<button class="fb" data-filter="{html.escape(sn)}" onclick="sf(this)">{html.escape(sn)}</button>'
        for sn in sources
    )

    page = (
        _HTML_TEMPLATE
        .replace("<!--TOTAL-->", str(total))
        .replace("<!--MATCHED_COUNT-->", str(matched_count))
        .replace("<!--LAST_UPDATED-->", last_updated)
        .replace("<!--SRC_BTNS-->", src_btns)
        .replace("<!--CARDS-->", cards_html)
    )

    tmp = html_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(page)
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
        _generate_html(history_path, html_path)
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
