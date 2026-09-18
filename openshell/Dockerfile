# syntax=docker/dockerfile:1
# Build from the repository root:
#   openshell sandbox create --name rubix-eval --from . --policy ./openshell/policy.yaml --no-auto-providers
#   docker build -f openshell/Dockerfile .

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/sandbox/.venv/bin:/usr/local/bin:/usr/bin:/bin" \
    RUBIX_LANE=verified \
    RUBIX_WEB_ACCESS=0 \
    RUBIX_HARNESS=openshell \
    RUBIX_TRUSTED_RENDERER=0

WORKDIR /opt/rubix-eval

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        bash \
        chromium \
        fonts-liberation \
        libgl1 \
        libglib2.0-0 \
        libnss3 \
        libatk-bridge2.0-0 \
        libgtk-3-0 \
        libasound2 \
        libdrm2 \
        libgbm1 \
        libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE /opt/rubix-eval/
COPY src /opt/rubix-eval/src
COPY web /opt/rubix-eval/web
COPY evals /opt/rubix-eval/evals
COPY docs /opt/rubix-eval/docs
COPY openshell/skills /sandbox/.agents/skills
COPY openshell/run-verified.sh /usr/local/bin/run-verified
COPY openshell/policy.yaml /etc/openshell/policy.yaml

RUN python -m venv /sandbox/.venv \
    && /sandbox/.venv/bin/pip install --no-cache-dir /opt/rubix-eval \
    && mkdir -p /eval /sandbox/.claude/skills /sandbox/.codex \
    && ln -sf /sandbox/.agents/skills/rubiks-eval /sandbox/.claude/skills/rubiks-eval \
    && chmod +x /usr/local/bin/run-verified \
    && printf 'export PATH="/sandbox/.venv/bin:/usr/local/bin:/usr/bin:/bin"\nexport PS1="rubix@openshell:\\w\\$ "\nexport RUBIX_LANE=verified\nexport RUBIX_WEB_ACCESS=0\nexport RUBIX_HARNESS=openshell\n' > /sandbox/.bashrc \
    && useradd --create-home --home-dir /sandbox --shell /bin/bash --uid 1500 sandbox \
    && chown -R 1500:1500 /sandbox /eval /opt/rubix-eval

WORKDIR /eval
USER sandbox
ENTRYPOINT ["/usr/local/bin/run-verified"]
