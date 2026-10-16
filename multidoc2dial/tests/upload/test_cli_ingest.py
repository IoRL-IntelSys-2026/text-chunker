"""CLI ingest: справка и локальные шаги без Qdrant."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from preprocessing.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_ingest_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in (
        "adapt-mdd",
        "accept",
        "chunk",
        "embed",
        "index",
        "quality",
        "all",
        "alias",
        "snapshot",
    ):
        assert name in result.stdout


def test_adapt_mdd_writes_snapshot(tmp_path: Path) -> None:
    archive = ROOT / "data" / "cache" / "multidoc2dial.zip"
    if not archive.is_file():
        return
    out = tmp_path / "mdd_v1"
    result = runner.invoke(
        app,
        ["adapt-mdd", "--archive", str(archive), "--out", str(out)],
    )
    assert result.exit_code == 0, result.stdout
    assert (out / "manifest.jsonl").is_file()
    assert (out / "snapshot_info.json").is_file()
    assert (out / "pages").is_dir()
    assert (out / "structure").is_dir()


def test_set_alias_operations_without_existing(monkeypatch) -> None:
    from preprocessing import index as index_mod

    class FakeAliases:
        aliases = []

    class FakeClient:
        def collection_exists(self, name: str) -> bool:
            return True

        def get_aliases(self):
            return FakeAliases()

        def update_collection_aliases(self, change_aliases_operations):
            self.ops = change_aliases_operations

    client = FakeClient()
    index_mod.set_alias(collection="mdd_chunks_v1", alias="mdd_current", client=client)
    assert len(client.ops) == 1
