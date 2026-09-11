# Batchivo single-owner releases

## Handover sequence

PR #202 introduces real Woodpecker PR validation and includes the native commerce
source already deployed in production. Keep the Argo commit pin until the PR has
passed its required checks, merged normally, and its Kubernetes tree has been
verified against the running release. The PR and the shop operations handover
report record the current migration status. Do not bypass validation.

## Validation and publishing

`test-fast` runs backend lint/format, unit tests with ephemeral PostgreSQL,
frontend lint/tests/TypeScript build, and backend/frontend dependency scans.
`test-integration` runs the remaining backend tests against its own ephemeral
PostgreSQL databases. Both run on PRs targeting main, pushes to main, and explicit
`build-release` deployment events. Neither receives publishing credentials or
production database credentials.

GitHub reports the actual PR contexts as `ci/woodpecker/pr/test-fast` and
`ci/woodpecker/pr/test-integration`. Require both with an up-to-date branch before
merging. Single-owner policy removes the impossible second-person/code-owner
approval requirement; it does not waive tests or security checks.

The Woodpecker repository setting **Allow deployments** must be enabled for this
workflow. It was enabled on 11 September 2026 after confirming that `techize` was
the sole collaborator with push access. Other approval and trust settings were
preserved. Reassess this setting when granting another user repository write
access: deployment events may receive release-only secrets. See the
[Woodpecker project settings documentation](https://woodpecker-ci.org/docs/usage/project-settings).

Publishing is a separate owner-triggered action on a successful main pipeline:

```sh
woodpecker-cli pipeline deploy techize/batchivo MAIN_PIPELINE_NUMBER build-release
```

The event reruns validation first. `build` depends on both validation workflows,
publishes commit-tagged backend/frontend images, then scans those images. A failed
scan means the images are not eligible for promotion. Publishing does not edit
staging or production manifests. PR validation never publishes images.

## Promotion

1. Record the successful release run, exact main commit and image digests.
2. Rehearse migrations and verify the release against isolated commerce data.
3. Create a separate manifest PR pinning the approved digests (including migration
   init containers), with a rollback reference and migration compatibility notes.
4. Run required PR checks and inspect the rendered manifest diff. Preserve commerce
   role credentials, order ownership and legacy payment callback configuration.
5. Merge the exact validated PR. Allow Argo to synchronize only after checking its
   target revision and ensuring the intended manifest is the only release change.
6. Verify readiness, order/stock processing, callbacks and monitoring. Do not make
   real payment charges as a deployment smoke test.

Rollback uses the previously recorded manifest/image revision. Database changes
must remain backwards compatible; do not restore a stale database over live orders.
The existing shop cutover runbook retains the customer/payment reconciliation steps.

## Lint compatibility

Ruff 0.16 expanded its default rule set. The project explicitly selects its
established `E4`, `E7`, `E9`, `F` rules to prevent dependency upgrades silently
changing lint policy. Existing SQLAlchemy relationship/conditional-import ignores
are retained. Source was formatted and genuine selected-rule failures fixed.
See https://astral.sh/blog/ruff-v0.16.0.

## CI host log capture

The k3s nodes need sufficient inotify capacity for Kubernetes log streams. The
shop operations repository owns `commerce/scripts/configure-ci-log-limits.py`
and its node preimage report. It persists a minimum of 1,024 instances and
524,288 watches in `/etc/sysctl.d/90-woodpecker-inotify.conf`, without reducing
higher existing limits. It does not restart services. Scratch CI databases use
`fsync=off` and `synchronous_commit=off`; production database settings are untouched.

## Validation scope

The legacy integration suite includes pre-existing skipped cases (rate-limiter
isolation, SQLite-era return fixtures and unfinished historical endpoints). A
green CI run does not mean those skipped scenarios were exercised. Preserve their
counts in release evidence and use the commerce sandbox/browser acceptance suite
for changes to payments, orders, fulfilment or stock. Dependency lock updates here
do not patch the already-running image; a new image needs its own isolated release
acceptance before promotion.
