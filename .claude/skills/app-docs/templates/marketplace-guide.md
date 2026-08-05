---
title: "Deploy <App> through the Linode Marketplace"
description: "Learn how to deploy <App>, <short one-line description>, on an Akamai Compute Instance."
published: <YYYY-MM-DD>
keywords: ['<keyword>','<keyword>','<keyword>']
tags: ["marketplace", "linode platform", "cloud manager"]
external_resources:
- '[<App> Official Documentation](<official-docs-url>)'
aliases: ['/products/tools/marketplace/guides/<slug>/','/guides/<slug>-marketplace-app/']
authors: ["Akamai"]
contributors: ["Akamai"]
license: '[CC BY-ND 4.0](https://creativecommons.org/licenses/by-nd/4.0)'
marketplace_app_id: <numeric-id>
marketplace_app_name: "<App>"
---

<!--
  TEMPLATE NOTES (delete this block in the generated guide):
  - Fill every <placeholder> from grounded sources (see app-docs SKILL.md grounding contract).
  - `modified:` is optional — add it only when updating an already-published guide.
  - `marketplace_app_id` is assigned by Akamai at publish time. If unknown, leave a
    <!-- REVIEW: marketplace_app_id assigned at publish --> note rather than guessing.
  - Keep the section order and the {{% content … %}} shortcode includes below.
  - Drop the optional sections (Software Included, Going Further) if they don't apply.
-->

[<App>](<official-site-url>) is <one to three sentence intro: what the app is and what it's for>.

## Deploying a Marketplace App

{{% content "deploy-marketplace-apps-shortguide" %}}

{{% content "marketplace-verify-standard-shortguide" %}}

{{< note >}}
**Estimated deployment time:** <App> should be fully installed within <X-Y> minutes after the Compute Instance has finished provisioning.
{{< /note >}}

## Configuration Options

- **Supported distributions:** Ubuntu 24.04 LTS
- **Recommended plan:** <grounded sizing guidance — cite upstream docs or the tested plan from linode-config.sh>

### <App> Options

<!-- App-specific UDF fields from the deploy script. Omit this list if the app has no app-specific UDFs. -->
- **<Field label>** *(required)*: <description of what to enter, from the UDF label>.

{{% content "marketplace-required-limited-user-fields-shortguide" %}}

{{% content "marketplace-custom-domain-fields-shortguide" %}}

{{% content "marketplace-special-character-limitations-shortguide" %}}

## Getting Started after Deployment

<!--
  Choose ONE access pattern based on how the app is actually reached (per e2e_testing.md):
  A) Web UI with native login  → "Accessing the <App> Web Interface"
  B) API-/client-only (no UI)  → "Obtain Your Credentials" / "Connect Your Application"
-->

### Accessing the <App> Web Interface

1.  Open your web browser and navigate to `https://[domain]`, where *[domain]* is the custom domain you entered during deployment or your Compute Instance's rDNS domain (such as `192-0-2-1.ip.linodeusercontent.com`). To learn more about viewing IP addresses and rDNS, see the [Managing IP Addresses](/docs/products/compute/compute-instances/guides/manage-ip-addresses/).

    ![Screenshot of the <App> login page](<slug>-login.png)
    <!-- REVIEW: capture + add this screenshot -->

1.  Use the following credentials to log in:
    - **Username:** *<default username, grounded from the compose env / architecture notes>*
    - **Password:** Enter the password stored in the credentials file on your server. To obtain it, log in to your Compute Instance via SSH or Lish and run:

        ```command
        cat /home/$USER/.credentials
        ```

<closing sentence(s): what the user can now do in the app; link to the upstream quickstart>

## Software Included

The <App> Marketplace App installs the following software on your Compute Instance:

| **Software** | **Description** |
|:---|:---|
| [**<Software>**](<url>) | <one-line description> |

## Going Further

<!-- Optional: links to upstream docs, quickstart, the Marketplace Apps repository, related guides. -->

{{% content "marketplace-update-note-shortguide" %}}
