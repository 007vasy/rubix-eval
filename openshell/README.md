# OpenShell verified computer-use

The agent has **no public internet** and may only drive a **local browser** on
the visual `/eval` page. Inference is `https://inference.local`. There is no
`task.json` path and no click-helper API.

```bash
curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh

openshell sandbox create \
  --name rubix-eval \
  --from . \
  --policy ./openshell/policy.yaml \
  --no-auto-providers
```

`openshell/policy.yaml` allows Chromium to `127.0.0.1:8766` only. It does not
allow `claude` / `codex` / `grok` / `curl` to fetch cube JSON. Do not add
`api.anthropic.com`, `api.openai.com`, or `api.x.ai`.

On the host (or inside the sandbox):

```bash
# terminal 1 — local eval, verified lane, no GCS
RUBIX_VERIFIED_PORT=8766 ./openshell/run-verified.sh serve

# terminal 2 — one agent at a time, native computer-use
./openshell/run-verified.sh fable    # official 3x3 full
./openshell/run-verified.sh astra    # official 3x3 d10
./openshell/run-verified.sh grok     # official 3x3 d2
```

After Done, the record is already `lane=verified`. Attest and upload:

```bash
rubix-eval publish-verified <record_id>
```

Open / web-on records are refused. Do not point the agent at Cloud Run.

If sandboxes die with `Policy fetch failed: failed to connect to OpenShell
server`, Docker packets to `172.18.0.1:17670` are blocked (typical UFW). Fix:

```bash
sudo ./openshell/allow-docker-gateway.sh
```
