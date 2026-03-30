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

if [[ -n "${DISABLE_ROOT}" ]]; then
        UDF_VARS["DISABLE_ROOT"]="${DISABLE_ROOT}"
else
        UDF_VARS["DISABLE_ROOT"]="No"
fi

if [[ -n "${CLUSTER_NAME}" ]]; then
        UDF_VARS["CLUSTER_NAME"]="${CLUSTER_NAME}"
else
        UDF_VARS["CLUSTER_NAME"]="Galera Cluster"
fi

if [[ -n "${TOKEN_PASSWORD}" ]]; then
        UDF_VARS["TOKEN_PASSWORD"]="${TOKEN_PASSWORD}"
elif [[ -n "${LINODE_API_SECRET}" ]]; then
        UDF_VARS["TOKEN_PASSWORD"]="${LINODE_API_SECRET}"
else
        UDF_VARS["TOKEN_PASSWORD"]="HugsAreWorthMoreThanHandshakes"
fi

if [[ -n "${ADD_SSH_KEYS}" ]]; then
        UDF_VARS["ADD_SSH_KEYS"]="${ADD_SSH_KEYS}"
else
        UDF_VARS["ADD_SSH_KEYS"]="yes"
fi

if [[ -n "${SSLHEADER}" ]]; then
        UDF_VARS["SSLHEADER"]="${SSLHEADER}"
else
        UDF_VARS["SSLHEADER"]="Yes"
fi

if [[ -n "${COUNTRY_NAME}" ]]; then
        UDF_VARS["COUNTRY_NAME"]="${COUNTRY_NAME}"
else
        UDF_VARS["COUNTRY_NAME"]="US"
fi

if [[ -n "${STATE_OR_PROVINCE_NAME}" ]]; then
        UDF_VARS["STATE_OR_PROVINCE_NAME"]="${STATE_OR_PROVINCE_NAME}"
else
        UDF_VARS["STATE_OR_PROVINCE_NAME"]="Pennsylvania"
fi

if [[ -n "${LOCALITY_NAME}" ]]; then
        UDF_VARS["LOCALITY_NAME"]="${LOCALITY_NAME}"
else
        UDF_VARS["LOCALITY_NAME"]="Philadelphia"
fi

if [[ -n "${ORGANIZATION_NAME}" ]]; then
        UDF_VARS["ORGANIZATION_NAME"]="${ORGANIZATION_NAME}"
else
        UDF_VARS["ORGANIZATION_NAME"]="Akamai Technologies"
fi

if [[ -n "${EMAIL_ADDRESS}" ]]; then
        UDF_VARS["EMAIL_ADDRESS"]="${EMAIL_ADDRESS}"
else
        UDF_VARS["EMAIL_ADDRESS"]="webmaster@${DEFAULT_DNS}"
fi

if [[ -n "${CA_COMMON_NAME}" ]]; then
        UDF_VARS["CA_COMMON_NAME"]="${CA_COMMON_NAME}"
else
        UDF_VARS["CA_COMMON_NAME"]="Galera CA"
fi

if [[ -n "${COMMON_NAME}" ]]; then
        UDF_VARS["COMMON_NAME"]="${COMMON_NAME}"
else
        UDF_VARS["COMMON_NAME"]="Galera Server"
fi

if [[ -n "${CLUSTER_SIZE}" ]]; then
        UDF_VARS["CLUSTER_SIZE"]="${CLUSTER_SIZE}"
else
        UDF_VARS["CLUSTER_SIZE"]="3"
fi

set_vars() {
  for key in "${!UDF_VARS[@]}"; do
    export "${key}"="${UDF_VARS[$key]}"
  done
}

# main
set_vars