# Adding a source

Every tool ends up as rows in `evidence/index/activity.csv`. There are three ways in, and none needs code.

## 1. A preset

`mapping = "<preset>"` with `method = "export"`. Presets: `jira-csv`, `linear-csv`, `asana-csv`, `clickup-csv`, `shortcut-csv`, `azure-devops-csv`, `slack-export`. A preset marked unverified prints a warning on import: compare the first converted rows with the export before relying on it.

## 2. A mapping file for any CSV or JSON export

Write `mappings/<tool>.toml` in the claim folder and set `mapping = "mappings/<tool>.toml"`. Draft it from the export's header row (CSV) or one record (JSON), then run `python3 <skill-dir>/scripts/index.py import --claim . --source NAME` and fix what the column report shows.

```toml
tool = "trello"            # roster aliases use this prefix, e.g. trello:jdoe
kind = "tracker"
format = "json"            # csv | json
verified = true            # you checked the converted rows against the export
timezone = ""              # optional: zone of times written without one; default is company.timezone
weight = "verbatim"        # "summary" for non-verbatim records
date_formats = ["iso"]     # tried in order: iso, epoch, epoch_ms, js, or strptime patterns like "%d/%b/%y %I:%M %p"
records = "actions"        # json only: dotted path to the list of records
key = "id"                 # column or dotted path holding the record id
container = "data.board.name"   # optional; a list means first non-empty
title = "data.card.name"   # optional
url = ""                   # optional
tags = []                  # columns whose values become tags (repeated CSV columns included)

[[events]]                 # each record can yield several rows
kind = "issue_created"     # an activity kind: commit, pr_opened, pr_merged, pr_review, pr_comment,
                           # issue_created, issue_state_change, issue_resolved, issue_assigned,
                           # issue_comment, chat_message, meeting, doc_edit
key_suffix = ""            # default ":<kind>"
when = { field = "type", equals = "createCard" }   # optional filter
date = "date"
actor = "memberCreator.username"
actor_email = ""           # optional
actor_name = ""            # optional
actor_strip = ""           # optional, e.g. "[]" for "[Jane Doe, Raj Patel]"
actor_split = ""           # optional, e.g. "," to keep the first of several people
excerpt = ""               # optional

[[events]]                 # a CSV with repeated columns, e.g. Jira "Comment" columns
kind = "issue_comment"
repeat = "Comment"
split = ";"
split_fields = ["date", "actor", "excerpt"]
```

A missing key or date column stops the import with the column names. A row whose date does not parse is listed as a failure; the others still import.

## 3. A Claude connector

For tools with a connector but no useful export (Notion, Confluence, meeting notes): save what the connector returns under `evidence/raw/NAME/`, then write `evidence/raw/NAME/rows.csv` with exactly these columns:

`source,key,kind,person,actor_raw,date,timestamp,container,tags,paths,title,excerpt,refs,url,raw_path,weight`

- `key`: a durable id from the tool; unique within the source.
- `actor_raw`: the person as the tool names them; `index.py build` resolves `person` from it through `roster.csv`.
- `date`: company-local `YYYY-MM-DD`; `timestamp`: UTC ISO with `Z`.
- `excerpt`: verbatim, at most 500 characters, truncation marked `…[truncated]`.
- `raw_path`: the saved raw file, relative to the claim folder.
- `weight`: `verbatim`, or `summary` for anything paraphrased (AI meeting notes are summaries).

Then `index.py build` and `index.py validate`.
