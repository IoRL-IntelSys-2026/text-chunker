# Шаблон: приёмка снимка (`acceptance.md`)

Файл пишет `python ingest.py accept`. Ниже — что значат поля словаря `snapshot_stats`.

| Поле | Что значит |
| --- | --- |
| `n_docs` | Число строк в `manifest.jsonl` |
| `by_content_type` | Сколько документов каждого типа (`text/plain`, `text/html`, …) |
| `by_lang` | Сколько документов каждого языка |
| `by_section` | Сколько документов в каждом разделе `section` |
| `unknown_sections` | Разделы из описи, которых нет в `reports/sections.json` |
| `size_bytes` | min / median / max размера файлов по `path` |
| `too_large` | Документы больше лимита из конфига (`max_html_bytes` / `max_file_bytes`) |
| `no_outlinks_share` | Доля документов без исходящих ссылок (`outlinks` пуст или поля нет) |
| `validation_errors` | Нарушения формата K1 из `validate_snapshot` / `rag-validate k1` |

На пилоте `mdd_v1` ожидается: 488 документов; dmv 149, ssa 109, va 138, studentaid 92; все `text/plain` и `en`; `no_outlinks_share = 1.0`.
