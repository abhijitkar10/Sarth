# Fusion mechanism study (synthetic)

`fusion_simulation.py` simulates rank-blend ensembles on **synthetic data, not RSNA data**.
Each model score is `d * label + Gaussian noise`, with a chosen noise correlation between
models. All parameters are assumed. It covers ensemble size, cross-family blending,
post-calibration residuals (as in A and B) and gain-view averaging (as in G).

Run: `python3 fusion_simulation.py` (needs numpy; fixed seed). Output: `results.json`,
which the slide deck charts are generated from.
