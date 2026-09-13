"""Shared fixtures for member 1 data-pipeline tests.

All synthetic data is explicitly marked as test fixtures, not production data,
in accordance with the project's rule:
  "Do not use synthetic data in the production pipeline unless explicitly
   marked as test fixtures."
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_pipeline.config import PipelineConfig, build_table_specs


HEADER_DEMO = "primaryid$caseid$caseversion$i_f_code$event_dt$mfr_dt$init_fda_dt$fda_dt$rept_cod$auth_num$mfr_num$mfr_sndr$lit_ref$age$age_cod$age_grp$sex$e_sub$wt$wt_cod$rept_dt$to_mfr$occp_cod$reporter_country$occr_country"
HEADER_DRUG = "primaryid$caseid$drug_seq$role_cod$drugname$prod_ai$val_vbm$route$dose_vbm$cum_dose_chr$cum_dose_unit$dechal$rechal$lot_num$exp_dt$nda_num$dose_amt$dose_unit$dose_form$dose_freq"
HEADER_REAC = "primaryid$caseid$pt$drug_rec_act"
HEADER_OUTC = "primaryid$caseid$outc_cod"

SYNTH_DEMO_LINES = [
    HEADER_DEMO,
    "R001$C001$1$F$20260110$20260210$20260301$20260315$EXP$$MFR01$NOVARTIS$$55$YR$$F$Y$$$20260201$$HP$US$US",
    "R002$C002$1$I$20260205$20260215$20260302$20260316$EXP$$MFR02$PFIZER$$62$YR$$M$Y$$$20260210$$HP$US$US",
    "R003$C003$1$F$20260120$20260220$20260303$20260317$EXP$$MFR03$REDDY$$48$YR$$F$Y$$$20260215$$HP$US$US",
    "R004$C004$1$F$$20260212$20260304$20260318$EXP$$MFR04$ROCHE$$73$YR$$M$Y$$$20260211$$HP$US$US",
    "R005$C005$1$F$20260301$20260305$20260306$20260319$EXP$$MFR05$ABBVIE$$41$YR$$F$Y$$$20260302$$HP$US$US",
]
_DRUG_ROW_TEMPLATE = dict(
    primaryid="", caseid="", drug_seq="", role_cod="", drugname="", prod_ai="",
    val_vbm="", route="", dose_vbm="", cum_dose_chr="", cum_dose_unit="",
    dechal="", rechal="", lot_num="", exp_dt="", nda_num="",
    dose_amt="", dose_unit="", dose_form="", dose_freq="",
)


def _drug_line(**kw) -> str:
    row = dict(_DRUG_ROW_TEMPLATE)
    row.update(kw)
    return "$".join([row[k] for k in _DRUG_ROW_TEMPLATE])


SYNTH_DRUG_LINES = [
    HEADER_DRUG,
    _drug_line(primaryid="R001", caseid="C001", drug_seq="1", role_cod="PS",
               drugname="ASPIRIN", prod_ai="ACETYLSALICYLIC ACID", val_vbm="1",
               route="Oral", cum_dose_chr="UNK", dechal="N",
               dose_amt="500mg", dose_unit="Tablet", dose_form="QID"),
    _drug_line(primaryid="R001", caseid="C001", drug_seq="2", role_cod="SS",
               drugname="CLOPIDOGREL", prod_ai="CLOPIDOGREL BESILATE", val_vbm="2",
               route="Oral", cum_dose_chr="UNK", dechal="N",
               dose_amt="75mg", dose_unit="Tablet", dose_form="QD"),
    _drug_line(primaryid="R001", caseid="C001", drug_seq="3", role_cod="C",
               drugname="OMEPRAZOLE", prod_ai="OMEPRAZOLE", val_vbm="3",
               route="Oral", cum_dose_chr="UNK", dechal="N",
               dose_amt="20mg", dose_unit="Capsule", dose_form="QD"),
    _drug_line(primaryid="R002", caseid="C002", drug_seq="1", role_cod="PS",
               drugname="WARFARIN", prod_ai="WARFARIN SODIUM", val_vbm="1",
               route="Oral", cum_dose_chr="UNK", dechal="Y",
               dose_amt="5mg", dose_unit="Tablet", dose_form="QD"),
    _drug_line(primaryid="R002", caseid="C002", drug_seq="2", role_cod="SS",
               drugname="Heparin", prod_ai="HEPARIN", val_vbm="2",
               route="Intravenous", cum_dose_chr="UNK", dechal="N",
               dose_amt="5000", dose_unit="U", dose_form="Solution"),
    _drug_line(primaryid="R003", caseid="C003", drug_seq="1", role_cod="PS",
               drugname="ASPIRIN", prod_ai="ACETYLSALICYLIC ACID", val_vbm="1",
               route="Oral", cum_dose_chr="UNK", dechal="N",
               dose_amt="81mg", dose_unit="Tablet", dose_form="QD"),
    _drug_line(primaryid="R004", caseid="C004", drug_seq="1", role_cod="PS",
               drugname="METFORMIN", prod_ai="METFORMIN HYDROCHLORIDE", val_vbm="1",
               route="Oral", cum_dose_chr="UNK", dechal="N",
               dose_amt="500mg", dose_unit="Tablet", dose_form="BID"),
    _drug_line(primaryid="R004", caseid="C004", drug_seq="2", role_cod="C",
               drugname="Lisinopril", prod_ai="LISINOPRIL", val_vbm="2",
               route="Oral", cum_dose_chr="UNK", dechal="N",
               dose_amt="10mg", dose_unit="Tablet", dose_form="QD"),
    _drug_line(primaryid="R005", caseid="C005", drug_seq="1", role_cod="PS",
               drugname="Warfarin", prod_ai="WARFARIN SODIUM", val_vbm="1",
               route="Oral", cum_dose_chr="UNK", dechal="N",
               dose_amt="7mg", dose_unit="Tablet", dose_form="QD"),
    _drug_line(primaryid="R005", caseid="C005", drug_seq="2", role_cod="DN",
               drugname="unknown_drug", prod_ai="UNKNOWN", val_vbm="2",
               route="Oral", cum_dose_chr="UNK", dechal="N",
               dose_amt="50mg", dose_unit="Tablet", dose_form="QD"),
]
SYNTH_REAC_LINES = [
    HEADER_REAC,
    "R001$C001$Bleeding$",
    "R001$C001$Gastrointestinal bleeding$",
    "R002$C002$Haemorrhage$",
    "R003$C003$Bleeding$",
    "R003$C003$Gastrointestinal bleeding$",
    "R004$C004$Nausea$",
    "R005$C005$Headache$",
]
SYNTH_OUTC_LINES = [HEADER_OUTC, "R001$C001$DE", "R002$C002$HO", "R003$C003$OT", "R004$C004$RI", "R005$C005$LT"]


@pytest.fixture()
def tmp_faers_dir(tmp_path: Path) -> Path:
    """Write minimal synthetic FAERS text files into tmp_path."""

    quarter = "2026Q1"
    suffix = "26Q1"
    (tmp_path / f"DEMO{suffix}.txt").write_text("\n".join(SYNTH_DEMO_LINES), encoding="utf-8")
    (tmp_path / f"DRUG{suffix}.txt").write_text("\n".join(SYNTH_DRUG_LINES), encoding="utf-8")
    (tmp_path / f"REAC{suffix}.txt").write_text("\n".join(SYNTH_REAC_LINES), encoding="utf-8")
    (tmp_path / f"OUTC{suffix}.txt").write_text("\n".join(SYNTH_OUTC_LINES), encoding="utf-8")
    return tmp_path


@pytest.fixture()
def test_config(tmp_faers_dir: Path) -> PipelineConfig:
    """Minimal config pointing to the synthetic FAERS data directory."""

    return PipelineConfig(
        quarter="2026Q1",
        data_dir=tmp_faers_dir,
        output_dir=tmp_faers_dir / "out",
    )


@pytest.fixture()
def demo_frame() -> pd.DataFrame:
    """Quick DEMO frame from synthetic data (load + process separately)."""
    from io import StringIO
    from data_pipeline.loaders import load_faers_table
    from data_pipeline.config import build_table_specs
    specs = build_table_specs("2026Q1")
    # The fixture writes files into tmp; load from there if you need the full
    # stats. For unit tests the frame is built directly.
    return pd.DataFrame()


@pytest.fixture()
def sample_pairs() -> pd.DataFrame:
    """Hand-crafted pair universe for deterministic unit tests.

    Universe:
    - report R001: ASPIRIN (PS), reactions BLEEDING + GASTROINTESTINAL BLEEDING
    - report R002: WARFARIN (PS), reactions HAEMORRHAGE
    - report R003: ASPIRIN (PS), reactions BLEEDING + GASTROINTESTINAL BLEEDING

    Metric universe counts (observation level):
      ASPIRIN  x BLEEDING                  = 2  (R001, R003)
      ASPIRIN  x GASTROINTESTINAL BLEEDING = 2  (R001, R003)
      WARFARIN x HAEMORRHAGE               = 1  (R002)

    N = 5  total observation rows
    ASPIRIN appears in 4 observations; WARFARIN in 1.
    BLEEDING appears in 2; GASTROINTESTINAL BLEEDING in 2; HAEMORRHAGE in 1.
    """

    return pd.DataFrame(
        {
            "primaryid": ["R001", "R001", "R002", "R003", "R003"],
            "caseid": ["C001", "C001", "C002", "C003", "C003"],
            "drug_name": ["ASPIRIN", "ASPIRIN", "WARFARIN", "ASPIRIN", "ASPIRIN"],
            "event_name": ["BLEEDING", "GASTROINTESTINAL BLEEDING", "HAEMORRHAGE", "BLEEDING", "GASTROINTESTINAL BLEEDING"],
            "raw_drug_name": ["ASPIRIN", "ASPIRIN", "WARFARIN", "ASPIRIN", "ASPIRIN"],
            "raw_reaction": ["Bleeding", "Gastrointestinal bleeding", "Haemorrhage", "Bleeding", "Gastrointestinal bleeding"],
            "source": "FDA_FAERS",
        }
    )