#!/bin/bash

DEFAULT_DNS="$(hostname -I | awk '{print $1}'| tr '.' '-' | awk {'print $1 ".ip.linodeusercontent.com"'})"

# custom env variables from cli
if [[ -n ${INSTANCE_ENV} ]]; then
  custom_vars=(${INSTANCE_ENV})
  var_count=${#custom_vars[@]}
  count=0
  while [ ${count} -lt ${var_count} ]; do
    export ${custom_vars[count]}
  count=$(( $count + 1 ))
  done
fi

# UDF Variables

declare -A UDF_VARS

if [[ -n "${SUDO_USERNAME}" ]]; then
        UDF_VARS["SUDO_USERNAME"]="${SUDO_USERNAME}"
else
        UDF_VARS["SUDO_USERNAME"]="admin" # default
fi

if [[ -n "${DISABLE_ROOT}" ]]; then
        UDF_VARS["DISABLE_ROOT"]="${DISABLE_ROOT}"
else
        UDF_VARS["DISABLE_ROOT"]="No" # default
fi

if [[ -n "${TOKEN_PASSWORD}" ]]; then
        UDF_VARS["TOKEN_PASSWORD"]="${TOKEN_PASSWORD}"
elif [[ -n "${LINODE_API_SECRET}" ]]; then
        UDF_VARS["TOKEN_PASSWORD"]="${LINODE_API_SECRET}"
else
        UDF_VARS["TOKEN_PASSWORD"]="HugsAreWorthMoreThanHandshakes" # default
fi

if [[ -n "${CLUSTER_SIZE}" ]]; then
        UDF_VARS["CLUSTER_SIZE"]="${CLUSTER_SIZE}"
else
        UDF_VARS["CLUSTER_SIZE"]="3" # default
fi

if [[ -n "${ADD_SSH_KEYS}" ]]; then
        UDF_VARS["ADD_SSH_KEYS"]="${ADD_SSH_KEYS}"
else
        UDF_VARS["ADD_SSH_KEYS"]="yes" # default
fi

if [[ -n "${COUNTRY_NAME}" ]]; then
        UDF_VARS["COUNTRY_NAME"]="${COUNTRY_NAME}"
else
        UDF_VARS["COUNTRY_NAME"]="US" # default
fi

if [[ -n "${STATE_OR_PROVINCE_NAME}" ]]; then
        UDF_VARS["STATE_OR_PROVINCE_NAME"]="${STATE_OR_PROVINCE_NAME}"
else
        UDF_VARS["STATE_OR_PROVINCE_NAME"]="Pennsylvania" # default
fi

if [[ -n "${LOCALITY_NAME}" ]]; then
        UDF_VARS["LOCALITY_NAME"]="${LOCALITY_NAME}"
else
        UDF_VARS["LOCALITY_NAME"]="Philadelphia" # default
fi

if [[ -n "${ORGANIZATION_NAME}" ]]; then
        UDF_VARS["ORGANIZATION_NAME"]="${ORGANIZATION_NAME}"
else
        UDF_VARS["ORGANIZATION_NAME"]="Akamai Technologies" # default
fi

if [[ -n "${EMAIL_ADDRESS}" ]]; then
        UDF_VARS["EMAIL_ADDRESS"]="${EMAIL_ADDRESS}"
else
        UDF_VARS["EMAIL_ADDRESS"]="webmaster@${DEFAULT_DNS}" # default
fi

if [[ -n "${CA_COMMON_NAME}" ]]; then
        UDF_VARS["CA_COMMON_NAME"]="${CA_COMMON_NAME}"
else
        UDF_VARS["CA_COMMON_NAME"]="Couchbase RootCA" # default
fi

set_vars() {
  for key in "${!UDF_VARS[@]}"; do
    export "${key}"="${UDF_VARS[$key]}"
  done
}

# main
set_vars