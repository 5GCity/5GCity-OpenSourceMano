#!/bin/bash

#Database parameters
#db_host:   localhost
#db_user:   mano
#db_passwd: manopw
#db_name:   mano_db

sed -i "s/^db_host:.*/db_host: $DB_HOST/" /opt/openmano/openmanod.cfg
sed -i "s/^db_user:.*/db_user: $DB_USER/" /opt/openmano/openmanod.cfg
sed -i "s/^db_passwd:.*/db_passwd: $DB_PSWD/" /opt/openmano/openmanod.cfg
sed -i "s/^db_name:.*/db_name: $DB_NAME/" /opt/openmano/openmanod.cfg