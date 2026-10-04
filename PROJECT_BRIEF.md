# GridSaathi - Project Brief

## Goal
Build a simulation of one low-voltage distribution transformer (about 100 consumers: households, small shops, a few critical users like a clinic and cold storage) in an Indian peri-urban neighbourhood. Show that a small shared battery + forecasting + MPC dispatch + "virtual battery" (freezers, water pumps, geysers used as flexible storage) + a fairness engine reduces evening outage hours compared to a baseline.

## Pain Window
Evening ramp, 6 PM to 10 PM, when solar drops and demand peaks.

## Stack
Python, pandas, numpy, pvlib, LightGBM, cvxpy, matplotlib or plotly, pytest, FastAPI (later).

## Hard Rules
1. Every assumption lives in `config/config.yaml`. Nothing hardcoded in code.
2. Data loaders are swappable: `SyntheticLoader` now, `CSVLoader` later, same interface.
3. Label all synthetic data clearly in code and in outputs.
4. Fixed random seed from config.
5. Small readable functions, docstrings, a few unit tests per module.
6. Work ONE phase at a time. When a phase is done, stop, print: what you built, how to run it, what I should check. Wait for me to say "next".
7. Only edit files that belong to the current phase. Do not rewrite unrelated files.
8. Never invent results. Every number in a summary must come from a saved output file.
9. Do not touch `/frontend`. Another agent may own it later.

## Folder Structure
```
/config/config.yaml
/data/raw, /data/processed
/src/data, /src/forecast, /src/optim, /src/sim, /src/fairness, /src/metrics
/api
/outputs, /models
/tests
/docs
README.md, PROJECT_BRIEF.md
```

## Phases Summary
- **Phase 0**: Skeleton (Folders, runnable empty skeleton, README, PROJECT_BRIEF.md, config.yaml).
- **Phase 1**: Data layer (Weather loader, PV model, synthetic load generator, DataLoaders, plots).
- **Phase 2**: Baseline simulator (S1 scenario, metrics, unit tests, baseline_metrics.csv).
- **Phase 3**: Forecasting (LightGBM solar & load forecast, baselines, quantile models, gap forecast).
- **Phase 4**: Battery & MPC (cvxpy MPC dispatch, scenarios S2 & S3, energy balance test).
- **Phase 5**: Tiers & Virtual Battery (Tiering, virtual battery models, response rates, scenario S4, min battery experiment).
- **Phase 6**: Fairness (Credit ledger, scenario S5, Jain's index, fairness trade-off curve).
- **Phase 7**: Experiments (Run S1-S5, stress tests, sensitivity analysis, final results & charts).
- **Phase 8**: Export for Frontend (Static JSON export, FastAPI endpoint server).
- **Phase 9**: Documentation (README, ASSUMPTIONS.md, RESULTS.md, technical write-up).
