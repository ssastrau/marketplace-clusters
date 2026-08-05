<!--
Template: MODEL-SERVING / AI marketplace app README (GPU inference / vector DB).
Fill every <placeholder> from the validated artifacts. Delete this comment block.
This README is a STARTING POINT — the operator must review it before the PR is final.
References for tone/structure: linode-marketplace-deepseek, -qwen, -milvus, -chroma (READMEs).
-->

# <Model / Engine Name> Marketplace App

Serve [<Model / Engine>](<upstream-url>) on Akamai Cloud Compute GPU instances — <one-line
description: what the model/engine is, what it's good for>.

## What gets deployed

- <Engine, e.g. vLLM> serving <model> in a GPU container (<image>).
- nginx reverse proxy with a Let's Encrypt certificate (HTTP→HTTPS redirect).
- API authentication: <API key / bearer token> — the inference endpoint is **not** open.
- `nvidia-persistenced` + NVIDIA drivers / container toolkit.
- A limited sudo user; UFW (22, 80, 443<, API port>); fail2ban.
- Generated credentials + API key written to `/home/<user>/.credentials`.

## Requirements

- GPU plan: <plan, e.g. g1-gpu-rtx6000-4 or g2-gpu-...>. <VRAM / compute-capability notes>.
- <model-size → GPU-count guidance; quantization/precision notes (e.g. FP16 vs BF16 support)>.

<!-- REVIEW: confirm GPU plan + precision against the tested deploy and any GPU memory notes. -->

## Deployment options (UDFs)

| Field | Description | Default |
|---|---|---|
| Limited sudo user | The non-root user created on the instance | — |
| Domain / Subdomain | FQDN for the TLS certificate | — |
| <model selection / context length / etc.> | <description> | <default> |

## Getting started after deploy

1. SSH in (or use LISH) and read `/home/<user>/.credentials` for the API key.
2. Send an authenticated request:
   ```bash
   curl https://<subdomain>.<domain>/v1/chat/completions \
     -H "Authorization: Bearer <API_KEY>" \
     -H "Content-Type: application/json" \
     -d '{"model": "<model>", "messages": [{"role": "user", "content": "Hello"}]}'
   ```
<!-- REVIEW: replace endpoint/payload with the real tested request from e2e_testing.md. -->

## Performance & scaling

- <tensor-parallel / GPU-count guidance; gpu-memory-utilization notes>.
- <warmup / model-download time; health-check expectations>.

## Software included

| Software | Version | License |
|---|---|---|
| <Engine> | <version> | <license> |
| <Model> | <version> | <license> |
| nginx | <version> | BSD-2-Clause |

## Documentation

- Upstream: <docs-url>
- Model card: <model-card-url>
