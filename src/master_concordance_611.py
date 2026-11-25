"""
master_concordance_611.py — Definitive 1-to-1 inter-database audit between
OKR v2.1.0 (619 khipus) and KFG (650 rows -> 647 unique okr_name).

Exact corpus accounting:
  - OKR v2.1.0 (619) = 611 matched 1-to-1 + 8 OKR-only
  - KFG (650)        = 611 matched 1-to-1 + 3 duplicate okr_name collisions + 36 KFG-only

Produces all frozen summary CSVs in results/ for figures, notebook, and LaTeX paper:
  1. master_matched_611.csv
  2. table1_specimen_concordance_611.csv
  3. table2_subsidiary_drop_611.csv
  4. table3_cord_level_benchmark_611.csv
  5. table4_kfg_replication_h3_h5c_611.csv
  6. kfg_h3a_611.csv, kfg_h3b_611.csv, kfg_h5c_611.csv
"""

import os
import pathlib
import re
import sqlite3
import sys
import warnings

import numpy as np
import openpyxl
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

OKR_DB = pathlib.Path(
    os.environ.get(
        "KHIPU_DB_PATH",
        r"C:\Users\maria\.gemini\antigravity\scratch\Khipu-ML\data\open-khipu-repository-2.1.0\data\khipu.db",
    )
)
KFG_DIR = pathlib.Path(
    r"C:\Users\maria\.gemini\antigravity\scratch\khipu-okr-kfg-concordance\data\kfg\data"
)
KFG_CSV = KFG_DIR / "khipu_summary.csv"
KFG_XLSX_DIR = KFG_DIR / "KFG_DB_Excel"
KFG_SQL = KFG_DIR / "KFG_DB.SQL"
OKR_H3_CSV = pathlib.Path(
    r"C:\Users\maria\.gemini\antigravity\scratch\khipu-intra-grammar\results\deep_dive_fdr_1000.csv"
)
OKR_H5_CSV = pathlib.Path(
    r"C:\Users\maria\.gemini\antigravity\scratch\khipu-intra-grammar\results\extension_h5_sums.csv"
)
RESULTS = pathlib.Path(__file__).resolve().parent.parent / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, r"C:\Users\maria\.gemini\antigravity\scratch\khipu-intra-grammar\src")
from controls_h1_h2_h3 import decode_base10_cords


def norm_key(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip().str.upper()


def clean_meta(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip().str.strip('"').str.strip().str.lower()


def to_float_or_nan(x):
    if x is None:
        return np.nan
    s = str(x).strip()
    if s == "" or s.lower() in {"none", "nan", "u", "unknown", "x"}:
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def norm_twist(x) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "U"
    s = str(x).strip().upper()
    if s.startswith("S"):
        return "S"
    if s.startswith("Z"):
        return "Z"
    return "U"


def norm_attach(x) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "U"
    s = str(x).strip().upper()
    if s.startswith("R"):
        return "R"
    if s.startswith("V"):
        return "V"
    return "U"


def norm_color(x) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    return re.sub(r"\s+", "", str(x).strip().upper())


def non_zero_digits(val: float) -> str:
    if not np.isfinite(val) or val < 0:
        return ""
    return str(int(round(val))).replace("0", "")


def metric_row(label: str, a: np.ndarray, b: np.ndarray) -> dict:
    mask = np.isfinite(a) & np.isfinite(b)
    a, b = a[mask], b[mask]
    diff = np.abs(a - b)
    exact = float(np.mean(diff == 0)) * 100
    within5 = float(np.mean(diff <= np.maximum(1, 0.05 * np.maximum(a, b)))) * 100
    rho = float(stats.spearmanr(a, b).statistic) if len(a) > 2 else np.nan
    return {
        "Field": label,
        "n": int(len(a)),
        "Exact_%": round(exact, 1),
        "Within_5%": round(within5, 1),
        "Med_abs_diff": round(float(np.median(diff)), 2),
        "Max_abs_diff": round(float(np.max(diff)), 1),
        "Spearman_r": round(rho, 4),
    }


def parse_kfg_xlsx(xlsx_path: pathlib.Path):
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    cords_rows = []
    if "Cords" in wb.sheetnames:
        ws = wb["Cords"]
        it = ws.iter_rows(values_only=True)
        header = next(it, None)
        if header is not None:
            col_idx = {str(h).strip(): i for i, h in enumerate(header) if h is not None}
            for r in it:
                if not r or r[0] is None:
                    continue
                cname = str(r[col_idx["Cord_Name"]]).strip()
                if not cname or cname.startswith("!"):
                    continue
                def get_col(name):
                    i = col_idx.get(name, None)
                    return r[i] if i is not None and i < len(r) else None
                cords_rows.append(
                    {
                        "Cord_Name": cname,
                        "Twist": get_col("Twist"),
                        "Attachment": get_col("Attachment"),
                        "Color": get_col("Color"),
                        "Value": get_col("Value"),
                    }
                )
    clusters = []
    if "Clusters" in wb.sheetnames:
        ws = wb["Clusters"]
        for r in ws.iter_rows(values_only=True):
            if not r or r[0] is None:
                continue
            s = str(r[0]).strip()
            if not s or s.startswith("!"):
                continue
            m_range = re.search(r"\((\d+)\s*-\s*(\d+)\)", s)
            m_single = re.search(r"\((\d+)\)", s)
            if m_range:
                a, b = int(m_range.group(1)), int(m_range.group(2))
                clusters.append((a, b, b - a + 1))
            elif m_single:
                a = int(m_single.group(1))
                clusters.append((a, a, 1))
    wb.close()
    return pd.DataFrame(cords_rows), clusters


def h3_color_stat_int(mat_int: np.ndarray) -> float:
    n_g, m = mat_int.shape
    denom = n_g * (n_g - 1) // 2
    if denom == 0:
        return np.nan
    total = 0
    for c in range(m):
        _, counts = np.unique(mat_int[:, c], return_counts=True)
        total += int(np.sum(counts * (counts - 1) // 2))
    return total / (m * denom)


def pre_rank_z(mat: np.ndarray):
    ranks = np.apply_along_axis(stats.rankdata, 1, mat)
    stds = ranks.std(axis=1)
    valid = stds > 0
    if valid.sum() < 2:
        return None
    r_v = ranks[valid]
    return (r_v - r_v.mean(axis=1, keepdims=True)) / stds[valid, None]


def mean_offdiag_corr(z: np.ndarray) -> float:
    m = z.shape[1]
    corr = (z @ z.T) / m
    iu = np.triu_indices(z.shape[0], k=1)
    return float(np.mean(corr[iu]))


def count_h5c_hits(mat: np.ndarray):
    n_g, m = mat.shape
    fl_hits = 0
    any_hits = 0
    for c in range(m):
        col = mat[:, c]
        tot = col.sum()
        if col[0] > 0 and np.count_nonzero(col[1:] > 0) >= 2 and abs(tot - 2 * col[0]) < 1e-6:
            fl_hits += 1
        elif col[-1] > 0 and np.count_nonzero(col[:-1] > 0) >= 2 and abs(tot - 2 * col[-1]) < 1e-6:
            fl_hits += 1
        for r in range(n_g):
            if col[r] > 0 and abs(tot - 2 * col[r]) < 1e-6 and np.count_nonzero(col > 0) >= 3:
                any_hits += 1
                break
    return fl_hits, any_hits


def main():
    # =========================================================================
    # 0. LOAD OKR v2.1.0 & KFG, PERFORM EXACT 1-TO-1 DEDUPLICATED MATCHING
    # =========================================================================
    con = sqlite3.connect(str(OKR_DB))
    vals = decode_base10_cords(con)
    kh = pd.read_sql(
        "SELECT KHIPU_ID, OKR_NUM, INVESTIGATOR_NUM, CREATED_BY, MUSEUM_NAME, MUSEUM_NUM, REGION, PROVENANCE FROM khipu_main",
        con,
    )
    cord = pd.read_sql(
        "SELECT KHIPU_ID, CORD_ID, CORD_LEVEL, CORD_ORDINAL, CLUSTER_ID, TWIST, ATTACHMENT_TYPE FROM cord",
        con,
    )
    cc = pd.read_sql("SELECT KHIPU_ID, CLUSTER_ID, CLUSTER_LEVEL, NUM_CORDS FROM cord_cluster", con)
    knot = pd.read_sql("SELECT CORD_ID, DIRECTION FROM knot", con)
    col = pd.read_sql("SELECT KHIPU_ID, CORD_ID, PCORD_FLAG, COLOR_CD_1, FULL_COLOR FROM ascher_cord_color", con)
    con.close()

    kfg = pd.read_csv(KFG_CSV)
    kh["key_okr"] = norm_key(kh["OKR_NUM"])
    kh["key_inv"] = norm_key(kh["INVESTIGATOR_NUM"])
    kfg["key_okr"] = norm_key(kfg["okr_name"])
    kfg["key_orig"] = norm_key(kfg["original_name"])

    # Deduplicate the 3 KFG duplicate okr_name collisions (prefer khipu_id < 6000000, i.e., authentic OKR-imported record)
    kfg_sorted = kfg.sort_values("khipu_id").copy()
    kfg_dupes = kfg_sorted[kfg_sorted.duplicated("key_okr", keep="first")].copy()
    kfg_dedup = kfg_sorted.drop_duplicates("key_okr", keep="first").copy()

    # Pass 1: OKR_NUM == okr_name
    m_pass1 = kh.merge(kfg_dedup, on="key_okr", how="inner")
    m_pass1["match_type"] = "OKR_NUM==okr_name"

    # Pass 2: Remaining OKR vs remaining KFG by INVESTIGATOR_NUM == original_name (recovers 18 Dallas QU01-QU18)
    rem_okr = kh[~kh["KHIPU_ID"].isin(set(m_pass1["KHIPU_ID"]))].copy()
    rem_kfg = kfg_dedup[~kfg_dedup["khipu_id"].isin(set(m_pass1["khipu_id"]))].copy()
    m_pass2 = rem_okr.merge(rem_kfg, left_on="key_inv", right_on="key_orig", how="inner")
    m_pass2["match_type"] = "INVESTIGATOR_NUM==original_name"

    matched = pd.concat([m_pass1, m_pass2], ignore_index=True)
    okr_only = kh[~kh["KHIPU_ID"].isin(set(matched["KHIPU_ID"]))]
    kfg_only = kfg_dedup[~kfg_dedup["khipu_id"].isin(set(matched["khipu_id"]))]

    print("=== 0. EXACT 1-TO-1 CORPUS ACCOUNTING ===")
    print(f"  OKR v2.1.0 total : {len(kh)} = {len(matched)} matched ({len(m_pass1)} primary + {len(m_pass2)} Dallas/secondary) + {len(okr_only)} OKR-only")
    print(f"  KFG total rows   : {len(kfg)} = {len(matched)} matched + {len(kfg_dupes)} duplicate okr_name collisions + {len(kfg_only)} KFG-only")
    assert len(matched) + len(okr_only) == len(kh)
    assert len(matched) + len(kfg_dupes) + len(kfg_only) == len(kfg)

    # =========================================================================
    # 1. SPECIMEN-LEVEL CONCORDANCE (n = 611, RAW VS HARMONIZED)
    # =========================================================================
    cord = cord.merge(vals[["CORD_ID", "cord_val", "is_clean_decimal"]], on="CORD_ID", how="left")
    cord["cord_val"] = cord["cord_val"].fillna(0.0)
    kn_cnt = knot.groupby("CORD_ID").size().rename("n_knots")
    cord = cord.merge(kn_cnt, on="CORD_ID", how="left")
    cord["n_knots"] = cord["n_knots"].fillna(0).astype(int)

    tw = cord["TWIST"].apply(norm_twist)
    att = cord["ATTACHMENT_TYPE"].apply(norm_attach)
    cord["is_S"] = (tw == "S").astype(int)
    cord["is_Z"] = (tw == "Z").astype(int)
    cord["is_R"] = (att == "R").astype(int)
    cord["is_V"] = (att == "V").astype(int)
    cord["is_pend"] = (cord["CORD_LEVEL"] == 1).astype(int)
    cord["is_sub"] = (cord["CORD_LEVEL"] > 1).astype(int)

    c_agg = cord.groupby("KHIPU_ID").agg(
        okr_num_cords=("CORD_ID", "count"),
        okr_num_pendant=("is_pend", "sum"),
        okr_num_sub=("is_sub", "sum"),
        okr_cl_all=("CLUSTER_ID", "nunique"),
        okr_s_cords=("is_S", "sum"),
        okr_z_cords=("is_Z", "sum"),
        okr_r_cords=("is_R", "sum"),
        okr_v_cords=("is_V", "sum"),
        okr_mean_val=("cord_val", "mean"),
    ).reset_index()

    cl_lvl1 = cc[cc["CLUSTER_LEVEL"] == 1].groupby("KHIPU_ID")["CLUSTER_ID"].nunique().rename("okr_cl_lvl1")
    km = knot.merge(cord[["CORD_ID", "KHIPU_ID"]], on="CORD_ID", how="inner")
    kd = km["DIRECTION"].fillna("").astype(str).str.upper().str.strip()
    km["k_S"] = (kd == "S").astype(int)
    km["k_Z"] = (kd == "Z").astype(int)
    k_agg = km.groupby("KHIPU_ID").agg(
        okr_knot_count=("CORD_ID", "count"),
        okr_s_knots=("k_S", "sum"),
        okr_z_knots=("k_Z", "sum"),
    ).reset_index()

    col_cd1 = col.groupby("KHIPU_ID")["COLOR_CD_1"].nunique().rename("okr_col_cd1")
    col_full_nopc = col[col["PCORD_FLAG"] != 1].groupby("KHIPU_ID")["FULL_COLOR"].nunique().rename("okr_col_full_nopc")

    m = (
        matched.merge(c_agg, on="KHIPU_ID", how="left")
        .merge(cl_lvl1, on="KHIPU_ID", how="left")
        .merge(k_agg, on="KHIPU_ID", how="left")
        .merge(col_cd1, on="KHIPU_ID", how="left")
        .merge(col_full_nopc, on="KHIPU_ID", how="left")
    )
    for cname in [c for c in m.columns if c.startswith("okr_") and c not in {"okr_mean_val", "okr_name"}]:
        m[cname] = m[cname].fillna(0).astype(int)
    m["okr_mean_val"] = m["okr_mean_val"].fillna(0.0)
    m["okr_mean_val_round"] = m["okr_mean_val"].round()
    m.to_csv(RESULTS / "master_matched_611.csv", index=False)

    print("\n=== 1. SPECIMEN-LEVEL CONCORDANCE (n = 611) ===")
    pairs = [
        ("Recto cords", "okr_r_cords", "recto_cords"),
        ("Verso cords", "okr_v_cords", "verso_cords"),
        ("Z-twist cords", "okr_z_cords", "num_z_cords"),
        ("Pendant cords", "okr_num_pendant", "num_pendant_cords"),
        ("S-twist cords", "okr_s_cords", "num_s_cords"),
        ("Total cords", "okr_num_cords", "num_total_cords"),
        ("Subsidiary cords (L>1)", "okr_num_sub", "num_subsidiary_cords"),
        ("Total knots", "okr_knot_count", "knot_count"),
        ("S-dir knots", "okr_s_knots", "num_s_knots"),
        ("Z-dir knots", "okr_z_knots", "num_z_knots"),
        ("Cord clusters (raw: all levels)", "okr_cl_all", "num_cord_clusters"),
        ("Cord clusters (harmonized: LEVEL=1)", "okr_cl_lvl1", "num_cord_clusters"),
        ("Unique colors (raw: COLOR_CD_1)", "okr_col_cd1", "num_ascher_colors"),
        ("Unique colors (harmonized: FULL_COLOR)", "okr_col_full_nopc", "num_ascher_colors"),
        ("Mean cord value (raw float)", "okr_mean_val", "mean_cord_value"),
        ("Mean cord value (rounded int)", "okr_mean_val_round", "mean_cord_value"),
    ]
    t1 = pd.DataFrame([metric_row(lbl, m[c1].values.astype(float), m[c2].values.astype(float)) for lbl, c1, c2 in pairs])
    t1.to_csv(RESULTS / "table1_specimen_concordance_611.csv", index=False)
    print(t1.to_string(index=False))

    # Metadata agreement on n=611
    print("\n  Metadata exact agreement (n = 611):")
    bad = {"", "unknown", "nan", "none", "na"}
    for lbl, c1, c2 in [("REGION", "REGION", "region"), ("PROVENANCE", "PROVENANCE", "provenance"), ("MUSEUM", "MUSEUM_NAME", "museum_name")]:
        s1, s2 = clean_meta(m[c1]), clean_meta(m[c2])
        ok1, ok2 = ~s1.isin(bad), ~s2.isin(bad)
        both = ok1 & ok2
        agree = float((s1[both] == s2[both]).mean() * 100) if both.sum() else np.nan
        print(f"    {lbl:11s}: OKR={ok1.sum():3d}/611 | KFG={ok2.sum():3d}/611 | both={both.sum():3d} | exact={agree:5.1f}%")

    # Quick check on the 18 Dallas khipus specifically
    dal = m[m["match_type"] == "INVESTIGATOR_NUM==original_name"]
    print(f"\n  Dallas recovered subset (n = {len(dal)}):")
    print(
        f"    Total cords exact={(dal['okr_num_cords']==dal['num_total_cords']).sum()}/{len(dal)} | "
        f"Pendants exact={(dal['okr_num_pendant']==dal['num_pendant_cords']).sum()}/{len(dal)} | "
        f"Sub drop (okr_sub>0 & kfg_sub==0)={((dal['okr_num_sub']>0)&(dal['num_subsidiary_cords']==0)).sum()}"
    )

    # =========================================================================
    # 2. SILENT SUBSIDIARY DROP (n = 611) + CHECK 11 EXCEL-MISSING IN SQL
    # =========================================================================
    print("\n=== 2. SILENT SUBSIDIARY DROP (n = 611) ===")
    m["silent_drop"] = (m["okr_num_sub"] > 0) & (m["num_subsidiary_cords"] == 0)
    has_sub = m[m["okr_num_sub"] > 0]
    dropped = m[m["silent_drop"]]
    print(f"  Khipus with OKR sub > 0: {len(has_sub)} | KFG csv sub == 0: {len(dropped)} ({100*len(dropped)/len(has_sub):.1f}%)")
    print(f"  Subsidiary cords dropped in khipu_summary.csv: {int(dropped['okr_num_sub'].sum()):,} / {int(has_sub['okr_num_sub'].sum()):,} ({100*dropped['okr_num_sub'].sum()/has_sub['okr_num_sub'].sum():.1f}%)")

    by_cb = (
        has_sub.groupby(has_sub["CREATED_BY"].fillna("NULL"))
        .agg(
            n_with_okr_sub=("KHIPU_ID", "count"),
            n_kfg_zero_sub=("silent_drop", "sum"),
            okr_sub_cords=("okr_num_sub", "sum"),
            dropped_sub_cords=("okr_num_sub", lambda s: int(s[has_sub.loc[s.index, "silent_drop"]].sum())),
        )
        .sort_values("dropped_sub_cords", ascending=False)
        .reset_index()
    )
    by_cb.to_csv(RESULTS / "table2_subsidiary_drop_611.csv", index=False)
    print(by_cb.to_string(index=False))

    # Check KFG Excel & KFG_DB.SQL for all dropped khipus
    xlsx_map = {p.stem.upper(): p for p in KFG_XLSX_DIR.glob("*.xlsx")}
    with open(KFG_SQL, "r", encoding="utf-8", errors="replace") as f:
        cord_inserts = "\n".join(line for line in f if line.startswith("INSERT INTO `cord`"))

    excel_zero = []
    excel_present = 0
    for _, r in dropped.iterrows():
        lf = str(r["legal_filename"]).strip().upper() if pd.notna(r["legal_filename"]) else ""
        kfgn = str(r["kfg_name"]).strip().upper() if pd.notna(r["kfg_name"]) else ""
        p = xlsx_map.get(lf) or xlsx_map.get(kfgn)
        n_xs = 0
        if p is not None:
            cdf, _ = parse_kfg_xlsx(p)
            if not cdf.empty:
                n_xs = int(cdf["Cord_Name"].str.contains(r"s\d+", case=False, regex=True).sum())
        if n_xs > 0:
            excel_present += 1
        else:
            kid_kfg = int(r["khipu_id"])
            sql_rows = len(re.findall(rf"\(\d+,{kid_kfg},|\({kid_kfg},\d+,", cord_inserts))
            excel_zero.append((r["OKR_NUM"], r["INVESTIGATOR_NUM"], r["CREATED_BY"], int(r["okr_num_pendant"]), int(r["okr_num_sub"]), sql_rows))
    print(f"\n  Origin of dropped subsidiaries ({len(dropped)} khipus):")
    print(f"    Present in KFG_DB_Excel (summary-CSV bug only) : {excel_present} / {len(dropped)}")
    print(f"    Absent in KFG_DB_Excel too                     : {len(excel_zero)} / {len(dropped)}")
    if excel_zero:
        ez_df = pd.DataFrame(excel_zero, columns=["OKR_NUM", "INV_NUM", "CREATED_BY", "okr_pend", "okr_sub", "kfg_sql_cord_rows"])
        print(ez_df.to_string(index=False))

    # =========================================================================
    # 3. CORD-BY-CORD MULTI-FIELD BENCHMARK & KFG H3/H5c REPLICATION (n = 611)
    # =========================================================================
    print("\n=== 3. CORD-BY-CORD BENCHMARK & KFG H3/H5c REPLICATION (n = 611) ===")
    # Pre-aggregate OKR cord primary color (first row per CORD_ID from ascher_cord_color)
    col_cord = col[col["PCORD_FLAG"] != 1].groupby("CORD_ID")["FULL_COLOR"].first().rename("okr_full_color")
    cord_m = cord[cord["KHIPU_ID"].isin(set(m["KHIPU_ID"]))].merge(col_cord, on="CORD_ID", how="left")
    okr_pend_by_kid = {
        kid: grp.sort_values(["CORD_ORDINAL", "CORD_ID"]).reset_index(drop=True)
        for kid, grp in cord_m[cord_m["CORD_LEVEL"] == 1].groupby("KHIPU_ID")
    }

    rng = np.random.default_rng(42)
    N_PERM_H3 = 1000
    N_PERM_H5 = 500

    n_aligned_khipus = 0
    # Cord-level counters
    tot_c = 0
    tw_eq = tw_both_known = tw_known_eq = 0
    att_eq = att_both_known = att_known_eq = 0
    col_both_known = col_known_eq = 0
    val_unknot_tot = val_unknot_eq = 0
    val_clean_tot = val_clean_eq = val_clean_mm_nz = val_clean_mm_p10 = 0
    val_dirty_tot = val_dirty_eq = 0
    khipu_has_zerotier_shift = set()

    h3a_rows, h3b_rows = [], []
    h5c_mats, h5c_meta = [], []

    for _, row in m.iterrows():
        kid = row["KHIPU_ID"]
        lf = str(row["legal_filename"]).strip().upper() if pd.notna(row["legal_filename"]) else ""
        kfgn = str(row["kfg_name"]).strip().upper() if pd.notna(row["kfg_name"]) else ""
        p = xlsx_map.get(lf) or xlsx_map.get(kfgn)
        if p is None:
            continue
        cords_df, clusters = parse_kfg_xlsx(p)
        if cords_df.empty:
            continue

        pend_mask = cords_df["Cord_Name"].str.match(r"^[pP]\d+$")
        kfg_pends = cords_df[pend_mask].copy()
        if kfg_pends.empty:
            continue
        kfg_pends["p_num"] = kfg_pends["Cord_Name"].str[1:].astype(int)
        kfg_pends = kfg_pends.drop_duplicates("p_num").sort_values("p_num").reset_index(drop=True)
        kfg_pends["kfg_val"] = kfg_pends["Value"].apply(to_float_or_nan).fillna(0.0)

        # (A) Cord-by-cord multi-field comparison when pendant count matches
        okr_pends = okr_pend_by_kid.get(kid, pd.DataFrame())
        if len(okr_pends) > 0 and len(okr_pends) == len(kfg_pends):
            n_aligned_khipus += 1
            for i in range(len(okr_pends)):
                tot_c += 1
                # Twist
                t1 = norm_twist(okr_pends.loc[i, "TWIST"])
                t2 = norm_twist(kfg_pends.loc[i, "Twist"])
                if t1 == t2:
                    tw_eq += 1
                if t1 in {"S", "Z"} and t2 in {"S", "Z"}:
                    tw_both_known += 1
                    if t1 == t2:
                        tw_known_eq += 1
                # Attachment
                a1 = norm_attach(okr_pends.loc[i, "ATTACHMENT_TYPE"])
                a2 = norm_attach(kfg_pends.loc[i, "Attachment"])
                if a1 == a2:
                    att_eq += 1
                if a1 in {"R", "V"} and a2 in {"R", "V"}:
                    att_both_known += 1
                    if a1 == a2:
                        att_known_eq += 1
                # Color
                c1 = norm_color(okr_pends.loc[i, "okr_full_color"])
                c2 = norm_color(kfg_pends.loc[i, "Color"])
                if c1 != "" and c2 != "":
                    col_both_known += 1
                    if c1 == c2:
                        col_known_eq += 1
                # Value
                ov = float(okr_pends.loc[i, "cord_val"])
                kv = float(kfg_pends.loc[i, "kfg_val"])
                nk = int(okr_pends.loc[i, "n_knots"])
                cl = okr_pends.loc[i, "is_clean_decimal"]
                if nk == 0:
                    val_unknot_tot += 1
                    if ov == kv:
                        val_unknot_eq += 1
                elif cl == 1:
                    val_clean_tot += 1
                    if ov == kv:
                        val_clean_eq += 1
                    else:
                        if non_zero_digits(ov) == non_zero_digits(kv) and non_zero_digits(ov) != "":
                            val_clean_mm_nz += 1
                            khipu_has_zerotier_shift.add(kid)
                        if ov > 0 and kv > 0 and (kv / ov in {10.0, 100.0, 1000.0, 0.1, 0.01, 0.001}):
                            val_clean_mm_p10 += 1
                else:
                    val_dirty_tot += 1
                    if ov == kv:
                        val_dirty_eq += 1

        # (B) KFG H3 & H5c on Clusters sheet
        valid_cl = [(a, b, sz) for (a, b, sz) in clusters if sz >= 3]
        if len(valid_cl) < 2:
            continue
        vc = pd.Series([sz for _, _, sz in valid_cl]).value_counts()
        modal_m = int(vc.index[0])
        if vc.iloc[0] < 2:
            continue
        groups = [(a, b) for (a, b, sz) in valid_cl if sz == modal_m]
        p_map = kfg_pends.set_index("p_num")

        color_rows, val_rows = [], []
        for a, b in groups:
            idxs = list(range(a, b + 1))
            if all(idx in p_map.index for idx in idxs):
                c_vec = [norm_color(p_map.loc[idx, "Color"]) for idx in idxs]
                v_vec = [float(p_map.loc[idx, "kfg_val"]) for idx in idxs]
                if all(c != "" for c in c_vec):
                    color_rows.append(c_vec)
                val_rows.append(v_vec)

        if len(color_rows) >= 2:
            c_mat = np.array(color_rows, dtype=object)
            uniq = {v: i for i, v in enumerate(set(c_mat.ravel()))}
            if len(uniq) >= 2:
                c_int = np.vectorize(uniq.get)(c_mat)
                obs = h3_color_stat_int(c_int)
                n_g = c_int.shape[0]
                nulls = np.empty(N_PERM_H3)
                for k in range(N_PERM_H3):
                    sh = rng.integers(0, modal_m, size=n_g)
                    nulls[k] = h3_color_stat_int(np.array([np.roll(c_int[i], sh[i]) for i in range(n_g)]))
                h3a_rows.append({
                    "KHIPU_ID": kid, "OKR_NUM": row["OKR_NUM"], "MUSEUM": row["MUSEUM_NAME"],
                    "m": modal_m, "n_groups": n_g, "obs": obs, "null_mean": float(nulls.mean()),
                    "delta": obs - float(nulls.mean()), "p_emp": float((np.sum(nulls >= obs) + 1) / (N_PERM_H3 + 1)),
                })

        if len(val_rows) >= 2:
            v_mat = np.array(val_rows, dtype=float)
            z = pre_rank_z(v_mat)
            if z is not None:
                obs = mean_offdiag_corr(z)
                n_g = z.shape[0]
                nulls = np.empty(N_PERM_H3)
                for k in range(N_PERM_H3):
                    sh = rng.integers(0, modal_m, size=n_g)
                    nulls[k] = mean_offdiag_corr(np.array([np.roll(z[i], sh[i]) for i in range(n_g)]))
                h3b_rows.append({
                    "KHIPU_ID": kid, "OKR_NUM": row["OKR_NUM"], "MUSEUM": row["MUSEUM_NAME"],
                    "m": modal_m, "n_groups": n_g, "obs": obs, "null_mean": float(nulls.mean()),
                    "delta": obs - float(nulls.mean()), "p_emp": float((np.sum(nulls >= obs) + 1) / (N_PERM_H3 + 1)),
                })
            if len(val_rows) >= 3:
                h5c_mats.append(v_mat)
                h5c_meta.append((kid, row["OKR_NUM"], modal_m, len(val_rows)))

    # Print & save Table 3 (Cord-by-cord multi-field benchmark)
    val_all_eq = val_unknot_eq + val_clean_eq + val_dirty_eq
    clean_mm = val_clean_tot - val_clean_eq
    t3 = pd.DataFrame([
        {"Field_Subset": "TWIST (all cords, incl. U)", "n_cords": tot_c, "Exact_%": round(100 * tw_eq / tot_c, 2), "Mismatches": tot_c - tw_eq},
        {"Field_Subset": "TWIST (both S/Z known)", "n_cords": tw_both_known, "Exact_%": round(100 * tw_known_eq / tw_both_known, 2), "Mismatches": tw_both_known - tw_known_eq},
        {"Field_Subset": "ATTACHMENT (all cords, incl. U)", "n_cords": tot_c, "Exact_%": round(100 * att_eq / tot_c, 2), "Mismatches": tot_c - att_eq},
        {"Field_Subset": "ATTACHMENT (both R/V known)", "n_cords": att_both_known, "Exact_%": round(100 * att_known_eq / att_both_known, 2), "Mismatches": att_both_known - att_known_eq},
        {"Field_Subset": "COLOR (FULL_COLOR vs KFG Color, both known)", "n_cords": col_both_known, "Exact_%": round(100 * col_known_eq / col_both_known, 2), "Mismatches": col_both_known - col_known_eq},
        {"Field_Subset": "VALUE (all aligned pendants)", "n_cords": tot_c, "Exact_%": round(100 * val_all_eq / tot_c, 2), "Mismatches": tot_c - val_all_eq},
        {"Field_Subset": "VALUE (unknotted, n_knots==0)", "n_cords": val_unknot_tot, "Exact_%": round(100 * val_unknot_eq / val_unknot_tot, 2), "Mismatches": val_unknot_tot - val_unknot_eq},
        {"Field_Subset": "VALUE (knotted, clean decimal)", "n_cords": val_clean_tot, "Exact_%": round(100 * val_clean_eq / val_clean_tot, 2), "Mismatches": clean_mm},
        {"Field_Subset": "VALUE (knotted, non-clean decimal)", "n_cords": val_dirty_tot, "Exact_%": round(100 * val_dirty_eq / val_dirty_tot, 2), "Mismatches": val_dirty_tot - val_dirty_eq},
    ])
    t3.to_csv(RESULTS / "table3_cord_level_benchmark_611.csv", index=False)
    print(f"  Aligned pendant cords: {tot_c:,} across {n_aligned_khipus} khipus")
    print(t3.to_string(index=False))
    print(f"  Clean-decimal mismatches explained by implicit zero-tier spacing: {val_clean_mm_nz}/{clean_mm} ({100*val_clean_mm_nz/max(1,clean_mm):.1f}%), pure power-of-10: {val_clean_mm_p10}/{clean_mm} ({100*val_clean_mm_p10/max(1,clean_mm):.1f}%)")

    # Save H3 & run H5c
    h3a_df = pd.DataFrame(h3a_rows)
    h3b_df = pd.DataFrame(h3b_rows)
    h3a_df.to_csv(RESULTS / "kfg_h3a_611.csv", index=False)
    h3b_df.to_csv(RESULTS / "kfg_h3b_611.csv", index=False)

    okr_h3 = pd.read_csv(OKR_H3_CSV)
    m_a = h3a_df.merge(okr_h3[["KHIPU_ID", "h3_col_exc"]].dropna(), on="KHIPU_ID", how="inner")
    m_b = h3b_df.merge(okr_h3[["KHIPU_ID", "h3_val_exc"]].dropna(), on="KHIPU_ID", how="inner")

    # H5c
    obs_fl_total = obs_any_total = khipus_with_fl = khipus_p05_fl = 0
    h5_rows = []
    for idx, v_mat in enumerate(h5c_mats):
        kid, okr_num, mm, n_g = h5c_meta[idx]
        fl, an = count_h5c_hits(v_mat)
        obs_fl_total += fl
        obs_any_total += an
        if fl > 0:
            khipus_with_fl += 1
        fl_null = np.empty(N_PERM_H5)
        an_null = np.empty(N_PERM_H5)
        for k in range(N_PERM_H5):
            sh = rng.integers(0, mm, size=n_g)
            f_k, a_k = count_h5c_hits(np.array([np.roll(v_mat[i], sh[i]) for i in range(n_g)]))
            fl_null[k], an_null[k] = f_k, a_k
        p_fl = float((np.sum(fl_null >= fl) + 1) / (N_PERM_H5 + 1)) if fl > 0 else 1.0
        if p_fl < 0.05:
            khipus_p05_fl += 1
        h5_rows.append({
            "KHIPU_ID": kid, "OKR_NUM": okr_num, "m": mm, "n_groups": n_g,
            "obs_fl": fl, "exp_fl": float(fl_null.mean()), "p_fl": p_fl,
            "obs_any": an, "exp_any": float(an_null.mean()),
            "has_zerotier_shift": kid in khipu_has_zerotier_shift,
        })
    h5_df = pd.DataFrame(h5_rows)
    h5_df.to_csv(RESULTS / "kfg_h5c_611.csv", index=False)

    N_AGG = 1000
    agg_fl = np.zeros(N_AGG)
    agg_any = np.zeros(N_AGG)
    for k in range(N_AGG):
        tf = ta = 0
        for v_mat in h5c_mats:
            n_g, mm = v_mat.shape
            sh = rng.integers(0, mm, size=n_g)
            fk, ak = count_h5c_hits(np.array([np.roll(v_mat[i], sh[i]) for i in range(n_g)]))
            tf += fk
            ta += ak
        agg_fl[k], agg_any[k] = tf, ta
    p_agg_fl = float((np.sum(agg_fl >= obs_fl_total) + 1) / (N_AGG + 1))
    p_agg_any = float((np.sum(agg_any >= obs_any_total) + 1) / (N_AGG + 1))

    # Reconcile KFG H5c vs OKR H5c
    okr_h5 = pd.read_csv(OKR_H5_CSV)
    okr_h5_fl_col = [c for c in okr_h5.columns if "h5c" in c.lower() and "fl" in c.lower() and "obs" in c.lower()]
    if okr_h5_fl_col:
        fl_c = okr_h5_fl_col[0]
        h5_cmp = h5_df.merge(okr_h5[["KHIPU_ID", fl_c]], on="KHIPU_ID", how="outer").fillna(0)
        h5_cmp["diff_fl"] = h5_cmp["obs_fl"] - h5_cmp[fl_c]
        gained = h5_cmp[h5_cmp["diff_fl"] > 0].sort_values("diff_fl", ascending=False)
        print(f"\n  H5c first/last reconciliation (KFG obs={obs_fl_total} vs OKR obs={int(okr_h5[fl_c].sum())}):")
        print(f"    Khipus gaining hits in KFG: {len(gained)} (total +{int(gained['diff_fl'].sum())} hits; {int(gained['has_zerotier_shift'].sum())}/{len(gained)} have zero-tier shifts)")
        print(gained[["OKR_NUM", fl_c, "obs_fl", "diff_fl", "has_zerotier_shift"]].head(12).to_string(index=False))

    # Save Table 4 summary
    wa = stats.wilcoxon(h3a_df["delta"])
    wma = stats.wilcoxon(h3a_df.groupby(h3a_df["MUSEUM"].fillna("Unknown"))["delta"].median())
    wb = stats.wilcoxon(h3b_df["delta"])
    wmb = stats.wilcoxon(h3b_df.groupby(h3b_df["MUSEUM"].fillna("Unknown"))["delta"].median())
    t4 = pd.DataFrame([
        {
            "Test": "KFG H3a (Color homology)", "n": len(h3a_df),
            "Effect_or_Obs": f"{h3a_df['delta'].median():+.4f} ({100*(h3a_df['delta']>0).mean():.1f}% pos)",
            "p_specimen": f"{wa.pvalue:.2e}",
            "p_museum": f"{wma.pvalue:.2e} (n_m={h3a_df['MUSEUM'].fillna('Unknown').nunique()})",
            "OKR_KFG_Spearman": f"{stats.spearmanr(m_a['delta'], m_a['h3_col_exc']).statistic:.4f} (n={len(m_a)})",
        },
        {
            "Test": "KFG H3b (Numeric homology)", "n": len(h3b_df),
            "Effect_or_Obs": f"{h3b_df['delta'].median():+.4f} ({100*(h3b_df['delta']>0).mean():.1f}% pos)",
            "p_specimen": f"{wb.pvalue:.2e}",
            "p_museum": f"{wmb.pvalue:.2e} (n_m={h3b_df['MUSEUM'].fillna('Unknown').nunique()})",
            "OKR_KFG_Spearman": f"{stats.spearmanr(m_b['delta'], m_b['h3_val_exc']).statistic:.4f} (n={len(m_b)})",
        },
        {
            "Test": "KFG H5c (first/last sum)", "n": len(h5c_mats),
            "Effect_or_Obs": f"{obs_fl_total} vs {agg_fl.mean():.2f} ({obs_fl_total/agg_fl.mean():.2f}x; {khipus_with_fl} khipus)",
            "p_specimen": f"agg p={p_agg_fl:.4f} ({khipus_p05_fl} p<0.05)",
            "p_museum": "—", "OKR_KFG_Spearman": "—",
        },
        {
            "Test": "KFG H5c (any-row sum)", "n": len(h5c_mats),
            "Effect_or_Obs": f"{obs_any_total} vs {agg_any.mean():.2f} ({obs_any_total/agg_any.mean():.2f}x)",
            "p_specimen": f"agg p={p_agg_any:.4f}",
            "p_museum": "—", "OKR_KFG_Spearman": "—",
        },
    ])
    t4.to_csv(RESULTS / "table4_kfg_replication_h3_h5c_611.csv", index=False)
    print("\n=== 4. FROZEN KFG REPLICATION TABLE (n = 611 CORPUS) ===")
    print(t4.to_string(index=False))
    print("\nAll frozen master tables saved to:", RESULTS)


if __name__ == "__main__":
    main()
