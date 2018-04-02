#!/usr/bin/env bash
/bin/bash /root/MON/osm_mon/plugins/vRealiseOps/vROPs_Webservice/install.sh
nohup python /root/MON/osm_mon/plugins/OpenStack/Aodh/notifier.py &
python /root/MON/osm_mon/core/message_bus/common_consumer.py

