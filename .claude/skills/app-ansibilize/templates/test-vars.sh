#!/bin/bash
# CI UDF defaults for <app>. Sourced before the deploy script so required UDF vars
# have sensible values when not explicitly set.
# Reference: deployment_scripts/linode-marketplace-hashicorp-nomad/test-vars.sh

DEFAULT_DNS="$(hostname -I | awk '{print $1}' | tr '.' '-' | awk '{print $1 ".ip.linodeusercontent.com"}')"

declare -A UDF_VARS

# pattern: use the env var if set, else a CI default
if [[ -n "${USER_NAME:-}" ]]; then UDF_VARS["USER_NAME"]="${USER_NAME}"; else UDF_VARS["USER_NAME"]="admin"; fi
if [[ -n "${DISABLE_ROOT:-}" ]]; then UDF_VARS["DISABLE_ROOT"]="${DISABLE_ROOT}"; else UDF_VARS["DISABLE_ROOT"]="No"; fi
if [[ -n "${SUBDOMAIN:-}" ]]; then UDF_VARS["SUBDOMAIN"]="${SUBDOMAIN}"; else UDF_VARS["SUBDOMAIN"]="${DEFAULT_DNS%%.*}"; fi
if [[ -n "${DOMAIN:-}" ]]; then UDF_VARS["DOMAIN"]="${DOMAIN}"; else UDF_VARS["DOMAIN"]="${DEFAULT_DNS#*.}"; fi
if [[ -n "${SOA_EMAIL_ADDRESS:-}" ]]; then UDF_VARS["SOA_EMAIL_ADDRESS"]="${SOA_EMAIL_ADDRESS}"; else UDF_VARS["SOA_EMAIL_ADDRESS"]="admin@${DEFAULT_DNS#*.}"; fi
# --- add app-specific UDF defaults here ---

set_vars() {
  for key in "${!UDF_VARS[@]}"; do
    export "${key}"="${UDF_VARS[$key]}"
  done
}

set_vars
