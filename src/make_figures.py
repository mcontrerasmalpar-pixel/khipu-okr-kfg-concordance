"""
make_figures.py — Generate 4 publication-ready figures (300 DPI) for
khipu-okr-kfg-concordance from the frozen n=611 master CSVs.
"""

import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

OKR_H3_CSV = pathlib.Path(
    r"C:\Users\maria\.gemini\antigravity\scratch\khipu-intra-grammar\results\deep_dive_fdr_1000.csv"
)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

NAVY = "#1F4E79"
TEAL = "#2E8B8B"
CORAL = "#C85A32"
GOLD = "#D49B2A"
SLATE = "#7A8B99"
LIGHT = "#DCE6F1"


def fig1_concordance_overview():
    t1 = pd.read_csv(RESULTS / "table1_specimen_concordance_611.csv")

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(12.2, 5.2), gridspec_kw={"width_ratios": [1.0, 1.55]}
    )

    # Panel A: Exact 1-to-1 corpus accounting
    cats = ["OKR v2.1.0\n(619)", "KFG\n(650 rows)"]
    # Stacked horizontal bars
    y = np.arange(len(cats))
    h = 0.45

    # Primary matched (593), Dallas secondary (18), OKR-only (8), KFG dupes (3), KFG-only (36)
    ax1.barh(y, [593, 593], height=h, color=NAVY, label="Matched primary (593)")
    ax1.barh(y, [18, 18], left=[593, 593], height=h, color=TEAL, label="Matched Dallas QU01–18 (18)")
    ax1.barh(y[0], 8, left=611, height=h, color=GOLD, label="OKR-only (8)")
    ax1.barh(y[1], 3, left=611, height=h, color=CORAL, label="KFG duplicate okr_name (3)")
    ax1.barh(y[1], 36, left=614, height=h, color=SLATE, label="KFG-only (36)")

    ax1.text(296, 0, "593", ha="center", va="center", color="white", fontweight="bold", fontsize=10)
    ax1.text(296, 1, "593", ha="center", va="center", color="white", fontweight="bold", fontsize=10)
    ax1.text(624, 0, "+18 +8", ha="left", va="center", color="#222222", fontsize=8.5, fontweight="bold")
    ax1.text(654, 1, "+18 +3 +36", ha="left", va="center", color="#222222", fontsize=8.5, fontweight="bold")

    ax1.set_yticks(y)
    ax1.set_yticklabels(cats, fontweight="bold")
    ax1.set_xlim(0, 770)
    ax1.set_ylim(-0.55, 1.55)
    ax1.set_xlabel("Number of khipu records")
    ax1.set_title("A. Exact 1-to-1 Corpus Accounting (n = 611)")
    ax1.legend(loc="center", frameon=True, fontsize=8.2, ncol=1, facecolor="white", framealpha=0.95)
    ax1.invert_yaxis()

    # Panel B: Specimen-level exact agreement (raw vs schema-harmonized)
    order = [
        "Recto cords",
        "Z-twist cords",
        "Verso cords",
        "Cord clusters (harmonized: LEVEL=1)",
        "Pendant cords",
        "S-twist cords",
        "S-dir knots",
        "Z-dir knots",
        "Total cords",
        "Subsidiary cords (L>1)",
        "Total knots",
        "Unique colors (harmonized: FULL_COLOR)",
        "Cord clusters (raw: all levels)",
        "Unique colors (raw: COLOR_CD_1)",
        "Mean cord value (rounded int)",
        "Mean cord value (raw float)",
    ]
    sub = t1.set_index("Field").loc[order].reset_index()
    colors = []
    for f in sub["Field"]:
        if "harmonized" in f:
            colors.append(TEAL)
        elif "raw" in f or "rounded" in f:
            colors.append(CORAL)
        elif "Subsidiary" in f:
            colors.append(GOLD)
        else:
            colors.append(NAVY)

    yb = np.arange(len(sub))
    bars = ax2.barh(yb, sub["Exact_%"], color=colors, height=0.68)
    for idx, row in sub.iterrows():
        ax2.text(
            row["Exact_%"] + 1.2,
            idx,
            f"{row['Exact_%']:.1f}% (r={row['Spearman_r']:.2f})",
            va="center",
            fontsize=8.0,
            color="#222222",
        )
    ax2.set_yticks(yb)
    ax2.set_yticklabels(sub["Field"], fontsize=8.6)
    ax2.set_xlim(0, 126)
    ax2.set_xlabel("Exact specimen-level agreement (%) across n = 611")
    ax2.set_title("B. Specimen-Level Concordance: Raw vs. Harmonized")
    ax2.invert_yaxis()

    plt.tight_layout()
    out = FIGURES / "fig1_concordance_overview.png"
    fig.savefig(out)
    plt.close(fig)
    print("Saved:", out)


def fig2_subsidiary_drop():
    t2 = pd.read_csv(RESULTS / "table2_subsidiary_drop_611.csv")
    # Merge Chandra / chandra for clean display
    t2["CREATED_BY"] = t2["CREATED_BY"].str.lower()
    t2 = (
        t2.groupby("CREATED_BY", as_index=False)
        .agg(
            n_with_okr_sub=("n_with_okr_sub", "sum"),
            n_kfg_zero_sub=("n_kfg_zero_sub", "sum"),
            okr_sub_cords=("okr_sub_cords", "sum"),
            dropped_sub_cords=("dropped_sub_cords", "sum"),
        )
        .sort_values(["dropped_sub_cords", "okr_sub_cords"], ascending=[False, False])
        .reset_index(drop=True)
    )
    t2["retained"] = t2["okr_sub_cords"] - t2["dropped_sub_cords"]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(11.8, 4.6), gridspec_kw={"width_ratios": [1.55, 1.0]}
    )

    y = np.arange(len(t2))
    ax1.barh(y, t2["dropped_sub_cords"], color=CORAL, height=0.65, label="Dropped in khipu_summary.csv (0 reported)")
    ax1.barh(y, t2["retained"], left=t2["dropped_sub_cords"], color=LIGHT, edgecolor=NAVY, linewidth=0.6, height=0.65, label="Retained in khipu_summary.csv")

    for i, r in t2.iterrows():
        if r["dropped_sub_cords"] > 0:
            lbl = f"{int(r['dropped_sub_cords']):,}/{int(r['okr_sub_cords']):,} ({int(r['n_kfg_zero_sub'])}/{int(r['n_with_okr_sub'])} khipus)"
            col = CORAL
        else:
            lbl = f"0/{int(r['okr_sub_cords']):,} (0/{int(r['n_with_okr_sub'])})"
            col = "#555555"
        ax1.text(r["okr_sub_cords"] + 45, i, lbl, va="center", fontsize=8.3, color=col, fontweight="bold" if r["dropped_sub_cords"] > 10 else "normal")

    ax1.set_yticks(y)
    ax1.set_yticklabels(t2["CREATED_BY"], fontweight="bold")
    ax1.set_xlim(0, 4400)
    ax1.set_xlabel("OKR subsidiary cords (CORD_LEVEL > 1)")
    ax1.set_title("A. Silent Subsidiary Drop in KFG by OKR Cataloger")
    ax1.legend(loc="lower right", fontsize=8.3, frameon=True)
    ax1.invert_yaxis()

    # Panel B: Diagnostic origin of the 63 affected khipus
    orig_labels = [
        "In Excel & SQL\n(summary-CSV\nbug)",
        "Absent in\nExcel & SQL\n(older snapshot)",
        "Absent in Excel,\npartial in\nKFG_DB.SQL",
    ]
    orig_vals = [52, 9, 2]
    orig_cols = [CORAL, GOLD, SLATE]
    x = np.arange(len(orig_labels))
    bars = ax2.bar(x, orig_vals, color=orig_cols, width=0.56, edgecolor="#333333", linewidth=0.6)
    for b, v in zip(bars, orig_vals):
        ax2.text(b.get_x() + b.get_width() / 2, v + 1.3, f"{v} khipus\n({100*v/63:.1f}%)", ha="center", va="bottom", fontsize=8.8, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(orig_labels, fontsize=8.4)
    ax2.set_ylim(0, 64)
    ax2.set_ylabel("Number of affected khipus (total = 63)")
    ax2.set_title("B. Root Cause of the 63 Zero-Subsidiary Khipus")

    plt.tight_layout()
    out = FIGURES / "fig2_subsidiary_drop.png"
    fig.savefig(out)
    plt.close(fig)
    print("Saved:", out)


def fig3_cord_level_benchmark():
    t3 = pd.read_csv(RESULTS / "table3_cord_level_benchmark_611.csv")

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(11.8, 4.5), gridspec_kw={"width_ratios": [1.5, 1.0]}
    )

    keep = [
        ("TWIST (both S/Z known)", "TWIST (S/Z known)", NAVY),
        ("ATTACHMENT (both R/V known)", "ATTACHMENT (R/V known)", NAVY),
        ("VALUE (unknotted, n_knots==0)", "VALUE (unknotted)", TEAL),
        ("VALUE (knotted, clean decimal)", "VALUE (clean decimal)", TEAL),
        ("COLOR (FULL_COLOR vs KFG Color, both known)", "COLOR (FULL_COLOR)", GOLD),
        ("VALUE (knotted, non-clean decimal)", "VALUE (non-clean decimal)", CORAL),
    ]
    t3_idx = t3.set_index("Field_Subset")
    labels = [k[1] for k in keep]
    vals = [float(t3_idx.loc[k[0], "Exact_%"]) for k in keep]
    ns = [int(t3_idx.loc[k[0], "n_cords"]) for k in keep]
    cols = [k[2] for k in keep]

    y = np.arange(len(labels))
    ax1.barh(y, vals, color=cols, height=0.62)
    for i, (v, n) in enumerate(zip(vals, ns)):
        ax1.text(v + 1.5, i, f"{v:.2f}%  (n = {n:,})", va="center", fontsize=8.6, fontweight="bold")
    ax1.set_yticks(y)
    ax1.set_yticklabels(labels, fontweight="bold", fontsize=9.0)
    ax1.set_xlim(0, 128)
    ax1.set_xlabel("Exact cord-by-cord agreement (%)")
    ax1.set_title("A. Cord-Level Benchmark (33,752 Aligned Pendants, 567 Khipus)")
    ax1.invert_yaxis()

    # Panel B: Decomposition of the 1,137 clean-decimal value mismatches
    # Pure power-of-10 (626), Other implicit zero-tier same non-zero digits (993 - 626 = 367), Other differences (144)
    mm_labels = [
        "Pure ×10ⁿ shift\n(e.g., 10 vs 100)",
        "Internal zero-tier\n(e.g., 45 vs 405)",
        "Other / non-zero\ndigit difference",
    ]
    mm_vals = [626, 993 - 626, 1137 - 993]
    mm_cols = [NAVY, TEAL, CORAL]
    x = np.arange(len(mm_labels))
    bars = ax2.bar(x, mm_vals, color=mm_cols, width=0.56, edgecolor="#333333", linewidth=0.6)
    for b, v in zip(bars, mm_vals):
        ax2.text(b.get_x() + b.get_width() / 2, v + 18, f"{v}\n({100*v/1137:.1f}%)", ha="center", va="bottom", fontsize=8.8, fontweight="bold")
    ax2.annotate(
        "87.3% implicit zero-tier\nvertical spacing (993 / 1,137)",
        xy=(0.5, 650),
        xytext=(0.75, 760),
        ha="center",
        fontsize=8.5,
        fontweight="bold",
        color=NAVY,
        bbox=dict(boxstyle="round,pad=0.3", fc="#EEF4FA", ec=NAVY, lw=0.8),
    )
    ax2.set_xticks(x)
    ax2.set_xticklabels(mm_labels, fontsize=8.5)
    ax2.set_ylim(0, 880)
    ax2.set_ylabel("Number of mismatched cords (total = 1,137)")
    ax2.set_title("B. Clean-Decimal Mismatch Mechanism")

    plt.tight_layout()
    out = FIGURES / "fig3_cord_level_benchmark.png"
    fig.savefig(out)
    plt.close(fig)
    print("Saved:", out)


def fig4_kfg_replication_h3_h5c():
    h3a = pd.read_csv(RESULTS / "kfg_h3a_611.csv")
    h3b = pd.read_csv(RESULTS / "kfg_h3b_611.csv")
    okr = pd.read_csv(OKR_H3_CSV)

    ma = h3a.merge(okr[["KHIPU_ID", "h3_col_exc"]].dropna(), on="KHIPU_ID", how="inner")
    mb = h3b.merge(okr[["KHIPU_ID", "h3_val_exc"]].dropna(), on="KHIPU_ID", how="inner")

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(13.2, 4.3))

    # Panel A: H3a scatter
    ax1.axhline(0, color="#999999", lw=0.8, ls="--")
    ax1.axvline(0, color="#999999", lw=0.8, ls="--")
    ax1.scatter(ma["h3_col_exc"], ma["delta"], s=18, alpha=0.65, color=NAVY, edgecolors="none")
    lim_a = [-0.25, 0.85]
    ax1.plot(lim_a, lim_a, color=CORAL, lw=1.2, ls=":", label="y = x")
    ax1.set_xlim(lim_a)
    ax1.set_ylim(lim_a)
    ax1.set_xlabel("OKR H3a Color Δ")
    ax1.set_ylabel("KFG H3a Color Δ")
    ax1.set_title("A. H3a Color Homology (r = 0.983)")
    ax1.text(
        0.04, 0.93,
        f"n = {len(ma)}\nKFG p = 3.8e-32\nMuseum p = 2.6e-09",
        transform=ax1.transAxes, va="top", fontsize=8.3,
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#CCCCCC"),
    )

    # Panel B: H3b scatter
    ax2.axhline(0, color="#999999", lw=0.8, ls="--")
    ax2.axvline(0, color="#999999", lw=0.8, ls="--")
    ax2.scatter(mb["h3_val_exc"], mb["delta"], s=18, alpha=0.65, color=TEAL, edgecolors="none")
    lim_b = [-0.6, 1.05]
    ax2.plot(lim_b, lim_b, color=CORAL, lw=1.2, ls=":", label="y = x")
    ax2.set_xlim(lim_b)
    ax2.set_ylim(lim_b)
    ax2.set_xlabel("OKR H3b Numeric Δ (ordinal)")
    ax2.set_ylabel("KFG H3b Numeric Δ (vertical)")
    ax2.set_title("B. H3b Numeric Homology (r = 0.689)")
    ax2.text(
        0.04, 0.93,
        f"n = {len(mb)}\nKFG p = 3.1e-38\nMuseum p = 1.2e-09",
        transform=ax2.transAxes, va="top", fontsize=8.3,
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#CCCCCC"),
    )

    # Panel C: H5c Cross-Group Exact Sums (OKR vs KFG)
    cats = ["OKR\nfirst/last", "KFG\nfirst/last", "OKR\nany-row", "KFG\nany-row"]
    obs = [32, 45, 43, 57]
    exp = [18.0, 22.85, 33.9, 41.31]
    ratios = ["1.78×\np≤0.001", "1.97×\np=0.001", "1.27×\np=0.056", "1.38×\np=0.009"]

    x = np.arange(len(cats))
    w = 0.36
    ax3.bar(x - w / 2, obs, width=w, color=[NAVY, TEAL, NAVY, TEAL], label="Observed hits")
    ax3.bar(x + w / 2, exp, width=w, color="#C7D3DF", edgecolor="#666666", lw=0.5, label="Null expected")
    for i, (o, rtxt) in enumerate(zip(obs, ratios)):
        col = TEAL if i in {1, 3} else ("#222222" if i == 0 else CORAL)
        ax3.text(x[i], o + 1.8, rtxt, ha="center", va="bottom", fontsize=8.0, fontweight="bold", color=col)
    ax3.set_xticks(x)
    ax3.set_xticklabels(cats, fontsize=8.5, fontweight="bold")
    ax3.set_ylim(0, 70)
    ax3.set_ylabel("Exact cross-group sum hits")
    ax3.set_title("C. H5c Cross-Group Sums: OKR vs KFG")
    ax3.legend(loc="upper left", fontsize=8.0, frameon=True)

    plt.tight_layout()
    out = FIGURES / "fig4_kfg_replication_h3_h5c.png"
    fig.savefig(out)
    plt.close(fig)
    print("Saved:", out)


def main():
    fig1_concordance_overview()
    fig2_subsidiary_drop()
    fig3_cord_level_benchmark()
    fig4_kfg_replication_h3_h5c()
    print("All 4 figures generated successfully.")


if __name__ == "__main__":
    main()
