<!--
Template: STANDARD marketplace app README (service / CMS / HashiCorp-style).
Mirrors the house format (see apps/linode-marketplace-joomla/README.md): same sections, same order —
Title -> intro -> Software Included (+ Supported Distributions) -> Linode Helpers Included ->
Post-Deployment -> Use our API (SHELL then CLI) -> Resources.
Fill every <placeholder> from the validated artifacts (architecture_decisions.md, manual_install.md,
the playbook, e2e_testing.md). Pull the UDF list from the StackScript. Delete this comment block.
This README is a STARTING POINT — the operator must review it before the PR is final.
Branding: platform is **Akamai Cloud Compute** (not "Linode"); app type is "Quick Deploy App".
-->

# <App Name> Quick Deploy App

<App Name> is <one-line description of what the app does and who it's for>. This Marketplace App
deploys <App Name> <version> on Ubuntu 24.04 via <install method — e.g. Docker Compose / systemd>,
behind nginx with a Let's Encrypt certificate and <auth model: native login / nginx basic-auth>.

## Software Included

| Software | Version | Description |
| :---     | :----   | :---        |
| <App Name> | <version> | <what it is> |
| <dependency, e.g. PostgreSQL> | <version> | <role — e.g. backing store> |
| nginx    | <version> | Web server / reverse proxy |
| certbot  | <version> | Let's Encrypt TLS certificate client |

**Supported Distributions:**

- Ubuntu 24.04 LTS

## Linode Helpers Included

| Name  | Action  |
| :---  | :---    |
| Hostname | Assigns a hostname to the Linode based on the domain provided via UDF, or uses the default rDNS. For consistency, DNS and SSL configurations use the Hostname-generated `_domain` var. |
| Sudo User | Creates a limited `sudo` user from the UDF-supplied `username` and generates its password. Usernames containing illegal characters will cause the play to fail. |
| SSH Key | Writes a UDF-supplied SSH pubkey to `/home/$username/.ssh/authorized_keys`. To add an SSH key to `root`, use [Cloud Manager SSH Keys](https://www.linode.com/docs/products/tools/cloud-manager/guides/manage-ssh-keys/). |
| Secure SSH | Standard SSH hardening — writes to `/etc/ssh/sshd_config` to disable password auth and require public-key auth (applied only when `disable_root` is set). |
| Update Packages | Performs standard apt update and upgrade actions as root. |
| UFW | Imports `ufw_rules.yml` (22, 80, 443<, app ports>) and enables the firewall. <DB port, e.g. 5432, is not exposed.> |
| Fail2Ban | Installs, activates, and enables the Fail2Ban service. |
<!-- Include only the helpers this app actually uses; drop the rest. Common extras: -->
<!-- | Secure MySQL | Generates the DB root password, sets it, removes anonymous users + test database. | -->
<!-- | Docker | Installs Docker CE (used to run the <app> container/compose project). | -->
| Certbot SSL | Handles SSL/TLS certificate issuance via Let's Encrypt against nginx. |
| Addons | Optional monitoring/observability exporters (`newrelic`, `node_exporter`, `mysqld_exporter`, `opentelemetry_collector`, `alloy`). |

## Post-Deployment

When the playbook finishes, the operator can:

- Browse to the app at `https://<domain-or-rdns>/`<, log in to the admin area at `https://<domain-or-rdns>/<admin-path>/`>.
- Read the generated credentials from `/home/<sudo_user>/.credentials`. The file contains:
  - Sudo username + password
  - <App admin username + password>
  - <DB user + password + database name, if any>
  - App URL
- <first-run guidance — what a real user does next; link the upstream quickstart>.

<!-- REVIEW: confirm the post-deploy steps + credential contents against the actual deployed box. -->

## Use our API

Customers can deploy <App Name> through the Linode Marketplace or directly using the API. Before using the commands below, create an [API token](https://www.linode.com/docs/products/tools/linode-api/get-started/#create-an-api-token) or configure [linode-cli](https://www.linode.com/products/cli/), and substitute your own values for the defaults.

SHELL:
```
curl -H "Content-Type: application/json" \
-H "Authorization: Bearer $TOKEN" \
-X POST -d '{
    "image": "linode/ubuntu24.04",
    "region": "us-southeast",
    "type": "<g6-standard-2>",
    "label": "<app>-occ-us-southeast",
    "tags": [],
    "root_pass": "A_Secure_Password",
    "authorized_users": [
        "user1",
        "user2"
    ],
    "booted": true,
    "backups_enabled": false,
    "private_ip": false,
    "stackscript_id": 00000,
    "stackscript_data": {
        "soa_email_address": "email@domain.tld",
        "user_name": "sudo_user",
        "disable_root": "No",
        "token_password": "A_Valid_API_Token",
        "subdomain": "examplesubdomain",
        "domain": "domain.tld",
        "add_ons": "none"
    }
}' https://api.linode.com/v4/linode/instances
```
<!-- REVIEW: add any app-specific UDFs to stackscript_data (and the CLI form) — pull them from the StackScript #<UDF ...> declarations. -->

CLI:
```
linode-cli linodes create \
  --image 'linode/ubuntu24.04' \
  --region us-southeast \
  --type <g6-standard-2> \
  --label <app>-occ-us-southeast \
  --root_pass A_Secure_Password \
  --authorized_users user1 \
  --authorized_users user2 \
  --booted true \
  --backups_enabled false \
  --private_ip false \
  --stackscript_id 000000 \
  --stackscript_data '{"soa_email_address":"email@domain.tld","user_name":"sudo_user","disable_root":"No","token_password":"A_Valid_API_Token","subdomain":"examplesubdomain","domain":"domain.tld","add_ons":"none"}'
```

## Resources

- [<App Name> Documentation](<docs-url>)
- [<App Name> Repository](<repo-url>)
- <Akamai Marketplace guide URL, if one exists>
