# RAG SYSTEM

Это RAG-система: ответ собирается не из памяти модели, а из найденных кусков документов. Человек задаёт вопрос, программа ищет близкие фрагменты и просит модель написать ответ только по ним.

Система сделана на учебном архиве MultiDoc2Dial: 488 готовых английских страниц про права и регистрацию, социальное страхование, дела ветеранов и помощь студентам. Архив нужен раньше сайта университета, чтобы собрать и проверить всю цепочку на известных текстах. Документы приведены к снимку, нарезаны на фрагменты, посчитаны векторы и загружены в Qdrant.

Проект лежит в папке `multidoc2dial` репозитория [text-chunker](https://github.com/IoRL-IntelSys-2026/text-chunker/tree/main/multidoc2dial). Скачать её:

```text
git clone https://github.com/IoRL-IntelSys-2026/text-chunker.git
```

Дальнейшие команды выполняются из папки `text-chunker/multidoc2dial`.

## Что сделано

1. **Снимок `mdd_v1`.** Из `data/cache/multidoc2dial.zip` прочитаны 488 документов, zip на диск не распаковывался. Текст сохранён как есть. У каждого документа есть адрес `mdd://`, номер `doc_id`, файл страницы, файл разделов и строка в описи. Загрузчик: `packages/rag_common/datasets/mdd/`, адаптер: `preprocessing/adapters/mdd.py`.
2. **Нарезка S2.** Фрагменты режутся по разделам (`preprocessing/chunkers/md_header.py`): лимит 512 токенов, перекрытие 64, минимум 24. Получилось 7149 фрагментов в `chunks.jsonl`. Стратегию S1 (fixed) не делаем.
3. **Векторы.** Модель `BAAI/bge-m3` считает их по полю `embed_text`. В это поле собираются заголовок документа, заголовки раздела и текст фрагмента. По этой строке получаются плотный вектор на 1024 числа и разреженный вектор слов. Они лежат в `vectors.jsonl`, в том же порядке, что и фрагменты.
4. **Отчёт о качестве.** `python ingest.py quality` пишет `data/index/mdd_chunks_v1/quality_report.md` (статистика, гистограмма длин, `dup_ratio`, топ-20 повторов) и проверяет локальные ворота K2. На mdd ненулевой `dup_ratio` ожидаем. Как читать поля — `docs/specs/pre/templates/quality_report.md`.
5. **База.** Коллекция Qdrant Cloud `mdd_chunks_v1`: 7149 точек, номер точки равен `chunk_id`. Рабочий алиас: `mdd_current` → `mdd_chunks_v1`.
6. **CLI `ingest`.** Одна команда на шаги: `adapt-mdd`, `chunk`, `embed`, `quality`, `index`, `all`, `alias`, `snapshot`.
7. **Поиск и ответ.** `retrieve.py` ищет по смыслу и по словам и склеивает списки. `answer.py` отдаёт найденные фрагменты модели `Qwen/Qwen2.5-0.5B-Instruct`. Модель грузится через Hugging Face `transformers` на видеокарту, сервера vLLM нет.

## Как устроено

```text
1. Архив data/cache/multidoc2dial.zip
   Внутри 488 страниц. Zip на диск не распаковывается, текст читается из него в памяти.
   Загрузчик: packages/rag_common/datasets/mdd/

2. Снимок data/snapshots/mdd_v1
   У каждой страницы появляются файл текста, файл разделов и строка в описи. Сам текст не меняется.
   Сборка: python ingest.py adapt-mdd  (preprocessing/adapters/mdd.py)

3. Фрагменты data/index/mdd_chunks_v1/chunks.jsonl
   Страница режется по разделам (S2). Одна строка — один фрагмент, всего 7149. Векторов в этом файле ещё нет.
   Команда: python ingest.py chunk

4. Отчёт data/index/mdd_chunks_v1/quality_report.md
   Статистика нарезки, dup_ratio, топ повторов и локальные ворота K2.
   Команда: python ingest.py quality

5. Векторы data/index/mdd_chunks_v1/vectors.jsonl
   Модель bge-m3 по полю embed_text считает числовой портрет фрагмента.
   Команда: python ingest.py embed

6. Коллекция Qdrant mdd_chunks_v1 (+ алиас mdd_current)
   Фрагмент вместе со своим вектором кладётся в базу одной точкой. Номер точки равен chunk_id.
   Команды: python ingest.py index
             python ingest.py alias --collection mdd_chunks_v1 --alias mdd_current

7. retrieve.py
   Вопрос тоже превращается в вектор. База отдаёт ближайшие фрагменты.

8. answer.py
   Модель пишет ответ по тексту этих фрагментов и по вопросу.
```

Снимок, нарезка, `quality_report.md` и `.env` в git не входят. В репозитории лежат код, тесты, конфиг нарезки и копия архива.

Подробный разбор одного короткого документа: `docs/one_document_path.md`. Пояснение к снимку: `docs/mdd_v1_explained.md`. Схема папок: `docs/folders.md`. Команды ingest: `preprocessing/README.md`.

## Сборка после клона

После `git clone` сначала соберите снимок, нарезку и векторы через Docker. Локальный Python для этого шага не нужен, `.env` и ключ Qdrant тоже не нужны. Pytest не запускается, в базу ничего не пишется. Первый запуск долгий: скачивается модель `BAAI/bge-m3`.

```text
docker compose run --rm --build build
```

На диске появятся `data/snapshots/mdd_v1/` и `data/index/mdd_chunks_v1/` (`chunks.jsonl`, `vectors.jsonl`).

## Команды ingest

Одна точка входа: `python ingest.py …` (или `python -m preprocessing …`). Справка: `python ingest.py --help`.

Подробности также в `preprocessing/README.md`.

| Команда | Зачем | Когда после клона |
| --- | --- | --- |
| `adapt-mdd` | Собрать снимок `mdd_v1` из zip | Обычно не нужна: это уже делает Docker `build`. Нужна при локальной пересборке снимка без Docker. |
| `accept` | Приёмочная статистика K1 → `acceptance.md` | **Да, после Docker `build` (или после `adapt-mdd`).** Нужны Python и зависимости; Qdrant не нужен. |
| `chunk` | Нарезать снимок → `chunks.jsonl` | Обычно не нужна после Docker `build`. Нужна, если меняли нарезку и пересобираете локально. |
| `embed` | Посчитать векторы → `vectors.jsonl` | Обычно не нужна после Docker `build`. Нужна при локальном пересчёте векторов. |
| `index` | Залить фрагменты и векторы в Qdrant + `index_info.json` | **Да, после Docker `build`.** Docker в Qdrant не пишет. Нужны Python, зависимости и `.env`. |
| `quality` | Отчёт `quality_report.md` и локальные ворота K2 | **Да, после Docker `build` (или после `chunk`).** Нужны Python и зависимости; Qdrant не обязателен. Запускать до `alias`. |
| `all` | Сразу `chunk` + `quality` + `embed` + `index` | После Docker обычно не нужна (снова режет и считает векторы). Удобна, если собираете всё локально без Docker. |
| `alias` | Второе имя коллекции, например `mdd_current` | **Да, после `index` и `quality`.** Нужны Python, зависимости и `.env`. |
| `snapshot` | Резервная копия коллекции в Qdrant | По желанию, после `index`, перед демо или пересборкой базы. Нужны Python, зависимости и `.env`. |

### После Docker: запись в Qdrant

Нужны локальные зависимости и файл `.env` (в git не коммитится):

```text
python -m pip install -r requirements.txt
```

PowerShell:

```text
$env:PYTHONPATH = "packages;."
```

В `.env`:

```text
QDRANT_URL=...
QDRANT_API_KEY=...
```

Затем:

```text
python ingest.py quality --collection mdd_chunks_v1 --snapshot data/snapshots/mdd_v1
python ingest.py index --collection mdd_chunks_v1
python ingest.py alias --collection mdd_chunks_v1 --alias mdd_current
```

`quality` пишет `data/index/mdd_chunks_v1/quality_report.md` (статистика, гистограмма длин, `dup_ratio`, топ-20 повторов) и проверяет локальные ворота K2. На mdd ненулевой `dup_ratio` ожидаем и только фиксируем.

По желанию бэкап коллекции:

```text
python ingest.py snapshot --collection mdd_chunks_v1
```

Скрипт `python upload_db.py` делает ту же заливку, что `index`, и оставлен для совместимости.

### Локальная пересборка без Docker

Если Python и `PYTHONPATH` уже настроены, весь конвейер можно гнать без Docker:

```text
python ingest.py adapt-mdd --out data/snapshots/mdd_v1
python ingest.py all --snapshot data/snapshots/mdd_v1 --collection mdd_chunks_v1 --config configs/chunking/mdd_sections_512.yaml
python ingest.py alias --collection mdd_chunks_v1 --alias mdd_current
```

Отдельные шаги:

```text
python ingest.py chunk --snapshot data/snapshots/mdd_v1 --collection mdd_chunks_v1
python ingest.py embed --collection mdd_chunks_v1
python ingest.py index --collection mdd_chunks_v1
```

## Проверка

После сборки (Docker или локальный ingest) снимок и нарезка лежат на диске. Проверки — отдельно, нужен локальный Python:

```text
python -m pytest
```

## Запуск поиска

Поиск идёт отдельно, после того как точки уже лежат в коллекции `mdd_chunks_v1`. В `.env` нужны адрес кластера и ключ.

```text
python retrieve.py "How do I apply for disability benefits?"
```

Без аргумента скрипт спросит строку сам. Нужны видеокарта и уже загруженные точки. Модель ответа при первом запуске скачивается с Hugging Face.

## Архив

`data/cache/multidoc2dial.zip` — официальная копия архива MultiDoc2Dial, около 6,6 МБ. Архив не распаковывать: документы читаются из zip в памяти.

Источник: https://doc2dial.github.io/multidoc2dial/file/multidoc2dial.zip

Цитирование: Feng et al., «MultiDoc2Dial: Modeling Dialogues Grounded in Multiple Documents», EMNLP 2021.
