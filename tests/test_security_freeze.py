"""Tests for lumina.systools.security_freeze covering previously uncovered branches."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import lumina.systools.security_freeze as sf_mod


# ─────────────────────────────────────────────────────────────
# load_ledger
# ─────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_load_ledger_nonexistent_file(tmp_path):
    result = sf_mod.load_ledger(tmp_path / "missing.jsonl")
    assert result == []


@pytest.mark.unit
def test_load_ledger_valid_records(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    rec1 = {"record_id": "r1", "prev_record_hash": "genesis"}
    rec2 = {"record_id": "r2", "prev_record_hash": "hash1"}
    ledger.write_text(json.dumps(rec1) + "\n" + json.dumps(rec2) + "\n", encoding="utf-8")
    records = sf_mod.load_ledger(ledger)
    assert len(records) == 2
    assert records[0]["record_id"] == "r1"


@pytest.mark.unit
def test_load_ledger_empty_lines_skipped(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    rec = {"record_id": "r1", "prev_record_hash": "genesis"}
    ledger.write_text("\n" + json.dumps(rec) + "\n\n", encoding="utf-8")
    records = sf_mod.load_ledger(ledger)
    assert len(records) == 1


@pytest.mark.unit
def test_load_ledger_invalid_json_prints_warning_and_continues(tmp_path, capsys):
    """Invalid JSON lines print WARNING to stderr and are skipped (no sys.exit)."""
    ledger = tmp_path / "ledger.jsonl"
    rec = {"record_id": "r1", "prev_record_hash": "genesis"}
    ledger.write_text(json.dumps(rec) + "\nINVALID JSON HERE\n", encoding="utf-8")
    records = sf_mod.load_ledger(ledger)
    # Only valid record is returned
    assert len(records) == 1
    assert records[0]["record_id"] == "r1"
    # Warning printed to stderr
    captured = capsys.readouterr()
    assert "WARNING" in captured.err


# ─────────────────────────────────────────────────────────────
# verify_chain
# ─────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_verify_chain_empty_records():
    result = sf_mod.verify_chain([])
    assert result["intact"] is True
    assert result["records_checked"] == 0


@pytest.mark.unit
def test_verify_chain_first_not_genesis():
    records = [{"record_id": "r1", "prev_record_hash": "not-genesis"}]
    result = sf_mod.verify_chain(records)
    assert result["intact"] is False
    assert result["records_checked"] == 1
    assert result["first_broken_id"] == "r1"


@pytest.mark.unit
def test_verify_chain_single_intact():
    records = [{"record_id": "r1", "prev_record_hash": "genesis"}]
    result = sf_mod.verify_chain(records)
    assert result["intact"] is True
    assert result["records_checked"] == 1


@pytest.mark.unit
def test_verify_chain_hash_mismatch():
    rec1 = {"record_id": "r1", "prev_record_hash": "genesis"}
    rec2 = {"record_id": "r2", "prev_record_hash": "wrong-hash"}
    result = sf_mod.verify_chain([rec1, rec2])
    assert result["intact"] is False
    assert result["first_broken_id"] == "r2"
    assert "mismatch" in result["error"].lower()


@pytest.mark.unit
def test_verify_chain_two_intact():
    rec1 = {"record_id": "r1", "prev_record_hash": "genesis"}
    prev_hash = sf_mod.hash_record(rec1)
    rec2 = {"record_id": "r2", "prev_record_hash": prev_hash}
    result = sf_mod.verify_chain([rec1, rec2])
    assert result["intact"] is True
    assert result["records_checked"] == 2


# ─────────────────────────────────────────────────────────────
# run_security_freeze
# ─────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_run_security_freeze_no_ledger_files(tmp_path):
    """Returns 1 when no .jsonl files found."""
    result = sf_mod.run_security_freeze("actor-001", tmp_path, "test reason")
    assert result == 1


@pytest.mark.unit
def test_run_security_freeze_abort_on_wrong_confirmation(tmp_path):
    """Returns 1 when confirmation text is not 'FREEZE'."""
    ledger = tmp_path / "session.jsonl"
    rec = {"record_id": "r1", "prev_record_hash": "genesis"}
    ledger.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    with patch("builtins.input", return_value="no"):
        result = sf_mod.run_security_freeze("actor-001", tmp_path, "test reason")
    assert result == 1


@pytest.mark.unit
def test_run_security_freeze_confirmed_intact_returns_zero(tmp_path):
    """Returns 0 when all ledger chains are intact and confirmation is 'FREEZE'."""
    ledger = tmp_path / "session.jsonl"
    rec = {"record_id": "r1", "prev_record_hash": "genesis"}
    ledger.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    with patch("builtins.input", return_value="FREEZE"):
        result = sf_mod.run_security_freeze("actor-001", tmp_path, "test reason")
    assert result == 0
    # Freeze record should be appended
    lines = ledger.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    freeze_record = json.loads(lines[1])
    assert freeze_record["record_type"] == "CommitmentRecord"
    assert freeze_record["commitment_type"] == "policy_change"
    assert "security_freeze" in freeze_record["metadata"]["action"]


@pytest.mark.unit
def test_run_security_freeze_broken_chain_returns_two(tmp_path):
    """Returns 2 when chains have integrity issues but freeze still completes."""
    ledger = tmp_path / "session.jsonl"
    rec = {"record_id": "r1", "prev_record_hash": "NOT_GENESIS"}
    ledger.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    with patch("builtins.input", return_value="FREEZE"):
        result = sf_mod.run_security_freeze("actor-001", tmp_path, "test reason")
    assert result == 2


@pytest.mark.unit
def test_run_security_freeze_empty_ledger_uses_genesis_as_prev(tmp_path):
    """Empty ledger file: freeze record uses 'genesis' as prev_record_hash."""
    ledger = tmp_path / "empty.jsonl"
    ledger.write_text("", encoding="utf-8")
    with patch("builtins.input", return_value="FREEZE"):
        result = sf_mod.run_security_freeze("actor-001", tmp_path, "empty test")
    assert result == 0
    lines = ledger.read_text(encoding="utf-8").strip().splitlines()
    freeze_record = json.loads(lines[0])
    assert freeze_record["prev_record_hash"] == "genesis"


# ─────────────────────────────────────────────────────────────
# main() — CLI entry point
# ─────────────────────────────────────────────────────────────

@pytest.mark.unit
def test_main_runs_and_exits(tmp_path):
    """main() parses args and calls run_security_freeze, exiting with its return code."""
    ledger = tmp_path / "session.jsonl"
    rec = {"record_id": "r1", "prev_record_hash": "genesis"}
    ledger.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    with patch("builtins.input", return_value="FREEZE"):
        with patch(
            "sys.argv",
            [
                "security_freeze",
                "--actor-id", "actor-001",
                "--ledger-dir", str(tmp_path),
                "--reason", "test freeze",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                sf_mod.main()
    assert exc_info.value.code == 0
