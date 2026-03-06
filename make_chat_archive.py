import argparse
import csv
import datetime
import html
import json
import pathlib
import zipfile
from typing import Any

OUT_CSV = "chat_archive.csv"
OUT_HTML = "chat_archive.html"
DETAIL_DIR = "chat_pages"
RULE_FILE_NAME = "category_rules.json"

DEFAULT_CATEGORY_RULES = [
    {
        "name": "Code",
        "priority": 100,
        "keywords": [
            "python",
            "javascript",
            "typescript",
            "sql",
            "api",
            "git",
            "docker",
            "bug",
            "error",
            "code",
            "implementation",
        ],
    },
    {
        "name": "Writing",
        "priority": 90,
        "keywords": [
            "article",
            "blog",
            "summary",
            "translate",
            "email",
            "writing",
            "document",
            "markdown",
        ],
    },
    {
        "name": "Business",
        "priority": 80,
        "keywords": [
            "plan",
            "strategy",
            "sales",
            "market",
            "analysis",
            "kpi",
            "business",
            "revenue",
        ],
    },
    {
        "name": "Study",
        "priority": 70,
        "keywords": [
            "study",
            "learn",
            "english",
            "math",
            "exam",
            "question",
            "tutorial",
            "practice",
        ],
    },
]


def ts_to_iso(ts: Any) -> str:
    if not ts:
        return ""
    return datetime.datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create searchable ChatGPT archive (CSV + HTML + per-chat pages)."
    )
    parser.add_argument("--zip", help="Path to official ChatGPT export zip file.")
    parser.add_argument("--out-dir", default=".", help="Extraction and output directory.")
    parser.add_argument("--rules", default=None, help="Category rules JSON path.")
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip zip extraction even if --zip is given.",
    )
    return parser.parse_args()


def extract_zip(zip_path: pathlib.Path, out_dir: pathlib.Path) -> None:
    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP not found: {zip_path}")
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)


def load_category_rules(rule_file: pathlib.Path | None) -> list[dict[str, Any]]:
    if rule_file and rule_file.exists():
        raw = json.loads(rule_file.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("categories"), list):
            return raw["categories"]
        if isinstance(raw, list):
            return raw
        raise ValueError("Invalid category rules format.")
    return DEFAULT_CATEGORY_RULES


def categorize(text: str, rules: list[dict[str, Any]]) -> str:
    t = text.lower()
    best_category = "Other"
    best_score = 0
    best_priority = -1
    for rule in rules:
        name = str(rule.get("name") or "").strip()
        if not name:
            continue
        keywords = rule.get("keywords") or []
        if not isinstance(keywords, list):
            continue
        normalized = [str(k).lower() for k in keywords if str(k).strip()]
        score = sum(1 for kw in normalized if kw in t)
        priority = int(rule.get("priority", 0))
        if score > best_score or (score == best_score and priority > best_priority and score > 0):
            best_category = name
            best_score = score
            best_priority = priority
    return best_category


def load_conversations(base_dir: pathlib.Path) -> list[dict[str, Any]]:
    single = base_dir / "conversations.json"
    if single.exists():
        data = json.loads(single.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        raise ValueError("conversations.json is not an array.")

    split_files = sorted(base_dir.glob("conversations-*.json"))
    if not split_files:
        raise FileNotFoundError("No conversations.json or conversations-*.json found.")

    all_data: list[dict[str, Any]] = []
    for file_path in split_files:
        part = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(part, list):
            raise ValueError(f"{file_path.name} is not an array.")
        all_data.extend(part)
    return all_data


def load_project_map(base_dir: pathlib.Path) -> dict[str, str]:
    project_file = base_dir / "projects.json"
    if not project_file.exists():
        return {}
    raw = json.loads(project_file.read_text(encoding="utf-8"))
    items: list[dict[str, Any]] = []
    if isinstance(raw, list):
        items = [x for x in raw if isinstance(x, dict)]
    elif isinstance(raw, dict):
        for key in ("projects", "data", "items"):
            value = raw.get(key)
            if isinstance(value, list):
                items = [x for x in value if isinstance(x, dict)]
                break
        if not items:
            items = [raw]
    mapping: dict[str, str] = {}
    for item in items:
        pid = item.get("id") or item.get("project_id") or item.get("projectId")
        name = item.get("name") or item.get("title") or item.get("project_name")
        if pid:
            mapping[str(pid)] = str(name) if name else str(pid)
    return mapping


def extract_project_name(conv: dict[str, Any], project_map: dict[str, str]) -> str:
    for key in ("project_name", "projectName"):
        value = conv.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    project_id = None
    for key in ("project_id", "projectId", "workspace_id", "folder_id"):
        value = conv.get(key)
        if isinstance(value, str) and value.strip():
            project_id = value.strip()
            break
    if project_id and project_id in project_map:
        return project_map[project_id]
    if project_id:
        return project_id
    return "No Project"


def extract_text_from_parts(parts: Any) -> str:
    if not isinstance(parts, list):
        return ""
    texts: list[str] = []
    for part in parts:
        if isinstance(part, str):
            texts.append(part)
        elif isinstance(part, dict) and isinstance(part.get("text"), str):
            texts.append(part["text"])
    return "\n".join(texts).strip()


def build_message_rows(conv: dict[str, Any]) -> list[tuple[float, str, str]]:
    mapping = conv.get("mapping", {})
    if not isinstance(mapping, dict):
        return []
    messages: list[tuple[float, str, str]] = []
    for node in mapping.values():
        if not isinstance(node, dict):
            continue
        message = node.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content", {})
        parts = content.get("parts", []) if isinstance(content, dict) else []
        text = extract_text_from_parts(parts)
        if not text:
            continue
        author = message.get("author", {})
        role = author.get("role", "") if isinstance(author, dict) else ""
        create_time = message.get("create_time") or conv.get("update_time") or conv.get("create_time") or 0
        messages.append((float(create_time), str(role), text))
    messages.sort(key=lambda item: item[0])
    return messages


def write_detail_page(out_path: pathlib.Path, title: str, messages: list[tuple[float, str, str]]) -> None:
    blocks: list[str] = []
    for ts, role, text in messages:
        blocks.append(
            "<div class='msg'>"
            f"<div class='meta'>{html.escape(ts_to_iso(ts))} | {html.escape(role)}</div>"
            f"<pre>{html.escape(text)}</pre>"
            "</div>"
        )
    body = "\n".join(blocks) if blocks else "<p>(No visible text message)</p>"
    doc = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;padding:20px;max-width:1000px;margin:auto}}
h1{{font-size:20px}}
.msg{{border:1px solid #ddd;border-radius:8px;padding:10px;margin:10px 0;background:#fafafa}}
.meta{{font-size:12px;color:#555;margin-bottom:6px}}
pre{{white-space:pre-wrap;word-break:break-word;margin:0;font-family:inherit}}
a{{color:#0366d6}}
.hit{{border-color:#ff8a00;background:#fff4e8}}
</style>
<h1>{html.escape(title)}</h1>
<p><a href="../{OUT_HTML}">Back to archive index</a></p>
<input id="inChatQ" placeholder="Search in this chat..." style="width:60%;padding:6px">
<button id="inChatGo">Jump</button>
{body}
<script>
function findAndJump(keyword){{
  if(!keyword) return false;
  const kw=keyword.toLowerCase();
  const blocks=[...document.querySelectorAll('.msg')];
  for(const b of blocks) b.classList.remove('hit');
  for(const b of blocks){{
    const t=(b.innerText||'').toLowerCase();
    if(t.includes(kw)){{
      b.classList.add('hit');
      b.scrollIntoView({{behavior:'smooth', block:'center'}});
      return true;
    }}
  }}
  return false;
}}
document.getElementById('inChatGo').onclick=()=>{{
  const q=document.getElementById('inChatQ').value.trim();
  findAndJump(q);
}};
const urlQ=new URLSearchParams(location.search).get('q');
if(urlQ){{
  document.getElementById('inChatQ').value=urlQ;
  findAndJump(urlQ);
}}
</script>
</html>"""
    out_path.write_text(doc, encoding="utf-8")


def build_archive(base_dir: pathlib.Path, rules: list[dict[str, Any]]) -> None:
    conversations = load_conversations(base_dir)
    project_map = load_project_map(base_dir)
    detail_dir = base_dir / DETAIL_DIR
    detail_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for conv in conversations:
        title = str(conv.get("title") or "(no title)")
        conv_id = str(conv.get("conversation_id") or conv.get("id") or "")
        messages = build_message_rows(conv)
        full_text = "\n".join(m[2] for m in messages)
        category = categorize((title + "\n" + full_text)[:4000], rules)
        project_name = extract_project_name(conv, project_map)
        dt = conv.get("update_time") or conv.get("create_time") or 0
        detail_name = f"{conv_id}.html" if conv_id else f"unknown_{len(rows):06d}.html"
        local_link = f"{DETAIL_DIR}/{detail_name}"
        chatgpt_link = f"https://chatgpt.com/c/{conv_id}" if conv_id else ""
        write_detail_page(detail_dir / detail_name, title, messages)
        rows.append(
            {
                "datetime": ts_to_iso(dt),
                "category": category,
                "project": project_name,
                "title": title,
                "message_count": len(messages),
                "preview": (full_text[:200].replace("\n", " ") + "...") if full_text else "",
                "conversation_id": conv_id,
                "local_link": local_link,
                "chatgpt_link": chatgpt_link,
                "search_blob": full_text.lower()[:20000],
            }
        )
    rows.sort(key=lambda row: row["datetime"])

    fieldnames = [
        "datetime",
        "category",
        "project",
        "title",
        "message_count",
        "preview",
        "conversation_id",
        "local_link",
        "chatgpt_link",
    ]
    with open(base_dir / OUT_CSV, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({k: row[k] for k in fieldnames} for row in rows)

    categories = sorted({r["category"] for r in rows})
    projects = sorted({r["project"] for r in rows})
    category_options = "".join(f"<option>{html.escape(cat)}</option>" for cat in categories)
    project_options = "".join(f"<option>{html.escape(project)}</option>" for project in projects)
    table_rows_list: list[str] = []
    for r in rows:
        web_link = ""
        if r["chatgpt_link"]:
            web_link = f"<a href='{html.escape(r['chatgpt_link'])}' target='_blank'>Open ChatGPT</a>"
        table_rows_list.append(
            f"<tr data-search='{html.escape(r['search_blob'])}'>"
            f"<td>{html.escape(r['datetime'])}</td>"
            f"<td>{html.escape(r['category'])}</td>"
            f"<td>{html.escape(r['project'])}</td>"
            f"<td>{html.escape(r['title'])}</td>"
            f"<td>{r['message_count']}</td>"
            f"<td>{html.escape(r['preview'])}</td>"
            f"<td><a class='local-link' href='{html.escape(r['local_link'])}' target='_blank'>Open local</a></td>"
            f"<td>{web_link}</td>"
            "</tr>"
        )
    table_rows = "\n".join(table_rows_list)

    html_doc = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Chat Archive</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;padding:20px}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ddd;padding:8px;vertical-align:top}}
th{{cursor:pointer;background:#f6f6f6}}
input,select{{margin-right:8px;margin-bottom:12px;padding:6px}}
a{{color:#0366d6}}
</style>
<h2>Chat Archive</h2>
<input id="q" placeholder="Search..." style="width:40%">
<input id="fullq" placeholder="Full-text jump..." style="width:30%">
<button id="jump">Open first match</button>
<select id="cat"><option value="">All categories</option>{category_options}</select>
<select id="proj"><option value="">All projects</option>{project_options}</select>
<table id="t">
<thead>
<tr>
<th>DateTime</th><th>Category</th><th>Project</th><th>Title</th><th>Count</th><th>Preview</th><th>Local</th><th>Web</th>
</tr>
</thead>
<tbody>{table_rows}</tbody>
</table>
<script>
const q=document.getElementById('q');
const fullq=document.getElementById('fullq');
const jumpBtn=document.getElementById('jump');
const cat=document.getElementById('cat');
const proj=document.getElementById('proj');
const rows=[...document.querySelectorAll('#t tbody tr')];
function applyFilter(){{
  const keyword=q.value.toLowerCase();
  const category=cat.value;
  const project=proj.value;
  rows.forEach(r=>{{
    const text=r.innerText.toLowerCase();
    const okKeyword=!keyword||text.includes(keyword);
    const okCategory=!category||r.children[1].innerText===category;
    const okProject=!project||r.children[2].innerText===project;
    r.style.display=(okKeyword&&okCategory&&okProject)?'':'none';
  }});
}}
q.oninput=applyFilter;
cat.onchange=applyFilter;
proj.onchange=applyFilter;
jumpBtn.onclick=()=>{{
  const raw=fullq.value.trim();
  if(!raw) return;
  const kw=raw.toLowerCase();
  let target=rows.find(r=>(r.dataset.search||'').includes(kw) && r.style.display!=='none');
  if(!target) target=rows.find(r=>(r.dataset.search||'').includes(kw));
  if(!target){{
    alert('No match found in full text.');
    return;
  }}
  const a=target.querySelector('a.local-link');
  if(a){{
    const base=a.getAttribute('href');
    const sep=base.includes('?') ? '&' : '?';
    const href=base + sep + 'q=' + encodeURIComponent(raw);
    window.open(href,'_blank');
  }}
  target.scrollIntoView({{behavior:'smooth', block:'center'}});
  target.style.outline='2px solid #ff8a00';
  setTimeout(()=>target.style.outline='',1500);
}};
document.querySelectorAll('#t thead th').forEach((th,idx)=>th.onclick=()=>{{
  if(idx>5) return;
  const tbody=document.querySelector('#t tbody');
  const sorted=[...tbody.querySelectorAll('tr')].sort((a,b)=>
    a.children[idx].innerText.localeCompare(b.children[idx].innerText,'en'));
  sorted.forEach(r=>tbody.appendChild(r));
}});
</script>
</html>"""
    (base_dir / OUT_HTML).write_text(html_doc, encoding="utf-8")


def maybe_write_rule_template(base_dir: pathlib.Path) -> pathlib.Path:
    path = base_dir / RULE_FILE_NAME
    if path.exists():
        return path
    template = {"categories": DEFAULT_CATEGORY_RULES}
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    args = parse_args()
    out_dir = pathlib.Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.zip and not args.skip_extract:
        extract_zip(pathlib.Path(args.zip).expanduser().resolve(), out_dir)

    if args.rules:
        rule_file = pathlib.Path(args.rules).expanduser().resolve()
    else:
        candidate = out_dir / RULE_FILE_NAME
        rule_file = candidate if candidate.exists() else None

    rules = load_category_rules(rule_file)
    template_path = maybe_write_rule_template(out_dir)
    build_archive(out_dir, rules)

    print(f"Created: {out_dir / OUT_CSV}, {out_dir / OUT_HTML}, {out_dir / DETAIL_DIR}")
    print(f"Category rules template: {template_path}")


if __name__ == "__main__":
    main()
