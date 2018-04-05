#!/bin/bash

CONFIG_FILENAME="osm_policy_agent.cfg"
rm $CONFIG_FILENAME 2> /dev/null
touch $CONFIG_FILENAME
echo "[policy_module]" >> $CONFIG_FILENAME
if ! [[ -z "${BROKER_URI}" ]]; then
    HOST=$(echo $BROKER_URI | cut -d: -f1)
    PORT=$(echo $BROKER_URI | cut -d: -f2)
    echo "kafka_server_host=$HOST" >> $CONFIG_FILENAME
    echo "kafka_server_port=$PORT" >> $CONFIG_FILENAME
fi