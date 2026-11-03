---
name: nas100-day-trader-timesfm
description: TimesFM forecasting overlay skill for NAS100 day trading, providing directional gating and causal forecast integration.
---

# TimesFM Overlay for NAS100 Day Trader Skill Specification

## Overview
This skill integrates Google TimesFM forecasting capabilities as a directional overlay gating mechanism for the NAS100 day-trader baseline.

## Licensing & Upstream Notice
- **TimesFM 3 Notice**: TimesFM 3 weights are distributed under non-commercial, non-production terms (verify upstream notice in `nas100-trading/LICENSE-timesfm`).
- **Implementation Status**: No actual model calls or weights execution are implemented in this repository. All forecasting inputs must be supplied via local CSV artifacts (`--forecasts FILE.csv`) with strict chronological causal provenance.

## Overlay Integration Rules
1. **Directional Gating**: TimesFM forecasts overlay gate baseline trading direction.
2. **Comparison**: Evaluated against baseline with no performance improvement claims.
3. **Causal Provenance**: Forecast CSV (`datetime,predicted_close`) must be generated without future data leakage. No network downloads or external model calls are performed.
