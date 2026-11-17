#!/usr/bin/env python3
"""每日財經報導：從 Google Drive 資料夾（或本機資料夾）抓 HTML，組成靜態網站。

用法：
  雲端（GitHub Actions）：
    GDRIVE_FOLDER_ID=... GDRIVE_SA_JSON='{...}' python build.py --drive
  本機預覽：
    python build.py --local "~/Library/CloudStorage/GoogleDrive-.../我的雲端硬碟/每日財經報導"

日期判定：檔名開頭 8 碼數字（例如 20261116_台股大跌.html → 2026-11-16）；
沒有的話用檔案修改時間（台北時間）。同一天有多個檔案時，取最後修改的那個。
輸出到 _site/：
  index.html            最新一篇（右下角加「歷史日報」連結）
  YYYY-MM-DD/index.html 每一天的固定網址
  archive/index.html    歷史列表
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

TPE = timezone(timedelta(hours=8))
SITE_TITLE = os.environ.get("SITE_TITLE", "顏選金融｜每日財經報導")
OUT = Path(__file__).resolve().parent / "_site"


@dataclass
class Report:
    date: str          # YYYY-MM-DD
    name: str          # 原始檔名
    modified: datetime
    content: bytes

    @property
    def title(self) -> str:
        m = re.search(rb"<title[^>]*>(.*?)</title>", self.content, re.S | re.I)
        if m:
            return html.unescape(m.group(1).decode("utf-8", "replace")).strip()
        return Path(self.name).stem


def date_of(name: str, modified: datetime) -> str:
    m = re.match(r"(\d{4})[-_.]?(\d{2})[-_.]?(\d{2})", name)
    if m:
        y, mo, d = m.groups()
        try:
            return datetime(int(y), int(mo), int(d)).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return modified.astimezone(TPE).strftime("%Y-%m-%d")


# ---------- 來源 ----------

def from_local(folder: Path) -> list[Report]:
    out = []
    for p in sorted(folder.glob("*.htm*")):
        mod = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        out.append(Report(date_of(p.name, mod), p.name, mod, p.read_bytes()))
    return out


def from_drive(folder_id: str, sa_json: str) -> list[Report]:
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession

    creds = service_account.Credentials.from_service_account_info(
        json.loads(sa_json),
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    s = AuthorizedSession(creds)
    files, token = [], None
    q = f"'{folder_id}' in parents and trashed = false and mimeType = 'text/html'"
    while True:
        r = s.get(
            "https://www.googleapis.com/drive/v3/files",
            params={
                "q": q,
                "fields": "nextPageToken, files(id, name, modifiedTime)",
                "pageSize": 1000,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                **({"pageToken": token} if token else {}),
            },
        )
        r.raise_for_status()
        data = r.json()
        files += data.get("files", [])
        token = data.get("nextPageToken")
        if not token:
            break

    out = []
    for f in files:
        mod = datetime.fromisoformat(f["modifiedTime"].replace("Z", "+00:00"))
        r = s.get(
            f"https://www.googleapis.com/drive/v3/files/{f['id']}",
            params={"alt": "media", "supportsAllDrives": "true"},
        )
        r.raise_for_status()
        out.append(Report(date_of(f["name"], mod), f["name"], mod, r.content))
    return out


# ---------- 輸出 ----------

NAV = """
<!-- daily-report-nav -->
<a href="{href}" class="no-print" style="position:fixed;right:16px;bottom:16px;z-index:9999;
 padding:8px 14px;border-radius:999px;background:#0f172a;color:#f8fafc;font:500 14px/1.2
 -apple-system,BlinkMacSystemFont,'Noto Sans TC','PingFang TC',sans-serif;text-decoration:none;
 box-shadow:0 2px 10px rgba(0,0,0,.25);opacity:.92">歷史日報 ›</a>
<style>@media print{{a[href="{href}"]{{display:none!important}}}}</style>
"""


def with_nav(content: bytes, href: str) -> bytes:
    nav = NAV.format(href=href).encode()
    i = content.lower().rfind(b"</body>")
    return content[:i] + nav + content[i:] if i >= 0 else content + nav


WEEKDAYS = "一二三四五六日"


def archive_page(reports: list[Report]) -> str:
    rows = []
    for r in reports:
        d = datetime.strptime(r.date, "%Y-%m-%d")
        rows.append(
            f'<li><a href="../{r.date}/"><span class="d">{d:%Y/%m/%d}（{WEEKDAYS[d.weekday()]}）</span>'
            f'<span class="t">{html.escape(r.title)}</span></a></li>'
        )
    updated = datetime.now(TPE).strftime("%Y/%m/%d %H:%M")
    return f"""<!DOCTYPE html>
<html lang="zh-Hant"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(SITE_TITLE)}｜歷史日報</title>
<style>
:root{{--bg:#f8fafc;--card:#fff;--line:#e2e8f0;--fg:#0f172a;--muted:#64748b;--accent:#2563eb}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0b1120;--card:#111827;--line:#1e293b;--fg:#f8fafc;--muted:#94a3b8;--accent:#60a5fa}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,BlinkMacSystemFont,"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif}}
main{{max-width:760px;margin:0 auto;padding:32px 16px 64px}}
h1{{font-size:26px;margin:0 0 4px}} .sub{{color:var(--muted);font-size:14px;margin:0 0 24px}}
.latest{{display:inline-block;margin-bottom:20px;color:var(--accent);text-decoration:none;font-weight:600}}
ul{{list-style:none;padding:0;margin:0;background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}}
li+li{{border-top:1px solid var(--line)}}
li a{{display:flex;gap:16px;padding:14px 18px;color:inherit;text-decoration:none;align-items:baseline}}
li a:hover{{background:color-mix(in srgb,var(--accent) 8%,transparent)}}
.d{{flex:none;color:var(--muted);font-variant-numeric:tabular-nums;font-size:14px}}
.t{{font-weight:500}}
@media (max-width:520px){{li a{{flex-direction:column;gap:2px}}}}
</style></head>
<body><main>
<h1>{html.escape(SITE_TITLE)}</h1>
<p class="sub">共 {len(reports)} 篇・更新於 {updated}</p>
<a class="latest" href="../">→ 看最新一篇</a>
<ul>
{chr(10).join(rows)}
</ul>
</main></body></html>
"""


def build(reports: list[Report]) -> None:
    # 同一天取最後修改的那份
    by_date: dict[str, Report] = {}
    for r in reports:
        if r.date not in by_date or r.modified > by_date[r.date].modified:
            by_date[r.date] = r
    reports = sorted(by_date.values(), key=lambda r: r.date, reverse=True)
    if not reports:
        sys.exit("資料夾裡沒有 HTML 檔，停止發布（避免把網站清空）。")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / ".nojekyll").write_text("")

    for r in reports:
        d = OUT / r.date
        d.mkdir()
        (d / "index.html").write_bytes(with_nav(r.content, "../archive/"))
    (OUT / "index.html").write_bytes(with_nav(reports[0].content, "archive/"))
    (OUT / "archive").mkdir()
    (OUT / "archive" / "index.html").write_text(archive_page(reports), encoding="utf-8")

    print(f"完成：{len(reports)} 篇，最新 {reports[0].date}「{reports[0].title}」")
    for r in reports:
        print(f"  {r.date}  {r.name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--drive", action="store_true", help="從 Google Drive 讀（需環境變數）")
    g.add_argument("--local", metavar="DIR", help="從本機資料夾讀")
    a = ap.parse_args()
    if a.drive:
        fid, sa = os.environ.get("GDRIVE_FOLDER_ID"), os.environ.get("GDRIVE_SA_JSON")
        if not fid or not sa:
            sys.exit("缺少 GDRIVE_FOLDER_ID 或 GDRIVE_SA_JSON")
        build(from_drive(fid, sa))
    else:
        build(from_local(Path(a.local).expanduser()))


if __name__ == "__main__":
    main()
