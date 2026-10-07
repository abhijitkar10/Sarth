# Fusion mechanism study (synthetic)

`fusion_simulation.py` simulates rank-blend ensembles on **synthetic data, not RSNA data**.
Each model score is `d * label + Gaussian noise`, with a chosen noise correlation between
models. All parameters are assumed. Experiments:

1. ensemble size (one family)
2. cross-family blending versus error correlation
3. post-calibration residuals (as in A and B)
4. gain-view averaging (as in G)
5. factorial ablation on a toy replica of the fusion graph (A, B, G on/off), with head-quality
   scenarios and a stress test

Run: `python3 fusion_simulation.py` (needs numpy; fixed seed, deterministic). Output: `results.json`,
which the slide-deck charts and the numbers in `docs/Teaching_Guide.md` are generated from.
