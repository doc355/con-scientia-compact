# PI (Project Iris) build — branch `pi/build`
Built and tested by Devin (Ola, session 2e7fb4ab). Never on master. Nothing here goes live on PI without Christopher's word **SHIP**;
installs go through the MBP bridge into `~/HIFIDecant/Selflight/intake/devin/<date>_<slug>/` with SEND.md.

| component | path | status |
|---|---|---|
| PI Core Gateway (OpenAI-compatible router to ollama/exo/moonshot/openrouter/anthropic, append-only job API, health) | `gateway/pi_gateway.py` | built, 9 tests pass, default port 8784 |
| Background-safety gate 1: snapshot + diff | `safety/pi_baseline.py` | built, live-run against tailnet |
| Background-safety gate 3: chaos restart per launchd label | `safety/pi_chaos.sh` | built, runs on PI host only |
| Plaud watchdog (CLI poll, seen-IDs, retry/backoff, gateway or file signal) | `plaud/plaud_watchdog.py` | built, 2 tests pass with a fake CLI; real CLI command names unverified |
| Devin as callable agent (start/status/message, ACU cap, append-only ledger, key never logged) | `devin/pi_devin.py` | built, 3 tests pass against a fake API; live API unverified (needs DEVIN_API_KEY) |

Run all tests: `for d in gateway plaud devin; do (cd $d && python3 -m unittest discover -s tests -q); done`
Gate 2 (regression) = these tests + the eval harness's 88 tests on `council/harness`.
Stdlib Python 3 only: no installs on PI.
