# repro-gym (planned)

> Credibility requires numbers, not vibes.

`repro-gym` is the seeded-fault benchmark for repro-agents. It is **not yet
implemented** — this directory documents the plan and is a good source of
good-first-issues.

## Design

1. Collect ~20 small, healthy, permissively-licensed scientific Python repos
   (pyOpenSci-accepted packages, executable-paper repos, tutorial notebooks).
2. Inject known faults programmatically: delete a declared dep; add an undeclared
   import; unpin a version with a known API break; shuffle notebook cells; remove a
   seed; corrupt a stored output.
3. Metrics per pattern: precision/recall on fault detection, repair success rate
   (does the oracle go green?), **false-positive rate on the unmodified repos**
   (target < 5% — the trust killer), wall-clock, $ per audit, and variance across 5
   runs per task.
4. Publish the harness + a results table here.

The unit-test fixtures in
[`tests/fixtures/`](https://github.com/nitishagar/repro-agents/tree/main/tests/fixtures)
(`healthy_pkg`, `faulty_pkg`) are the seed of this corpus.

## Good first issues

- Add a new fault-injection type.
- Add a healthy source repo to the corpus.
- Implement the metrics harness (precision/recall/FPR/cost).
