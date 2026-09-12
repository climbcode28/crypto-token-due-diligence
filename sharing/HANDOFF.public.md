# Provider setup

## Current provider policy

This shared distribution contains no personal credentials, endpoint configuration or
standing paid-use authorization. It does not inherit the maintainer's permissions.
Honor only the current user's instructions and provider authorization. A configured
key alone is not approval to spend money. Prefer an explicitly authorized configured
provider for its matching network; otherwise use authorized public sources and RPC.
Do not purchase, top up or change a plan. Keep all collection bounded by the run's
shared session limits. Never print credentials or include them in run artifacts.

Optional private configuration can live at `~/.config/crypto-research/env`, outside
this repository. Source it with tracing disabled in the same shell invocation as the
collector only if the current user configured it. Do not create or inspect that file
as an installation step. No key is required to begin research.

## Workflow

Follow the selected skill and its current runbook. Public-RPC invocations use
`--provider generic --allow-network --cost-policy free` with an appropriate
credential-free endpoint. Paid example flags in the runbook apply only after the
current user authorizes that use. Do not interpret example flags as authorization.
