# Один документ: от текста в архиве до поиска

Берём одну короткую страницу и проводим её по тем же шагам, что и остальные 488. В архиве ключи те же. В этом рассказе в `doc_data` лежит только она.

Страница Social Security про онлайн-калькулятор пенсии. Исходный номер: `Benefits Planner: Retirement | Online Calculator (WEP Version)#1_0`. Наш номер, им названы файлы: `39cf5068-d272-54a5-9636-48ffc46052ff`.

Паспорт снимка и паспорт базы считают весь учебный набор: 488 документов и 7149 фрагментов. Эта страница — одна из них.

## Текст, который идёт дальше

Так страница лежит в `data/snapshots/mdd_v1/pages/39cf5068-d272-54a5-9636-48ffc46052ff.txt`. Это тот же `doc_text` из архива, байт в байт. Заголовок в начало не дописывался.

```text


Benefits Planner: Retirement 


Online Calculator (WEP Version) 
The calculator shown below allows you to estimate your Social Security benefit. However , for the most accurate estimates , use the Detailed Calculator. You need to enter all your past earnings, which are shown on your online. Please Note: The Online Calculator is updated periodically * with new benefit increases and other benefit amounts. Therefore , it is likely that your benefit estimates in the future will differ from those calculated today. The Online Calculator works on PCs and Macs with Javascript enabled. Some browsers may not allow you to print the table below. Note: If your birthday is on January 1st , we figure your benefit as if your birthday was in the previous year. If you qualify for benefits as a Survivor , your full retirement age for survivors benefits may be different. 
```

Из этого текста получаются четыре фрагмента. Заголовки в начале в поиск не попадают: это только название, без абзаца. Фраза про прошлые заработки короче 24 токенов, поэтому она склеивается с абзацем перед ней. Длиннее 512 токенов здесь ничего нет, внутри абзаца текст не резали.

```text
Benefits Planner: Retirement
    только заголовок, 10 токенов → в фрагменты не входит

Online Calculator (WEP Version)
    только заголовок, 9 токенов → в фрагменты не входит

The calculator shown below allows you to estimate your Social Security benefit. However , for the most accurate estimates , use the Detailed Calculator.
You need to enter all your past earnings, which are shown on your online.
    33 токена и 18 токенов, один заголовок раздела → фрагмент 0, символы 67–294

Please Note: The Online Calculator is updated periodically * with new benefit increases and other benefit amounts. Therefore , it is likely that your benefit estimates in the future will differ from those calculated today. The Online Calculator works on PCs and Macs with Javascript enabled. Some browsers may not allow you to print the table below.
    фрагмент 1, символы 294–644

Note: If your birthday is on January 1st , we figure your benefit as if your birthday was in the previous year.
    фрагмент 2, символы 644–756

If you qualify for benefits as a Survivor , your full retirement age for survivors benefits may be different.
    фрагмент 3, символы 756–866
```

Ниже те же слова проходят по файлам проекта: сначала JSON архива и его `spans`, потом снимок, потом строка фрагмента, потом векторы и поиск.

## JSON в архиве

Файл `data/cache/multidoc2dial.zip` на диск не распаковывается. Сначала sha256 всего zip сверяется с суммой в коде: `f0c034c249663d7b3cb08b19cf2cc2c3d101372485be982621d4711931a1ce00`. После этого из архива в памяти читается `multidoc2dial/multidoc2dial_doc.json`.

Верх файла — ключ `doc_data`. Внутри тема `ssa`, внутри неё исходный номер, внутри карточка.

`title` — заголовок. В конце `#1`: так архив отличает одноимённые страницы. `doc_id` в этой карточке — ещё исходный номер, с пробелами, `|` и `#`. `domain` — тема. `doc_text` — текст выше.

`spans` — разметка этого текста. Ключ `"1"`, `"2"`, … `"18"` — номер мелкого куска. В каждом куске одни и те же поля:

- `id_sp`, `tag` — номер и метка. `h2` и `h3` — заголовки, `u` — кусок абзаца.
- `start_sp`, `end_sp`, `text_sp` — где этот мелкий кусок лежит в `doc_text` и какой у него текст.
- `title` — заголовок раздела, к которому кусок относится.
- `parent_titles` — заголовки выше. У элемента три поля: `id_sp`, `text`, `level`. У большинства кусков список пустой. Заполнен он у второго заголовка.
- `id_sec`, `start_sec`, `end_sec`, `text_sec` — номер раздела и его границы. Несколько кусков с одним `id_sec` — это один раздел: у них одинаковые `start_sec`, `end_sec` и `text_sec`, а `text_sp` — только свой кусочек.

Так эта карточка лежит в архиве. Следом за `spans` в том же объекте есть `doc_html_ts` и `doc_html_raw`: это HTML страницы, в файлы снимка он не пишется.

```json
{
  "doc_data": {
    "ssa": {
      "Benefits Planner: Retirement | Online Calculator (WEP Version)#1_0": {
        "title": "Benefits Planner: Retirement | Online Calculator (WEP Version)#1",
        "doc_id": "Benefits Planner: Retirement | Online Calculator (WEP Version)#1_0",
        "domain": "ssa",
        "doc_text": "\n\nBenefits Planner: Retirement \n\n\nOnline Calculator (WEP Version) \nThe calculator shown below allows you to estimate your Social Security benefit. However , for the most accurate estimates , use the Detailed Calculator. You need to enter all your past earnings, which are shown on your online. Please Note: The Online Calculator is updated periodically * with new benefit increases and other benefit amounts. Therefore , it is likely that your benefit estimates in the future will differ from those calculated today. The Online Calculator works on PCs and Macs with Javascript enabled. Some browsers may not allow you to print the table below. Note: If your birthday is on January 1st , we figure your benefit as if your birthday was in the previous year. If you qualify for benefits as a Survivor , your full retirement age for survivors benefits may be different. ",
        "spans": {
          "1": {
            "id_sp": "1",
            "tag": "h2",
            "start_sp": 0,
            "end_sp": 32,
            "text_sp": "\n\nBenefits Planner: Retirement \n",
            "title": "Benefits Planner: Retirement",
            "parent_titles": [],
            "id_sec": "t_0",
            "start_sec": 0,
            "end_sec": 32,
            "text_sec": "\n\nBenefits Planner: Retirement \n"
          },
          "2": {
            "id_sp": "2",
            "tag": "h3",
            "start_sp": 32,
            "end_sp": 67,
            "text_sp": "\n\nOnline Calculator (WEP Version) \n",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [
              {
                "id_sp": "1",
                "text": "Benefits Planner: Retirement",
                "level": "h2"
              }
            ],
            "id_sec": "t_1",
            "start_sec": 32,
            "end_sec": 67,
            "text_sec": "\n\nOnline Calculator (WEP Version) \n"
          },
          "3": {
            "id_sp": "3",
            "tag": "u",
            "start_sp": 67,
            "end_sp": 147,
            "text_sp": "The calculator shown below allows you to estimate your Social Security benefit. ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "1",
            "start_sec": 67,
            "text_sec": "The calculator shown below allows you to estimate your Social Security benefit. However , for the most accurate estimates , use the Detailed Calculator. ",
            "end_sec": 220
          },
          "4": {
            "id_sp": "4",
            "tag": "u",
            "start_sp": 147,
            "end_sp": 157,
            "text_sp": "However , ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "1",
            "start_sec": 67,
            "text_sec": "The calculator shown below allows you to estimate your Social Security benefit. However , for the most accurate estimates , use the Detailed Calculator. ",
            "end_sec": 220
          },
          "5": {
            "id_sp": "5",
            "tag": "u",
            "start_sp": 157,
            "end_sp": 191,
            "text_sp": "for the most accurate estimates , ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "1",
            "start_sec": 67,
            "text_sec": "The calculator shown below allows you to estimate your Social Security benefit. However , for the most accurate estimates , use the Detailed Calculator. ",
            "end_sec": 220
          },
          "6": {
            "id_sp": "6",
            "tag": "u",
            "start_sp": 191,
            "end_sp": 220,
            "text_sp": "use the Detailed Calculator. ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "1",
            "start_sec": 67,
            "text_sec": "The calculator shown below allows you to estimate your Social Security benefit. However , for the most accurate estimates , use the Detailed Calculator. ",
            "end_sec": 220
          },
          "7": {
            "id_sp": "7",
            "tag": "u",
            "start_sp": 220,
            "end_sp": 294,
            "text_sp": "You need to enter all your past earnings, which are shown on your online. ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "2",
            "start_sec": 220,
            "text_sec": "You need to enter all your past earnings, which are shown on your online. ",
            "end_sec": 294
          },
          "8": {
            "id_sp": "8",
            "tag": "u",
            "start_sp": 294,
            "end_sp": 307,
            "text_sp": "Please Note: ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "3",
            "start_sec": 294,
            "text_sec": "Please Note: The Online Calculator is updated periodically * with new benefit increases and other benefit amounts. Therefore , it is likely that your benefit estimates in the future will differ from those calculated today. The Online Calculator works on PCs and Macs with Javascript enabled. Some browsers may not allow you to print the table below. ",
            "end_sec": 644
          },
          "9": {
            "id_sp": "9",
            "tag": "u",
            "start_sp": 307,
            "end_sp": 409,
            "text_sp": "The Online Calculator is updated periodically * with new benefit increases and other benefit amounts. ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "3",
            "start_sec": 294,
            "text_sec": "Please Note: The Online Calculator is updated periodically * with new benefit increases and other benefit amounts. Therefore , it is likely that your benefit estimates in the future will differ from those calculated today. The Online Calculator works on PCs and Macs with Javascript enabled. Some browsers may not allow you to print the table below. ",
            "end_sec": 644
          },
          "10": {
            "id_sp": "10",
            "tag": "u",
            "start_sp": 409,
            "end_sp": 421,
            "text_sp": "Therefore , ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "3",
            "start_sec": 294,
            "text_sec": "Please Note: The Online Calculator is updated periodically * with new benefit increases and other benefit amounts. Therefore , it is likely that your benefit estimates in the future will differ from those calculated today. The Online Calculator works on PCs and Macs with Javascript enabled. Some browsers may not allow you to print the table below. ",
            "end_sec": 644
          },
          "11": {
            "id_sp": "11",
            "tag": "u",
            "start_sp": 421,
            "end_sp": 517,
            "text_sp": "it is likely that your benefit estimates in the future will differ from those calculated today. ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "3",
            "start_sec": 294,
            "text_sec": "Please Note: The Online Calculator is updated periodically * with new benefit increases and other benefit amounts. Therefore , it is likely that your benefit estimates in the future will differ from those calculated today. The Online Calculator works on PCs and Macs with Javascript enabled. Some browsers may not allow you to print the table below. ",
            "end_sec": 644
          },
          "12": {
            "id_sp": "12",
            "tag": "u",
            "start_sp": 517,
            "end_sp": 586,
            "text_sp": "The Online Calculator works on PCs and Macs with Javascript enabled. ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "3",
            "start_sec": 294,
            "text_sec": "Please Note: The Online Calculator is updated periodically * with new benefit increases and other benefit amounts. Therefore , it is likely that your benefit estimates in the future will differ from those calculated today. The Online Calculator works on PCs and Macs with Javascript enabled. Some browsers may not allow you to print the table below. ",
            "end_sec": 644
          },
          "13": {
            "id_sp": "13",
            "tag": "u",
            "start_sp": 586,
            "end_sp": 644,
            "text_sp": "Some browsers may not allow you to print the table below. ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "3",
            "start_sec": 294,
            "text_sec": "Please Note: The Online Calculator is updated periodically * with new benefit increases and other benefit amounts. Therefore , it is likely that your benefit estimates in the future will differ from those calculated today. The Online Calculator works on PCs and Macs with Javascript enabled. Some browsers may not allow you to print the table below. ",
            "end_sec": 644
          },
          "14": {
            "id_sp": "14",
            "tag": "u",
            "start_sp": 644,
            "end_sp": 650,
            "text_sp": "Note: ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "4",
            "start_sec": 644,
            "text_sec": "Note: If your birthday is on January 1st , we figure your benefit as if your birthday was in the previous year. ",
            "end_sec": 756
          },
          "15": {
            "id_sp": "15",
            "tag": "u",
            "start_sp": 650,
            "end_sp": 687,
            "text_sp": "If your birthday is on January 1st , ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "4",
            "start_sec": 644,
            "text_sec": "Note: If your birthday is on January 1st , we figure your benefit as if your birthday was in the previous year. ",
            "end_sec": 756
          },
          "16": {
            "id_sp": "16",
            "tag": "u",
            "start_sp": 687,
            "end_sp": 756,
            "text_sp": "we figure your benefit as if your birthday was in the previous year. ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "4",
            "start_sec": 644,
            "text_sec": "Note: If your birthday is on January 1st , we figure your benefit as if your birthday was in the previous year. ",
            "end_sec": 756
          },
          "17": {
            "id_sp": "17",
            "tag": "u",
            "start_sp": 756,
            "end_sp": 800,
            "text_sp": "If you qualify for benefits as a Survivor , ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "5",
            "start_sec": 756,
            "text_sec": "If you qualify for benefits as a Survivor , your full retirement age for survivors benefits may be different. ",
            "end_sec": 866
          },
          "18": {
            "id_sp": "18",
            "tag": "u",
            "start_sp": 800,
            "end_sp": 866,
            "text_sp": "your full retirement age for survivors benefits may be different. ",
            "title": "Online Calculator (WEP Version)",
            "parent_titles": [],
            "id_sec": "5",
            "start_sec": 756,
            "text_sec": "If you qualify for benefits as a Survivor , your full retirement age for survivors benefits may be different. ",
            "end_sec": 866
          }
        }
      }
    }
  }
}
```

Куски `"3"`, `"4"`, `"5"` и `"6"` делят один раздел `id_sec` `"1"`: границы `67–220`, а `text_sp` у каждого свой. Из таких групп дальше собирается файл разделов. Сами `text_sp` в тот файл не пишутся.

## Номер и файлы снимка

Из темы и исходного номера собирается адрес. Пробел, `|` и `#` в имени файла нельзя, поэтому они кодируются. `%20` — пробел, `%7C` — `|`, `%23` — `#`.

```text
mdd://ssa/Benefits%20Planner%3A%20Retirement%20%7C%20Online%20Calculator%20%28WEP%20Version%29%231_0
```

`doc_id` — uuid5 от этого адреса: `39cf5068-d272-54a5-9636-48ffc46052ff`. Повтор даёт тот же номер. Исходный номер остаётся в описи, потому что диалоги архива ссылаются на него.

Текст уже показан: `data/snapshots/mdd_v1/pages/39cf5068-d272-54a5-9636-48ffc46052ff.txt`.

Текст страницы лежит в `data/snapshots/mdd_v1/pages/39cf5068-d272-54a5-9636-48ffc46052ff.txt`:

```text


Benefits Planner: Retirement 


Online Calculator (WEP Version) 
The calculator shown below allows you to estimate your Social Security benefit. However , for the most accurate estimates , use the Detailed Calculator. You need to enter all your past earnings, which are shown on your online. Please Note: The Online Calculator is updated periodically * with new benefit increases and other benefit amounts. Therefore , it is likely that your benefit estimates in the future will differ from those calculated today. The Online Calculator works on PCs and Macs with Javascript enabled. Some browsers may not allow you to print the table below. Note: If your birthday is on January 1st , we figure your benefit as if your birthday was in the previous year. If you qualify for benefits as a Survivor , your full retirement age for survivors benefits may be different. 
```

Разделы пишутся в `data/snapshots/mdd_v1/structure/39cf5068-d272-54a5-9636-48ffc46052ff.json`. Куски с одним `id_sec` схлопываются. В файле путь заголовков и границы в этом тексте:

```json
[
  {
    "title_path": ["Benefits Planner: Retirement"],
    "char_start": 0,
    "char_end": 32
  },
  {
    "title_path": ["Benefits Planner: Retirement", "Online Calculator (WEP Version)"],
    "char_start": 32,
    "char_end": 67
  },
  {
    "title_path": ["Online Calculator (WEP Version)"],
    "char_start": 67,
    "char_end": 220
  },
  {
    "title_path": ["Online Calculator (WEP Version)"],
    "char_start": 220,
    "char_end": 294
  },
  {
    "title_path": ["Online Calculator (WEP Version)"],
    "char_start": 294,
    "char_end": 644
  },
  {
    "title_path": ["Online Calculator (WEP Version)"],
    "char_start": 644,
    "char_end": 756
  },
  {
    "title_path": ["Online Calculator (WEP Version)"],
    "char_start": 756,
    "char_end": 866
  }
]
```

Первые два раздела — строки заголовков. Остальные пять — абзацы под заголовком `Online Calculator (WEP Version)`. Повтор заголовка здесь нормален: у абзаца тот же заголовок, другие границы.

Опись `data/snapshots/mdd_v1/manifest.jsonl` — одна строка на документ. Строка этой страницы:

```json
{
  "schema_version": "k1.v1",
  "doc_id": "39cf5068-d272-54a5-9636-48ffc46052ff",
  "source": "multidoc2dial",
  "url": "mdd://ssa/Benefits%20Planner%3A%20Retirement%20%7C%20Online%20Calculator%20%28WEP%20Version%29%231_0",
  "aliases": [],
  "source_doc_id": "Benefits Planner: Retirement | Online Calculator (WEP Version)#1_0",
  "title": "Benefits Planner: Retirement | Online Calculator (WEP Version)#1",
  "lang": "en",
  "content_type": "text/plain",
  "path": "pages/39cf5068-d272-54a5-9636-48ffc46052ff.txt",
  "content_hash": "5001abaf2583147c85bcb5f608557f8156372b35cc75e92cd5ced2c04bfd5293",
  "section": "ssa",
  "fetched_at": "2026-09-30T00:00:00Z",
  "last_modified": null
}
```

`content_hash` — sha256 текста после лёгкой подготовки к сравнению: ё приводится к е, убираются неразрывный пробел и мягкий перенос, несколько пробелов подряд схлопываются. Файл в `pages/` при этом не меняется. `aliases` пустой. `last_modified` пустой: у архива нет даты правки страницы. `fetched_at` зафиксирован полночью `2026-09-30T00:00:00Z`.

Паспорт всего снимка, `data/snapshots/mdd_v1/snapshot_info.json`:

```json
{
  "schema_version": "k1.v1",
  "adapter_version": "1",
  "archive_sha256": "f0c034c249663d7b3cb08b19cf2cc2c3d101372485be982621d4711931a1ce00",
  "document_count": 488,
  "created_at": "2026-09-30T00:00:00Z"
}
```

В `data/snapshots/mdd_v1/reports/page_stats.jsonl` у этой страницы строка `doc_id`, `depth: 0`, `removed_blocks: 0`, `audience: null`. `sections.json` считает документы по темам. В настоящем снимке ssa — 109, наша страница внутри этого числа. `crawl_stats.json`, `boilerplate_report.json` и `duplicates.json` с нулями: сайт не обходили, снимок собран из архива.

Проверка смотрит имя папки, строку описи, совпадение номера с адресом, файл текста, хеш и границы разделов. Вторая сборка во временную папку дала те же файлы.

## Нарезка в фрагменты

Настройки в `configs/chunking/mdd_sections_512.yaml`: режем по заголовкам (`strategy: md_header`), длина и векторы считает `BAAI/bge-m3`, лимит `max_tokens: 512`, перекрытие `overlap_tokens: 64`, минимум `min_tokens: 24`. Имя нарезки `chunker: mdd-sections+recursive/v1/512/64` входит в номер фрагмента.

Программа читает текст из `pages/`, разделы из `structure/`, заголовок из описи и режет по `char_start`/`char_end`. Получаются те семь кусков, которые уже видны в тексте выше. Два заголовка отбрасываются. Абзац на 18 токенов склеивается с предыдущим. Остаются четыре фрагмента.

У фрагмента два текста. `text` — срез страницы, заголовок документа в него не вклеен. `embed_text` — строка для векторов: заголовок документа, заголовок раздела, пустая строка, затем `text`.

Фрагмент 0 в `data/index/mdd_chunks_v1/chunks.jsonl` — одна такая строка. Векторов в ней нет.

```json
{
  "schema_version": "k2.v1",
  "chunk_id": "e1ab2f02-e704-52c7-95f3-28fa69f3bf67",
  "doc_id": "39cf5068-d272-54a5-9636-48ffc46052ff",
  "source": "multidoc2dial",
  "source_doc_id": "Benefits Planner: Retirement | Online Calculator (WEP Version)#1_0",
  "url": "mdd://ssa/Benefits%20Planner%3A%20Retirement%20%7C%20Online%20Calculator%20%28WEP%20Version%29%231_0",
  "content_type": "text/plain",
  "title": "Benefits Planner: Retirement | Online Calculator (WEP Version)#1",
  "breadcrumbs": [],
  "section": "ssa",
  "lang": "en",
  "headings": ["Online Calculator (WEP Version)"],
  "chunk_index": 0,
  "n_chunks": 4,
  "text": "The calculator shown below allows you to estimate your Social Security benefit. However , for the most accurate estimates , use the Detailed Calculator. You need to enter all your past earnings, which are shown on your online. ",
  "char_start": 67,
  "char_end": 294,
  "embed_text": "Benefits Planner: Retirement | Online Calculator (WEP Version)#1\nOnline Calculator (WEP Version)\n\nThe calculator shown below allows you to estimate your Social Security benefit. However , for the most accurate estimates , use the Detailed Calculator. You need to enter all your past earnings, which are shown on your online. ",
  "token_count": 50,
  "has_generated_text": false,
  "content_hash": "b38c809f670c0532849423b29c603176dac287dc1f55367f9993c0644c30ceab",
  "doc_content_hash": "5001abaf2583147c85bcb5f608557f8156372b35cc75e92cd5ced2c04bfd5293",
  "snapshot_id": "mdd_v1",
  "last_modified": null,
  "last_modified_source": null,
  "fetched_at": "2026-09-30T00:00:00Z",
  "md_path": "pages/39cf5068-d272-54a5-9636-48ffc46052ff.txt",
  "chunker": "mdd-sections+recursive/v1/512/64",
  "embedding_model": "BAAI/bge-m3"
}
```

`chunk_id` — uuid5 от номера документа, имени нарезки и `chunk_index`. Индексы здесь 0, 1, 2, 3. `breadcrumbs` пустой: у учебного снимка нет хлебных крошек сайта. `has_generated_text` равен `false`: текст написан не моделью. `content_hash` — sha256 поля `text`. `doc_content_hash` совпадает с хешем в описи.

Три остальных строки устроены так же. Меняются номер, границы и текст:

```text
1  d2d4a242-88ff-5a9d-9d1a-fe768e37dde2  294–644
   Please Note: The Online Calculator is updated periodically * with new benefit increases and other benefit amounts. Therefore , it is likely that your benefit estimates in the future will differ from those calculated today. The Online Calculator works on PCs and Macs with Javascript enabled. Some browsers may not allow you to print the table below.

2  5c1f3881-72bc-5587-9e89-b4f9037d86eb  644–756
   Note: If your birthday is on January 1st , we figure your benefit as if your birthday was in the previous year.

3  d867a6a5-5796-565c-92f0-eefc26821178  756–866
   If you qualify for benefits as a Survivor , your full retirement age for survivors benefits may be different.
```

Проверка нарезки сверяет срез txt с полем `text` и смотрит, что `embed_text` не длиннее 512 токенов.

## Векторы

Вектор считается по `embed_text`, не по всей строке JSON. Модель `BAAI/bge-m3` за один проход даёт два вектора. Плотный — 1024 числа, по ним ищут близкий смысл. Разреженный — пары «номер токена в словаре модели → вес», по ним ищут те же слова. Нулевые веса в файл не пишутся.

Строка фрагмента 0 в `data/index/mdd_chunks_v1/vectors.jsonl`. В файле списки полные. Здесь начало, чтобы было видно форму:

```json
{
  "chunk_id": "e1ab2f02-e704-52c7-95f3-28fa69f3bf67",
  "dense": [-0.01206, 0.04703, -0.04478],
  "sparse_indices": [7, 47, 67, 70],
  "sparse_values": [0.0650, 0.0818, 0.1233, 0.0051]
}
```

`dense` в файле длиной 1024. Разреженных пар у этого фрагмента 45, у трёх остальных 57, 35 и 36. `sparse_indices` и `sparse_values` одной длины и отсортированы по номеру токена, поэтому первые пары — не самые важные слова, а самые маленькие номера. `chunk_id` совпадает со строкой в `chunks.jsonl`, порядок строк тот же.

## Точка в базе

Коллекция Qdrant называется `mdd_chunks_v1`. Второе имя `mdd_current` отложено, поиск идёт по этому имени. Фрагмент 0 становится одной точкой.

Номер точки — `e1ab2f02-e704-52c7-95f3-28fa69f3bf67`, тот же `chunk_id`. В `vector` кладутся `dense` и `sparse` из строки `vectors.jsonl`. В `payload` копируется вся строка из `chunks.jsonl`, и к ней дописывается `"indexed_at": "2026-10-02T15:52:35Z"`. Векторы в payload не входят. Поиск сравнивает векторы, а наружу вместе с точкой возвращается payload: заголовок, адрес и текст.

Паспорт коллекции `data/index/mdd_chunks_v1/index_info.json` записывается, когда число точек совпало с числом строк фрагментов:

```json
{
  "collection": "mdd_chunks_v1",
  "snapshot_id": "mdd_v1",
  "chunker": "mdd-sections+recursive/v1/512/64",
  "strategy": "md_header",
  "max_tokens": 512,
  "overlap_tokens": 64,
  "min_tokens": 24,
  "embedding_model": "BAAI/bge-m3",
  "embedding_model_revision": "5617a9f61b028005a4858fdac845db406aefb181",
  "document_count": 488,
  "chunk_count": 7149,
  "created_at": "2026-10-02T15:52:35Z"
}
```

## Поиск

`retrieve.py` страницу заново не открывает. Вопрос считается той же моделью bge-m3, без приставки к тексту. Получаются плотный вектор и разреженный. В коллекции `mdd_chunks_v1` берутся 20 ближайших по смыслу и 20 ближайших по словам. Списки склеиваются, RRF с `k = 60`.

Наружу выходит карточка из payload: `score`, `chunk_id`, `title`, `url`, `text`. Если среди близких точек оказывается фрагмент 0, это выглядит так:

```text
title     Benefits Planner: Retirement | Online Calculator (WEP Version)#1
url       mdd://ssa/Benefits%20Planner%3A%20Retirement%20%7C%20Online%20Calculator%20%28WEP%20Version%29%231_0
chunk_id  e1ab2f02-e704-52c7-95f3-28fa69f3bf67
text      The calculator shown below allows you to estimate your Social Security benefit. However , for the most accurate estimates , use the Detailed Calculator. You need to enter all your past earnings, which are shown on your online.
```

`text` снова срез страницы. Проверить его можно в `pages/39cf5068-d272-54a5-9636-48ffc46052ff.txt`, символы с 67 по 294. Заголовок и адрес лежат рядом, чтобы ответ можно было подписать.
