# syntax=docker/dockerfile:1
# NVIDIA OpenShell sandbox image for the offline Rubik's cube eval.
#   openshell sandbox create --from . --policy ./openshell/policy.yaml

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/sandbox/.venv/bin:/usr/local/bin:/usr/bin:/bin"

WORKDIR /opt/rubix-eval

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        bash \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE /opt/rubix-eval/
COPY src /opt/rubix-eval/src
COPY evals /opt/rubix-eval/evals
COPY openshell/skills /sandbox/.agents/skills
COPY openshell/policy.yaml /etc/openshell/policy.yaml

RUN python -m venv /sandbox/.venv \
    && /sandbox/.venv/bin/pip install --no-cache-dir /opt/rubix-eval \
    && mkdir -p /eval /sandbox/.claude/skills \
    && ln -sf /sandbox/.agents/skills/rubiks-eval /sandbox/.claude/skills/rubiks-eval \
    && printf 'export PATH="/sandbox/.venv/bin:/usr/local/bin:/usr/bin:/bin"\nexport PS1="rubix@openshell:\\w\\$ "\n' > /sandbox/.bashrc \
    && useradd --create-home --home-dir /sandbox --shell /bin/bash --uid 1500 sandbox \
    && chown -R 1500:1500 /sandbox /eval /opt/rubix-eval

WORKDIR /eval
USER sandbox
ENTRYPOINT ["/bin/bash"]
