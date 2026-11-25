# OKR v2.1.0 vs. KFG: Cross-Repository Concordance & Schema Audit

Reproducible inter-database concordance audit comparing the **Open Khipu Repository (OKR v2.1.0, 619 khipus; DOI: `10.5281/zenodo.18025748`)** and the **Khipu Field Guide (KFG, 650 rows; `khipufieldguide/data-science-khipu-article`)**.

## Key Findings (`n = 611` exact 1-to-1 physical matches)

1. **Exact 1-to-1 Corpus Accounting:**
   - **OKR v2.1.0 (`619`)** = `611` matched (`593` by `OKR_NUM == okr_name` + `18` Dallas Museum of Art `QU01–QU18` matched by `INVESTIGATOR_NUM == original_name`) + `8` OKR-only.
   - **KFG (`650`)** = `611` matched + `3` duplicate `okr_name` collisions (`KH0227`, `KH0267`, `KH0350` under `khipu_id` `6000025–6000027`) + `36` KFG-only.
2. **Cord-Level Identity (`33,752` aligned pendant cords across `567` khipus):**
   - `TWIST` (both S/Z known, `n = 27,994`): **100.00%** exact agreement (`0` mismatches).
   - `ATTACHMENT` (both R/V known, `n = 23,027`): **100.00%** exact agreement (`0` mismatches).
   - `VALUE` (unknotted, `n = 10,705`): **98.91%**; clean decimal (`n = 17,933`): **93.66%** (`87.3%` of mismatches are implicit zero-tier vertical spacing shifts such as `45` vs `405`); non-clean decimal (`n = 5,114`): **3.77%**.
3. **Silent Subsidiary Drop in KFG `khipu_summary.csv`:**
   - `63 / 399` subsidiary-bearing khipus (`15.8%`) report `0` subsidiaries in `khipu_summary.csv`, silently dropping **`2,313 / 15,115` subsidiary cords (`15.3%`)**.
   - `62 / 63` affected khipus (`99.8%` of dropped cords) come from just two recent OKR catalogers: `julia` (`44/51`, `1,716` cords) and `jclindaniel` (`18/20`, `593` cords). In `52 / 63` cases, the subsidiaries remain intact inside `KFG_DB_Excel/*.xlsx` and `KFG_DB.SQL`, isolating a `khipu_summary.csv` aggregation bug.
4. **Schema Harmonization:**
   - Restricting OKR clusters to `cord_cluster.CLUSTER_LEVEL = 1` lifts exact cluster agreement from `31.3%` to **`94.9%`** (remaining `~5%` driven by KFG singleton imputation on unsegmented OKR khipus).
   - Switching from `COLOR_CD_1` to `FULL_COLOR` (`PCORD_FLAG != 1`) lifts exact unique-color agreement from `25.7%` to **`71.0%`** (`79.5%` cord-by-cord).
5. **Independent Cross-Repository Replication of Within-Khipu Grammar (`N_perm = 1,000`):**
   - **KFG H3a (Color tabular homology):** `n = 312`, median $\Delta = +0.0862$ (`70.8%` positive), $p = 3.84 \times 10^{-32}$ (museum-collapsed $p = 2.57 \times 10^{-9}$; OKR–KFG Spearman $r = 0.9830$).
   - **KFG H3b (Numeric tabular homology, KFG vertical values):** `n = 330`, median $\Delta = +0.4027$ (`83.3%` positive), $p = 3.05 \times 10^{-38}$ (museum-collapsed $p = 1.19 \times 10^{-9}$; OKR–KFG Spearman $r = 0.6887$).
   - **KFG H5c (Cross-group exact slot sums):** `first/last` $45$ vs. $22.85$ expected ($1.97\times$, aggregate $p = 0.0010$); `any-row` $57$ vs. $41.31$ ($1.38\times$, aggregate $p = 0.0090$).

## Repository Structure

```text
src/
  master_concordance_611.py   # End-to-end 1-to-1 audit (n=611) & KFG H3/H5c replication
  make_figures.py             # Generates all 4 publication figures (300 DPI)
notebooks/
  01_okr_kfg_concordance.ipynb # Executed summary & verification notebook
results/
  table1_specimen_concordance_611.csv
  table2_subsidiary_drop_611.csv
  table3_cord_level_benchmark_611.csv
  table4_kfg_replication_h3_h5c_611.csv
  master_matched_611.csv
  kfg_h3a_611.csv, kfg_h3b_611.csv, kfg_h5c_611.csv
figures/
  fig1_concordance_overview.png
  fig2_subsidiary_drop.png
  fig3_cord_level_benchmark.png
  fig4_kfg_replication_h3_h5c.png
```

## Reproduction

1. Download OKR v2.1.0 (`khipu.db`, DOI `10.5281/zenodo.18025748`) and clone KFG (`https://github.com/khipufieldguide/data-science-khipu-article.git`) into `data/kfg/`.
2. Install dependencies: `pip install -r requirements.txt`
3. Run the master audit and figure generator:
   ```bash
   python src/master_concordance_611.py
   python src/make_figures.py
   ```
