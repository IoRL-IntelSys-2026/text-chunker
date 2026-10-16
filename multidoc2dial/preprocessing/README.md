# PRE: конвейер ingest

Единая команда для снимка, нарезки, векторов и Qdrant.

```text
python ingest.py adapt-mdd --out data/snapshots/mdd_v1
python ingest.py accept --snapshot data/snapshots/mdd_v1
python ingest.py chunk --snapshot data/snapshots/mdd_v1 --collection mdd_chunks_v1 --config configs/chunking/mdd_sections_512.yaml
python ingest.py embed --collection mdd_chunks_v1
python ingest.py index --collection mdd_chunks_v1 --config configs/chunking/mdd_sections_512.yaml
python ingest.py quality --collection mdd_chunks_v1 --snapshot data/snapshots/mdd_v1
python ingest.py all --snapshot data/snapshots/mdd_v1 --collection mdd_chunks_v1 --config configs/chunking/mdd_sections_512.yaml
python ingest.py alias --collection mdd_chunks_v1 --alias mdd_current
python ingest.py snapshot --collection mdd_chunks_v1
```

То же через модуль: `python -m preprocessing …`.

| Команда | Что делает |
| --- | --- |
| `adapt-mdd` | снимок K1 из `data/cache/multidoc2dial.zip` |
| `accept` | приёмочная статистика K1 → `<snapshot>/acceptance.md` |
| `chunk` | `data/index/<collection>/chunks.jsonl` |
| `embed` | `data/index/<collection>/vectors.jsonl` |
| `index` | заливка в Qdrant + `index_info.json` (нужны `QDRANT_URL` и `QDRANT_API_KEY`) |
| `quality` | `quality_report.md` + локальные ворота K2 (до `alias`) |
| `all` | `chunk` + `quality` + `embed` + `index` (снимок уже должен быть) |
| `alias` | рабочее имя коллекции, например `mdd_current` |
| `snapshot` | резервная копия коллекции в Qdrant |

Шаблоны пояснений: `docs/specs/pre/templates/quality_report.md`, баг-репорт PRS — `bug_prs.md`.

Сборка через Docker по-прежнему: `docker compose run --rm --build build` (снимок + нарезка + векторы, без Qdrant).
