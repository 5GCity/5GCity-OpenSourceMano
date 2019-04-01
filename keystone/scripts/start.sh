#!/bin/bash

DB_EXISTS=""

max_attempts=120
function wait_db(){
    db_host=$1
    db_port=$2
    attempt=0
    echo "Wait until $max_attempts seconds for MySQL mano Server ${db_host}:${db_port} "
    while ! mysqladmin ping -h"$db_host" -P"$db_port" --silent; do
        #wait 120 sec
        if [ $attempt -ge $max_attempts ]; then
            echo
            echo "Can not connect to database ${db_host}:${db_port} during $max_attempts sec"
            return 1
        fi
        attempt=$[$attempt+1]
        echo -n "."
        sleep 1
    done
    return 0
}

function is_db_created() {
    db_host=$1
    db_port=$2
    db_user=$3
    db_pswd=$4
    db_name=$5

    if mysqlshow -h"$db_host" -P"$db_port" -u"$db_user" -p"$db_pswd" | grep -v Wildcard | grep -q $db_name; then
        echo "DB $db_name exists"
        return 0
    else
        echo "DB $db_name does not exist"
        return 1
    fi
}

wait_db "$DB_HOST" "$DB_PORT" || exit 1

is_db_created "$DB_HOST" "$DB_PORT" "$ROOT_DB_USER" "$ROOT_DB_PASSWORD" "keystone" && DB_EXISTS="Y"

if [ -z $DB_EXISTS ]; then
    mysql -h"$DB_HOST" -P"$DB_PORT" -u"$ROOT_DB_USER" -p"$ROOT_DB_PASSWORD" --default_character_set utf8 -e "CREATE DATABASE keystone"
    mysql -h"$DB_HOST" -P"$DB_PORT" -u"$ROOT_DB_USER" -p"$ROOT_DB_PASSWORD" --default_character_set utf8 -e "GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'localhost' IDENTIFIED BY '$KEYSTONE_DB_PASSWORD'"
    mysql -h"$DB_HOST" -P"$DB_PORT" -u"$ROOT_DB_USER" -p"$ROOT_DB_PASSWORD" --default_character_set utf8 -e "GRANT ALL PRIVILEGES ON keystone.* TO 'keystone'@'%' IDENTIFIED BY '$KEYSTONE_DB_PASSWORD'"
fi

# Setting Keystone database connection
sed -i "721s%.*%connection = mysql+pymysql://keystone:$KEYSTONE_DB_PASSWORD@$DB_HOST:$DB_PORT/keystone%" /etc/keystone/keystone.conf

# Setting Keystone tokens
sed -i "2934s%.*%provider = fernet%" /etc/keystone/keystone.conf

# Populate Keystone database
if [ -z $DB_EXISTS ]; then
    su -s /bin/sh -c "keystone-manage db_sync" keystone
fi

# Initialize Fernet key repositories
keystone-manage fernet_setup --keystone-user keystone --keystone-group keystone
keystone-manage credential_setup --keystone-user keystone --keystone-group keystone

# Bootstrap Keystone service
if [ -z $DB_EXISTS ]; then
    keystone-manage bootstrap --bootstrap-password "$ADMIN_PASSWORD" \
        --bootstrap-admin-url http://keystone:5000/v3/ \
        --bootstrap-internal-url http://keystone:5000/v3/ \
        --bootstrap-public-url http://keystone:5000/v3/ \
        --bootstrap-region-id RegionOne
fi

# Restart Apache Service
service apache2 restart

cat << EOF >> setup_env
export OS_PROJECT_DOMAIN_NAME=default
export OS_USER_DOMAIN_NAME=default
export OS_PROJECT_NAME=admin
export OS_USERNAME=admin
export OS_PASSWORD=$ADMIN_PASSWORD
export OS_AUTH_URL=http://keystone:5000/v3
export OS_IDENTITY_API_VERSION=3
export OS_IMAGE_API_VERSION=2
EOF

source setup_env

# Create NBI User
if [ -z $DB_EXISTS ]; then
    openstack user create --domain default --password "$NBI_PASSWORD" nbi
    openstack project create --domain default --description "Service Project" service
    openstack role add --project service --user nbi admin
fi

while ps -ef | grep -v grep | grep -q apache2
do
    sleep 60
done

# Only reaches this point if apache2 stops running
# When this happens exits with error code
exit 1
