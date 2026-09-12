# OpenShell sandbox

Run the eval so the agent has **no internet**. NVIDIA OpenShell keeps
`https://inference.local` available for a local or gateway-routed model.

```bash
# Install the OpenShell CLI (once)
curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh

# From the repo root: build this directory as a sandbox image
openshell sandbox create \
  --name rubix-eval \
  --from ./openshell \
  --policy ./openshell/policy.yaml \
  --no-auto-providers
```

Inside the sandbox:

```bash
rubix-eval task --size 3 --depth 8 --seed 1 -o /eval/task.json
rubix-eval show /eval/task.json --no-color
```

Point the agent at `/eval/task.json` and collect `/eval/solution.txt`.
Grade from the host or from the sandbox:

```bash
rubix-eval grade /eval/task.json --solution /eval/solution.txt
```

To use a local GPU model instead of the public internet, configure OpenShell
inference routing to Ollama/vLLM and keep this policy's empty `network_policies`.
See https://docs.nvidia.com/openshell/sandboxes/inference-routing
