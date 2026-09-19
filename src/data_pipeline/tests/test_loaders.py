"""Tests for FAERS ASCII ingestion (loaders + validation)."""

from __future__ import annotations

import pandas as pd
import pytest

from data_pipeline.config import PipelineConfig
from data_pipeline.loaders import load_all, load_deleted_cases, load_faers_table
from data_pipeline.validation import EmptyFileError, MissingFileError, SchemaError


def test_load_synthetic_demo(tmp_faers_dir):
    from data_pipeline.config import build_table_specs
    df, stats = load_faers_table(tmp_faers_dir / "DEMO26Q1.txt", build_table_specs("2026Q1")["DEMO"])
    assert len(df) == 5
    assert stats.loaded_rows == 5
    assert stats.skipped_bad_lines == 0
    assert stats.malformed_rows_kept == 0
    assert list(df.columns) == list(build_table_specs("2026Q1")["DEMO"].columns)


def test_load_all_counts(test_config):
    raw = load_all(test_config)
    assert len(raw.demo) == 5
    assert len(raw.drug) == 10
    assert len(raw.reac) == 7
    assert len(raw.outc) == 5
    assert list(raw.load_stats) == ["DEMO", "DRUG", "REAC", "OUTC"]


def test_outc_rows_are_loaded_by_primaryid(test_config):
    raw = load_all(test_config)
    assert raw.outc.set_index("primaryid").loc["R001", "outc_cod"] == "DE"
    assert raw.outc.set_index("primaryid").loc["R005", "outc_cod"] == "LT"


def test_missing_file_raises(tmp_path):
    from data_pipeline.config import build_table_specs
    with pytest.raises(MissingFileError):
        load_faers_table(tmp_path / "nope.txt", build_table_specs("2026Q1")["DEMO"])


def test_empty_file_raises(tmp_path):
    from data_pipeline.config import build_table_specs
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    with pytest.raises(EmptyFileError):
        load_faers_table(p, build_table_specs("2026Q1")["DEMO"])


def test_mismatched_header_raises(tmp_path):
    from data_pipeline.config import build_table_specs
    p = tmp_path / "bad.txt"
    p.write_text("primaryid$caseid$totally_wrong\n1$2$3\n", encoding="utf-8")
    with pytest.raises(SchemaError):
        load_faers_table(p, build_table_specs("2026Q1")["DEMO"])


def test_malformed_rows_are_counted_not_silent(tmp_path):
    from data_pipeline.config import build_table_specs
    spec = build_table_specs("2026Q1")["DEMO"]
    path = tmp_path / "demo.txt"
    lines = [
        "primaryid$caseid$caseversion$i_f_code$event_dt$mfr_dt$init_fda_dt$fda_dt$rept_cod$auth_num$mfr_num$mfr_sndr$lit_ref$age$age_cod$age_grp$sex$e_sub$wt$wt_cod$rept_dt$to_mfr$occp_cod$reporter_country$occr_country",
        "good1$C1$1$F$20260101$20260102$20260103$20260104$EXP$$M1$X$$33$YR$$M$Y$$$20260102$$HP$US$US",
        "short_row$C2$1",   # ragged -> malformed
        "good2$C3$1$F$20260101$20260102$20260103$20260104$EXP$$M2$X$$40$YR$$F$Y$$$20260102$$HP$US$US",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")

    df, stats = load_faers_table(path, spec)
    # ragged row has 3 fields ≠ 25 expected → skipped and counted
    assert len(df) == 2
    assert stats.skipped_bad_lines == 1
    assert stats.malformed_rows_kept == 0
    assert stats.rejected_rows == stats.skipped_bad_lines + stats.malformed_rows_kept
    assert stats.accepted_rows == 2


def test_deleted_cases_parsed(tmp_path):
    p = tmp_path / "DELETE26Q1.txt"
    p.write_text("1111\n2222\n", encoding="utf-8")
    assert load_deleted_cases(p) == {"1111", "2222"}


def test_load_all_rejects_missing_required(test_config, tmp_faers_dir):
    (tmp_faers_dir / "DRUG26Q1.txt").unlink()
    with pytest.raises(MissingFileError):
        load_all(test_config)