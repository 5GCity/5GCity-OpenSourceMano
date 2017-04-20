#!/bin/bash

function is_db_created() {
    db_host=$1
    db_port=$2
    db_user=$3
    db_pswd=$4
    db_name=$5

    RESULT=`mysqlshow -h"$db_host" -P"$db_port" -u"$db_user" -p"$db_pswd" | grep -v Wildcard | grep -o $db_name`
    if [ "$RESULT" == "$db_name" ]; then

        RESULT=`mysqlshow -h"$db_host" -P"$db_port" -u"$db_user" -p"$db_pswd" "$db_name" | grep -v Wildcard | grep schema_version`
        #TODO validate version
        if [ -n "$RESULT" ]; then
            echo " DB $db_name exists and inited"
            return 0
        else
            echo " DB $db_name exists BUT not inited"
            return 1
        fi
    fi
    echo " DB $db_name does not exist"
    return 1
}

echo "1/4 Apply config"
/opt/openmano-docker/configure.sh
[ $? -ne 0 ] && exit 1
echo "2/4 Wait for db"

/opt/openmano-docker/wait_db.sh
[ $? -ne 0 ] && exit 1

echo "3/4 Init database" && \
is_db_created "$DB_HOST" "$DB_PORT" "$DB_USER" "$DB_PSWD" "$DB_NAME"
if [ $? -ne 0 ]; then
    /opt/openmano/database_utils/init_mano_db.sh -u $DB_USER -p $DB_PSWD -h $DB_HOST -P $DB_PORT -d $DB_NAME
    [ $? -ne 0 ] && exit 1
else
    echo "    migrage database version"
    /opt/openmano/database_utils/migrate_mano_db.sh -u $DB_USER -p $DB_PSWD -h $DB_HOST -P $DB_PORT -d $DB_NAME
fi

echo "4/4 Try to start"
/opt/openmano/openmanod.py -c /opt/openmano/openmanod.cfg --log-file=/opt/openmano/logs/openmano.log