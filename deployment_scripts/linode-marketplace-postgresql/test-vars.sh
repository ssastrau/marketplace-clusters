#!/bin/bash

DEFAULT_DNS="$(hostname -I | awk '{print $1}'| tr '.' '-' | awk {'print $1 ".ip.linodeusercontent.com"'})"

if [[ -n ${INSTANCE_ENV} ]]; then
  custom_vars=(${INSTANCE_ENV})
  var_count=${#custom_vars[@]}
  count=0
  while [ ${count} -lt ${var_count} ]; do
    export ${custom_vars[count]}
  count=$(( $count + 1 ))
  done
fi

declare -A UDF_VARS

if [[ -n "${SUDO_USERNAME}" ]]; then
        UDF_VARS["SUDO_USERNAME"]="${SUDO_USERNAME}"
else
        UDF_VARS["SUDO_USERNAME"]="admin"
fi

if [[ -n "${DISABLE_ROOT}" ]]; then
        UDF_VARS["DISABLE_ROOT"]="${DISABLE_ROOT}"
else
        UDF_VARS["DISABLE_ROOT"]="No"
fi

if [[ -n "${TOKEN_PASSWORD}" ]]; then
        UDF_VARS["TOKEN_PASSWORD"]="${TOKEN_PASSWORD}"
elif [[ -n "${LINODE_API_SECRET}" ]]; then
        UDF_VARS["TOKEN_PASSWORD"]="${LINODE_API_SECRET}"
else
        UDF_VARS["TOKEN_PASSWORD"]="HugsAreWorthMoreThanHandshakes"
fi

if [[ -n "${CLUSTER_NAME}" ]]; then
        UDF_VARS["CLUSTER_NAME"]="${CLUSTER_NAME}"
else
        UDF_VARS["CLUSTER_NAME"]="PostgreSQL Cluster"
fi

if [[ -n "${CLUSTER_SIZE}" ]]; then
        UDF_VARS["CLUSTER_SIZE"]="${CLUSTER_SIZE}"
else
        UDF_VARS["CLUSTER_SIZE"]="3"
fi

if [[ -n "${ADD_SSH_KEYS}" ]]; then
        UDF_VARS["ADD_SSH_KEYS"]="${ADD_SSH_KEYS}"
else
        UDF_VARS["ADD_SSH_KEYS"]="yes"
fi

set_vars() {
  for key in "${!UDF_VARS[@]}"; do
    export "${key}"="${UDF_VARS[$key]}"
  done
}

set_vars