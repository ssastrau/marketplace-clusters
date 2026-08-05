# Reference Apps — Archetype Taxonomy

The pipeline skills reconcile a new/backported app's architecture against the apps already in the
marketplace. Rather than a hand-picked shortlist, this file buckets **every** app into a structural
archetype. A skill picks the bucket the target app most resembles, then weights the **most recently
added** members of that bucket highest (newer apps track current conventions).

**This is the single place to maintain the taxonomy** — update it by PR when apps are added or
recategorized. Membership (which bucket an app is in) is curated here; **recency is computed at
runtime, not stored here** (so it never goes stale).

## How the skills use this file

1. **Classify** the target app from its `architecture_decisions.md` — install method (docker-compose
   / binary+systemd / apt / source / language-pkg), web exposure (nginx reverse proxy? non-standard
   port?), auth model, and special traits (GPU? database? PHP? VPN?). Match it to **one** bucket
   below (an app may fit two — pick the dominant structure).
2. **Rank that bucket's members by date-added** (newest first) with:
   ```bash
   git log --diff-filter=A --format=%cs -- apps/linode-marketplace-<app> | tail -1
   ```
   run per member. (Use *date-added*, NOT last-commit — last-commit is polluted by repo-wide bulk
   commits where ~40 apps share one date.)
3. **Read the newest 2–3 members' actual files** (`site.yml`, `provision.yml`, `roles/<app>/`,
   the StackScript) as the primary template; older members are fallback. **Cite `file:line`** for
   any pattern borrowed — never reason from memory.

`/app-deploy` uses the matched bucket more lightly — to pull category-specific StackScript/UDF
specifics (e.g. GPU driver setup for bucket 1, multi-service compose port surfaces for bucket 3).

## Buckets

### 1. GPU / LLM model-serving
vLLM/inference engine + Open-WebUI, `gpu_utils` helper, NVIDIA drivers, docker-compose, model
download readiness, GPU firewall posture.
`ollama` · `deepseek` · `qwen` · `gpt-oss` · `gemma3` · `open-webui`

### 2. Vector / AI database
Vector store; data-endpoint auth (API key / TLS / nginx basic-auth); often single container or
multi-service compose.
`pgvector` · `milvus` · `chroma` · `weaviate`

### 3. Multi-service docker-compose web app
`community.docker.docker_compose_v2`, multiple services (app + DB + cache/daemon), nginx reverse
proxy, native login, often a systemd wrapper around the compose project.
`azuracast` · `guacamole` · `harbor` · `joplin` · `rocketchat` · `odoo` · `nextcloud` · `peppermint` · `simplex-chat` · `mastodon` · `appwrite` · `liveswitch`

### 4. Single-container docker app behind nginx
One `docker_container`, nginx reverse proxy + certbot, native login.
`focalboard` · `uptimekuma` · `jupyterlab`

### 5. Binary/package + systemd + nginx (service)
Binary/tarball/deb (or apt) → systemd unit(s) → nginx reverse proxy + certbot; config templated
(HCL/conf); often loopback-bound API + outer auth. The HashiCorp-style reference shape.
`hashicorp-nomad` · `hashicorp-vault` · `openbao` · `cribl` · `nats-single-node` · `antmedia` · `antmedia-community` · `owncast` · `akamai-mcp-client`
> Secrets/Vault family (`hashicorp-vault`, `openbao`): HCL config + TLS/self-signed CA + unseal/token
> handling. MCP client (`akamai-mcp-client`): `get_url` binary + systemd agent.

### 6. Package-repo service + native/admin UI
`apt`/vendor repo install; the app serves its own web/admin UI (proxied by nginx where needed);
native login. Includes admin-console apps that need a two-layer auth outer wrap.
`gitea` · `gitlab` · `jenkins` · `rabbitmq` · `jitsi` · `code-server` · `plex` · `haltdos`
> `haltdos` is the **two-layer-auth admin console** exemplar (public URL *is* the admin surface).

### 7. PHP CMS / LAMP-LEMP stack
PHP + Apache/nginx + PHP-FPM + MySQL/MariaDB; **installer-wizard elimination** (CLAUDE.md §7a);
CLI installer or pre-baked config; installer endpoint deleted/denied + smoke-tested.
`wordpress` · `woocommerce` · `drupal` · `moodle` · `grav` · `passbolt` · `joomla` · `lamp` · `lemp` · `openlitespeed-wordpress` · `openlitespeed-django`
> `joomla` is the recent CLI-installer + installer-dir-deletion exemplar.

### 8. Language-framework app & dev stacks
Python/Node/Ruby app via language package manager (pip/venv+gunicorn, npm/PM2, bundler/puma),
nginx reverse proxy, often a postgres backend; plus the base dev stacks.
`openclaw` · `backstage` · `django` · `flask` · `ruby-rails` · `apache-airflow` · `mean` · `mern` · `nodejs` · `saltcorn`

### 9. Database / data-store (headless or admin UI)
Datastore as the product; `database` helper role or native install; data-endpoint auth. Some expose
a management UI (graph DBs), most are headless.
`postgresql` · `mysql` · `redis` · `valkey` · `neo4j` · `memgraph` · `arangodb`

### 10. VPN / network / tunneling
apt/binary install, cert/key-based auth, systemd service, usually no web UI (or a thin admin UI).
`wireguard-server` · `wireguard-client` · `openvpn` · `shadowsocks` · `pritunl` · `netfoundry-edge-router`

### 11. Observability / monitoring
Metrics / logs / traces / SIEM; systemd or compose; nginx proxy; `data_exporter` where relevant.
`prometheus-grafana` · `influxdb` · `zabbix` · `wazuh` · `splunk` · `pihole` · `jaeger`

### 12. Hosting control panel (vendor installer)
Vendor binary/script installer that self-manages its stack and web UI; deviates from the standard
Ansible-module pattern by design.
`plesk` · `cpanel-almalinux` · `cpanel-ubuntu` · `cyberpanel` · `aapanel` · `cloudron`

### 13. Security / pentest / specialized tooling
Tool collections or specialized servers that don't follow the standard web-app shape.
`kali-linux` · `beef` · `benchkit` · `linuxgsm`

## Not reference archetypes (infrastructure baselines)
These install a base only (no app role) and shouldn't be used as a template for a new app:
`docker` (Docker engine only) · `secure-your-server` (hardening: `common` + `post` only).

## Maintenance
- When a new app merges, add it to its bucket here (one line). Recency handles "is it current" — you
  only maintain *membership*.
- If a bucket grows past ~12 and splits naturally (e.g. headless DB vs DB-with-UI), split it and note
  the rationale in the PR.
- Verify a member is implemented (not an empty scaffold) before citing it — read its
  `roles/<app>/tasks/`.
