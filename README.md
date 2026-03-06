# Chat Archive Tool

ChatGPT official export ZIP (or extracted folder) to local searchable archive:

- `chat_archive.html` (search / sort / filter / jump)
- `chat_archive.csv`
- `chat_pages/` (one page per chat)

## Features

- Extract from ZIP into any folder
- Read `conversations.json` or split `conversations-*.json`
- Keep custom `Category` + add `Project` column
- Parse `assetsJson` from `chat.html` when available
- Render image/audio attachments in `chat_pages/` detail pages
- Show `Media` count in `chat_archive.html` / `chat_archive.csv`
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
- Media mapping depends on `assetsJson` in exported `chat.html`; missing files are shown as missing links.

## What's New (vs previous version)

- Added parsing of `assetsJson` from exported `chat.html`.
- Added per-message media rendering in `chat_pages/*.html`.
- Images are shown as thumbnails with clickable links.
- Audio files are shown with HTML5 player (`<audio controls>`) and links.
- Missing attachment files are marked as `missing`.
- Added `Media` count column to both `chat_archive.html` and `chat_archive.csv`.
- Existing category/project filters and full-text jump behavior are preserved.

## Privacy Checklist Before Sharing

- Do not publish exported conversation data.
- Share script and README only.
- Remove personal paths, emails, phone numbers from screenshots.
