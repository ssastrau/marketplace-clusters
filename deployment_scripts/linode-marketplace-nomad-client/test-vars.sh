#!/bin/bash

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

if [[ -n "${ADD_SSH_KEYS}" ]]; then
        UDF_VARS["ADD_SSH_KEYS"]="${ADD_SSH_KEYS}"
else
        UDF_VARS["ADD_SSH_KEYS"]="yes" # default
fi

if [[ -n "${CLUSTERHEADER}" ]]; then
        UDF_VARS["CLUSTERHEADER"]="${CLUSTERHEADER}"
else
        UDF_VARS["CLUSTERHEADER"]="Yes" # default
fi

if [[ -n "${CLUSTER_SIZE}" ]]; then
        UDF_VARS["CLUSTER_SIZE"]="${CLUSTER_SIZE}"
else
        UDF_VARS["CLUSTER_SIZE"]="3" # default
fi

if [[ -n "${CONSUL_NOMAD_AUTOJOIN_TOKEN_PASSWORD}" ]]; then
        UDF_VARS["CONSUL_NOMAD_AUTOJOIN_TOKEN_PASSWORD"]="${CONSUL_NOMAD_AUTOJOIN_TOKEN_PASSWORD}"
else
        UDF_VARS["CONSUL_NOMAD_AUTOJOIN_TOKEN_PASSWORD"]="CONSUL_NOMAD_AUTOJOIN_TOKEN_PASSWORD" # default
fi

set_vars() {
  for key in "${!UDF_VARS[@]}"; do
    export "${key}"="${UDF_VARS[$key]}"
  done
}

# main
set_vars