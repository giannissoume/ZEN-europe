# BCR smoke checks

Run from the repository root:

```sh
../.conda/zen-europe/bin/python tests/integration/bcr_smoke/build_and_run.py
```

Requires the generation environment, the sibling `zen-solve` environment, cached
source data, and Gurobi. Outputs are written beneath `outputs/`.

Uses production pyrolysis, biochar carrier, fuel allocation and soil application.
Synthetic boundaries import biomass, electricity, diesel and freight, demand
1 MW of coal-equivalent fuel, and accept oil/heat coproducts without revenue.
Existing capacity and diffusion are explicitly disabled in this single-year,
one-node accounting fixture; it does not validate deployment dynamics.

Checks mixed fuel/application allocation, zero application with fuel production,
disabled application retaining fuel, and infeasibility above the production land
ceiling. Saved results must contain the expected technologies/carriers and finite
selected flows. The checker verifies conservation, coproducts, diesel, freight,
no biochar import/export bypass, capital and annual operating charges, procurement
cost, gross removal and the complete net emissions balance. Independent financial
expectations use the DEA scenario mean and the cached ECB 2012–2025 inflation
factor (1.3175551998230455). A deliberate source-cache update requires rechecking it.

The fixture also forces BCR and ERW simultaneously to their independent land
ceilings, using unchanged ERW production classes. The existing ERW co-application
fixture predates the new carrier; this BCR-owned case covers the updated interface.

Run `demonstrate_diffusion.py` for four zero-seed infeasibility checks and a
positive control with legitimate existing pyrolysis. See
[diffusion-review.md](diffusion-review.md) for the updated pathway diagram,
bookkeeping rationale, results and validation limits.
