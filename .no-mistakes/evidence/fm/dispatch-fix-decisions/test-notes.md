# Dispatch test evidence

Target: `a29f4e7769c375ea3f77d0c9e4577d221aaa5370`.
Base: `7da4c3621370534ff9689843d2b77f34158057fb`.

The final targeted baseline has 286 passing checks across nine suites, zero failing checks, and exit code 0 for every suite. The resolver suite accounts for 36 checks. The eight suites in `baseline-results.json` account for 250 checks.

`dispatch-live-evidence.txt` records real resolver invocations, live typesafe.ai responses, the installed Pi CLI, and the installed quota-axi 0.1.55. Quota windows are newly generated disposable data supplied through the tool's documented snapshot input. These records do not prove vendor cache reuse or real expired-token renewal. Logging wrappers call the real tools and preserve their responses.

`response-boundary-evidence.txt` records six offline cases with injected responses. Both provider paths reject ties and unoffered choices. The effective-rule audit check fails against the resolver before commit `59b5165a` and passes against this checkout. These cases are not live model evidence.

Setup corrections during this phase:

- The first resolver-suite invocation inherited TYPESAFE_API_KEY and failed its absent-key assertion. Removing provider credentials from that test process produced 36 passes and exit 0.
- The first live evidence observer counted Pi cache files as resolver temporary files. The corrected observer records files returned by real mktemp calls and verifies their permissions and removal. All live cases were rerun successfully.
- The first offline response driver exported QUOTA, which collided with the resolver's output-file variable. Renaming the fixture variable to QUOTA_FIXTURE produced six passes and exit 0.

Remaining live limits:

- Identical-rule API requests did not produce exact ties. Every live response selected its highest-probability option, so contradictory-choice audit substitutions and unoffered choices remain offline-only.
- Disposable Pi roots have no renewable provider login. Production credentials were not copied, expired, or renewed. Successful expired-token renewal needs a separately authorized disposable provider login.
- Autonomous primary-to-spawn behavior was not re-driven under the supplied test-1 exception. No primary, worker, or fleet lifecycle was started.
- OpenRouter had no supplied runtime key and was exercised only through offline response cases.
- The pi-signed executable was absent from PATH. Its signed-only selection path is covered by the existing behavioral suite, not a live signed executable.

The recorded inconclusive-live exception remains applicable. No new product failure was found. All disposable test roots were removed. No source files changed. Full-suite tests, lint, CI, publishing, and merge operations were not run.
