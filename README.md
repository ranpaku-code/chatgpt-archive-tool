# Chat Archive Tool

ChatGPT official export ZIP (or extracted folder) to local searchable archive:

- `chat_archive.html` (search / sort / filter / jump)
- `chat_archive.csv`
- `chat_pages/` (one page per chat)

## Features

- Extract from ZIP into any folder
- Read `conversations.json` or split `conversations-*.json`
- Keep custom `Category` + add `Project` column
- Full-text jump to first matching chat
- Per-chat page with in-chat jump
- Category rules configurable by JSON

## Requirements

- Python 3.9+
- No external Python package required

## Quick Start

### 1) Process extracted backup folder

```powershell
python make_chat_archive.py --out-dir "C:\path\to\ChatGPT_Backup" --skip-extract
```

### 2) Process from official ZIP directly

```powershell
python make_chat_archive.py --zip "C:\path\to\export.zip" --out-dir "C:\path\to\ChatGPT_Backup"
```

## Output Files

Generated under `--out-dir`:

- `chat_archive.html`
- `chat_archive.csv`
- `chat_pages\`
- `category_rules.json` (auto-created if missing)

## Category Rules

Default rules are auto-generated to `category_rules.json`.
You can edit categories, priority, and keywords.

Example source file is included:

- `category_rules.sample.json`

To use a custom rule file:

```powershell
python make_chat_archive.py --out-dir "C:\path\to\ChatGPT_Backup" --skip-extract --rules "C:\path\to\my_rules.json"
```

## Notes

- `Project` becomes `No Project` if export does not include project mapping fields.
- `chat.html` from official export is often huge and hard to read; this tool creates a practical local viewer.

## Privacy Checklist Before Sharing

- Do not publish exported conversation data.
- Share script and README only.
- Remove personal paths, emails, phone numbers from screenshots.
