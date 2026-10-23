"""
Преобразование PDF через LlamaIndex.

Что делает скрипт:
  1. берёт PDF из папки INPUT_DIR (все или только из списка MY_FILES);
  2. для каждого PDF сохраняет .md и .json в OUTPUT_DIR;
  3. собирает llama_index.jsonl из ВСЕХ .json в папке (одна строка = один PDF);
  4. пишет мини-отчёт report.txt: версии, параметры, статистика, предупреждения.
     Раздел «ЗАМЕЧЕННЫЕ ОШИБКИ» заполняется вручную и при повторном запуске НЕ стирается.

"""

import json
import platform
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from llama_index.core import SimpleDirectoryReader

# ================== НАСТРОЙКИ ==================
INPUT_DIR = Path("docs/llama_index_pdf_files")   #где лежат исходные PDF
OUTPUT_DIR = Path("LLAMA_INDEX_PDF_V1")          #должна лежать РЯДОМ с multidoc2dial
MY_FILES = sorted(p.name for p in INPUT_DIR.glob("*.pdf")) [0:11]  #если пустой список — берём все PDF
MIN_CHARS = 200      #если текста меньше — помечаем как подозрительный (возможно, скан)
# ===============================================

MD_DIR = OUTPUT_DIR / "md"
JSON_DIR = OUTPUT_DIR / "json"
JSONL_FILE = OUTPUT_DIR / "llama_index.jsonl"
REPORT_FILE = OUTPUT_DIR / "report.txt"
MANUAL_MARKER = "=== ЗАМЕЧЕННЫЕ ОШИБКИ И ПОТЕРИ (заполнить вручную) ==="


def pkg_version(name):
    try:
        return version(name)
    except PackageNotFoundError:
        return "не установлен"


VERSIONS = {
    "python": platform.python_version(),
    "llama-index-core": pkg_version("llama-index-core"),
    "llama-index-readers-file": pkg_version("llama-index-readers-file"),
    "pypdf": pkg_version("pypdf"),
}
READER_NAME = "SimpleDirectoryReader (PDFReader, pypdf)"

MD_DIR.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)

# ---------- 1. Читаем PDF ----------
if MY_FILES:
    reader = SimpleDirectoryReader(input_files=[str(INPUT_DIR / f) for f in MY_FILES])
else:
    reader = SimpleDirectoryReader(input_dir=str(INPUT_DIR), required_exts=[".pdf"])
documents = reader.load_data()

# LlamaIndex делит PDF на страницы — собираем страницы обратно по файлам
files = {}
for doc in documents:
    name = doc.metadata.get("file_name", "unknown.pdf")
    files.setdefault(name, []).append(doc.text)

# ---------- 2. Сохраняем .md и .json по каждому PDF ----------
now = datetime.now().isoformat(timespec="seconds")
for name, pages in files.items():
    text = "\n\n".join(pages).strip()
    stem = Path(name).stem

    (MD_DIR / f"{stem}.md").write_text(f"# {name}\n\n{text}\n", encoding="utf-8")

    record = {
        "doc_id": stem,
        "file_name": name,
        "source_path": str(INPUT_DIR / name).replace("\\", "/"),
        "num_pages": len(pages),
        "num_chars": len(text),
        "tool": "llama_index",
        "tool_version": VERSIONS["llama-index-core"],
        "reader": READER_NAME,
        "created_at": now,
        "text": text,
    }
    (JSON_DIR / f"{stem}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Готово: {name} ({len(pages)} стр., {len(text)} символов)")

# ---------- 3. Собираем jsonl из всех .json (весь набор) ----------
records = [
    json.loads(p.read_text(encoding="utf-8")) for p in sorted(JSON_DIR.glob("*.json"))
]
with open(JSONL_FILE, "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# ---------- 4. Мини-отчёт ----------
manual_part = "\n(пример: doc3.pdf, стр. 2 — таблица превратилась в сплошной текст)\n"
if REPORT_FILE.exists():
    old = REPORT_FILE.read_text(encoding="utf-8")
    if MANUAL_MARKER in old:
        manual_part = old.split(MANUAL_MARKER, 1)[1]

pdf_names = sorted(p.name for p in INPUT_DIR.glob("*.pdf"))
done = {r["file_name"] for r in records}
missing = [n for n in pdf_names if n not in done]
suspicious = [r for r in records if r["num_chars"] < MIN_CHARS]

lines = [
    "МИНИ-ОТЧЁТ: преобразование PDF через LlamaIndex",
    f"Дата последнего запуска: {now}",
    "",
    "=== ВЕРСИИ ===",
    *[f"{k}: {v}" for k, v in VERSIONS.items()],
    "",
    "=== ПАРАМЕТРЫ ЗАПУСКА ===",
    f"reader: {READER_NAME}",
    f"input_dir: {INPUT_DIR}",
    f"output_dir: {OUTPUT_DIR}",
    "страницы PDF склеиваются через пустую строку",
    f"порог подозрительно короткого текста: {MIN_CHARS} символов",
    "",
    "=== СТАТИСТИКА ===",
    f"PDF в наборе: {len(pdf_names)}",
    f"Преобразовано (строк в jsonl): {len(records)}",
    f"Ещё не преобразованы: {', '.join(missing) if missing else 'нет'}",
    "",
    "=== ПО ДОКУМЕНТАМ ===",
    *[f"{r['file_name']}: {r['num_pages']} стр., {r['num_chars']} символов" for r in records],
    "",
    "=== АВТОМАТИЧЕСКИЕ ПРЕДУПРЕЖДЕНИЯ ===",
    *(
        [f"{r['file_name']}: очень мало текста ({r['num_chars']}) — возможно, скан" for r in suspicious]
        or ["нет"]
    ),
    "",
    MANUAL_MARKER,
]
REPORT_FILE.write_text("\n".join(lines) + manual_part, encoding="utf-8")

print(f"\nВ jsonl: {len(records)} из {len(pdf_names)} PDF. Отчёт: {REPORT_FILE}")
