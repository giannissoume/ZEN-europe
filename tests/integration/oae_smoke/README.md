# Liming OAE functionality check

Run with the generation environment's Python:

```sh
python tests/integration/oae_smoke/build_and_run.py
```

The script uses the real OAE carriers, technologies, source data and coastal limits, and solves through the ordinary `zen-garden` command. Electricity, gas, hydrogen, diesel and freight supply are synthetic, priced boundaries. Fixture storage uses the real carbon-storage credit with simplified economics. Synthetic-gas testing uses the baseline methanation conversion factors. It is an accounting check, not a complete gas-sector scenario.

Checks cover forced activity, zero activity, disabled application, fossil gas, a zero-carbon gas boundary, baseline synthetic-gas conversion factors, unavailable storage, landlocked deployment and exceeding the marine allowance. Zero-carbon gas supply is a fixture proxy, not a complete biomethane value chain. Results and logs are under ignored `outputs/`. No installed solver files or plugins are changed.

Standard full-sector generation was subsequently verified for all 28 model countries and one year (2026), using the matching existing ENTSO-E cache. No API key was needed. The earlier two-country check requested a different geography-specific transmission cache, which was absent; it did not establish that all ENTSO-E caches were missing. A one-country attempt also encountered the baseline empty-edge-table error. Baseline files were left unchanged. No full-European optimization has been run for OAE.

OAE capture follows baseline CCS: 90% of calcination plus fuel CO2, using the existing IPCC natural-gas factor. The fixture checks reproduce this convention across supply routes; they do not independently validate the baseline synthetic-gas carbon coefficient.

Independent review reproduced 93 unit tests, all eight ordinary CLI smoke cases and full-sector 28-country generation for 2026 with ZEN-creator 2.1.0 and ZEN-garden 3.4.0. Full generation needed a live baseline Swiss energy-balance fetch; the ENTSO-E cache was reused without alteration. The checker now verifies zero capacity limits and zero existing/invested capacity before interpreting masked OAE flows as zero, requires the expected application technology to be present/absent, and checks annual hours and production/application operating costs. The disabled-application fixture retains the actual no-export hydrate boundary.
