# GridSaathi ⚡

**GridSaathi** is a simulation and optimization engine designed for low-voltage (LV) distribution transformers in Indian peri-urban neighbourhoods (~100 consumers: households, small shops, and critical loads like clinics and cold storage).

The core objective is to mitigate evening ramp outages (6 PM - 10 PM) by orchestrating a small shared battery, solar PV generation, load/solar forecasting, Model Predictive Control (MPC) dispatch, virtual battery flexibility (freezers, water pumps, geysers), and a credit-based fairness engine.

---

## 📁 Repository Structure

```
yuva yodha/
├── config/
│   └── config.yaml          # Single source of truth for all assumptions & parameters
├── data/
│   ├── raw/                 # Raw downloaded weather & environmental data
│   └── processed/           # Processed datasets (load profiles, resampled weather)
├── src/
│   ├── data/                # Data loaders (Open-Meteo, pvlib synthetic, load generator)
│   ├── forecast/            # LightGBM solar & load forecast models
│   ├── optim/               # cvxpy MPC optimization & virtual battery dispatch
│   ├── sim/                 # Step-by-step simulator (Baseline S1 to Full S5)
│   ├── fairness/            # Credit ledger & fairness allocation rules
│   ├── metrics/             # Evaluation metrics (outage hours, Jain's index, costs)
│   └── config.py            # Configuration loader utility
├── api/                     # FastAPI endpoint server for frontend integration
├── outputs/                 # Exported metrics CSVs, JSONs, and visualization plots
├── models/                  # Saved model artifacts (.pkl, .txt)
├── tests/                   # Pytest suite for unit & integration tests
├── docs/                    # Architecture, API contracts, and documentation
├── PROJECT_BRIEF.md         # Original hackathon specifications and rules
└── README.md                # Project README
```

---

## ⚙️ Setup & Installation

1. **Clone Repository & Set Environment:**
   Ensure Python 3.10+ is installed.

2. **Install Dependencies:**
   ```bash
   pip install pandas numpy pvlib lightgbm cvxpy matplotlib plotly pytest pyyaml fastapi uvicorn requests
   ```

3. **Run Skeleton Verification Test:**
   ```bash
   pytest tests/
   ```

---

## 🎯 Phase Workflow

- **Phase 0 (Current)**: Runnable Project Skeleton & Configuration Schema.
- **Phase 1**: Weather Loader, PV Model, and Synthetic Load Generator.
- **Phase 2**: Baseline Grid Simulator (S1) & Metrics Core.
- **Phase 3**: LightGBM Forecasting Engine (Solar, Load & Net Gap).
- **Phase 4**: Shared Battery & cvxpy MPC Optimization Engine.
- **Phase 5**: Tiered Loads & Virtual Battery Integration.
- **Phase 6**: Credit-Based Fairness Engine & Allocation Rules.
- **Phase 7**: End-to-End Simulation Experiments & Sensitivity Analysis.
- **Phase 8**: Static JSON Export & FastAPI Backend Service.
- **Phase 9**: Comprehensive Technical Documentation & Final Reports.
