#!/bin/bash

##
# Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U.
# This file is part of openvim
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact with: nfvlabs@tid.es
##

#
#Upgrade/Downgrade openvim database preserving the content
#

DBUSER="vim"
DBPASS=""
DEFAULT_DBPASS="vimpw"
DBHOST=""
DBPORT="3306"
DBNAME="vim_db"
QUIET_MODE=""
#TODO update it with the last database version
LAST_DB_VERSION=23

# Detect paths
MYSQL=$(which mysql)
AWK=$(which awk)
GREP=$(which grep)

function usage(){
    echo -e "Usage: $0 OPTIONS [version]"
    echo -e "  Upgrades/Downgrades openvim database preserving the content."\
            "If [version]  is not provided, it is upgraded to the last version"
    echo -e "  OPTIONS"
    echo -e "     -u USER  database user. '$DBUSER' by default. Prompts if DB access fails"
    echo -e "     -p PASS  database password. If missing it tries without and '$DEFAULT_DBPASS' password before prompting"
    echo -e "     -P PORT  database port. '$DBPORT' by default"
    echo -e "     -h HOST  database host. 'localhost' by default"
    echo -e "     -d NAME  database name. '$DBNAME' by default.  Prompts if DB access fails"
    echo -e "     -q --quiet: Do not prompt for credentials and exit if cannot access to database"
    echo -e "     --help   shows this help"
}

while getopts ":u:p:P:h:d:q-:" o; do
    case "${o}" in
        u)
            DBUSER="$OPTARG"
            ;;
        p)
            DBPASS="$OPTARG"
            ;;
        P)
            DBPORT="$OPTARG"
            ;;
        d)
            DBNAME="$OPTARG"
            ;;
        h)
            DBHOST="$OPTARG"
            ;;
        q)
            export QUIET_MODE=yes
            ;;
        -)
            [ "${OPTARG}" == "help" ] && usage && exit 0
            [ "${OPTARG}" == "quiet" ] && export QUIET_MODE=yes && continue
            echo "Invalid option: '--$OPTARG'. Type --help for more information" >&2
            exit 1
            ;;
        \?)
            echo "Invalid option: '-$OPTARG'. Type --help for more information" >&2
            exit 1
            ;;
        :)
            echo "Option '-$OPTARG' requires an argument. Type --help for more information" >&2
            exit 1
            ;;
        *)
            usage >&2
            exit 1
            ;;
    esac
done
shift $((OPTIND-1))

DB_VERSION=$1

if [ -n "$DB_VERSION" ] ; then
    # check it is a number and an allowed one
    [ "$DB_VERSION" -eq "$DB_VERSION" ] 2>/dev/null || 
        ! echo "parameter 'version' requires a integer value" >&2 || exit 1
    if [ "$DB_VERSION" -lt 0 ] || [ "$DB_VERSION" -gt "$LAST_DB_VERSION" ] ; then
        echo "parameter 'version' requires a valid database version between '0' and '$LAST_DB_VERSION'"\
             "If you need an upper version, get a newer version of this script '$0'" >&2
        exit 1
    fi
else
    DB_VERSION="$LAST_DB_VERSION"
fi

# Creating temporary file
TEMPFILE="$(mktemp -q --tmpdir "migratevimdb.XXXXXX")"
trap 'rm -f "$TEMPFILE"' EXIT
chmod 0600 "$TEMPFILE"
DEF_EXTRA_FILE_PARAM="--defaults-extra-file=$TEMPFILE"
echo -e "[client]\n user='${DBUSER}'\n password='$DBPASS'\n host='$DBHOST'\n port='$DBPORT'" > "$TEMPFILE"

# Check and ask for database user password
FIRST_TRY="yes"
while ! DB_ERROR=`mysql "$DEF_EXTRA_FILE_PARAM" $DBNAME -e "quit" 2>&1 >/dev/null`
do
    # if password is not provided, try silently with $DEFAULT_DBPASS before exit or prompt for credentials
    [[ -n "$FIRST_TRY" ]] && [[ -z "$DBPASS" ]] && DBPASS="$DEFAULT_DBPASS" &&
        echo -e "[client]\n user='${DBUSER}'\n password='$DBPASS'\n host='$DBHOST'\n port='$DBPORT'" > "$TEMPFILE" &&
        continue
    echo "$DB_ERROR"
    [[ -n "$QUIET_MODE" ]] && echo -e "Invalid database credentials!!!" >&2 && exit 1
    echo -e "Provide database name and credentials (Ctrl+c to abort):"
    read -e -p "    mysql database name($DBNAME): " KK
    [ -n "$KK" ] && DBNAME="$KK"
    read -e -p "    mysql user($DBUSER): " KK
    [ -n "$KK" ] && DBUSER="$KK"
    read -e -s -p "    mysql password: " DBPASS
    echo -e "[client]\n user='${DBUSER}'\n password='$DBPASS'\n host='$DBHOST'\n port='$DBPORT'" > "$TEMPFILE"
    FIRST_TRY=""
    echo
done

DBCMD="mysql $DEF_EXTRA_FILE_PARAM $DBNAME"
#echo DBCMD $DBCMD

#GET DATABASE VERSION
# check that the database seems a openvim database
if ! echo -e "show create table instances;\nshow create table numas" | $DBCMD >/dev/null 2>&1
then
    echo "    database $DBNAME does not seem to be an openvim database" >&2
    exit 1;
fi

if ! echo 'show create table schema_version;' | $DBCMD >/dev/null 2>&1
then
    DATABASE_VER="0.0"
    DATABASE_VER_NUM=0
else
    DATABASE_VER_NUM=`echo "select max(version_int) from schema_version;" | $DBCMD | tail -n+2` 
    DATABASE_VER=`echo "select version from schema_version where version_int='$DATABASE_VER_NUM';" | $DBCMD | tail -n+2` 
    [ "$DATABASE_VER_NUM" -lt 0 -o "$DATABASE_VER_NUM" -gt 100 ] &&
        echo "    Error can not get database version ($DATABASE_VER?)" >&2 && exit 1
    #echo "_${DATABASE_VER_NUM}_${DATABASE_VER}"
fi

[ "$DATABASE_VER_NUM" -gt "$LAST_DB_VERSION" ] &&
    echo "Database has been upgraded with a newer version of this script. Use this version to downgrade" >&2 &&
    exit 1

#GET DATABASE TARGET VERSION
#DB_VERSION=0
#[ $OPENVIM_VER_NUM -gt 1091 ] && DATABASE_TARGET_VER_NUM=1   #>0.1.91 =>  1
#[ $OPENVIM_VER_NUM -ge 2003 ] && DATABASE_TARGET_VER_NUM=2   #0.2.03  =>  2
#[ $OPENVIM_VER_NUM -ge 2005 ] && DATABASE_TARGET_VER_NUM=3   #0.2.5   =>  3
#[ $OPENVIM_VER_NUM -ge 3001 ] && DATABASE_TARGET_VER_NUM=4   #0.3.1   =>  4
#[ $OPENVIM_VER_NUM -ge 4001 ] && DATABASE_TARGET_VER_NUM=5   #0.4.1   =>  5
#[ $OPENVIM_VER_NUM -ge 4002 ] && DATABASE_TARGET_VER_NUM=6   #0.4.2   =>  6
#[ $OPENVIM_VER_NUM -ge 4005 ] && DATABASE_TARGET_VER_NUM=7   #0.4.5   =>  7
#[ $OPENVIM_VER_NUM -ge 4010 ] && DATABASE_TARGET_VER_NUM=8   #0.4.10  =>  8
#[ $OPENVIM_VER_NUM -ge 5001 ] && DATABASE_TARGET_VER_NUM=9   #0.5.1   =>  9
#[ $OPENVIM_VER_NUM -ge 5002 ] && DATABASE_TARGET_VER_NUM=10  #0.5.2   => 10
#[ $OPENVIM_VER_NUM -ge 5004 ] && DATABASE_TARGET_VER_NUM=11  #0.5.4   => 11
#[ $OPENVIM_VER_NUM -ge 5005 ] && DATABASE_TARGET_VER_NUM=12  #0.5.5   => 12
#[ $OPENVIM_VER_NUM -ge 5006 ] && DATABASE_TARGET_VER_NUM=13  #0.5.6   => 13
#[ $OPENVIM_VER_NUM -ge 5007 ] && DATABASE_TARGET_VER_NUM=14  #0.5.7   => 14
#[ $OPENVIM_VER_NUM -ge 5008 ] && DATABASE_TARGET_VER_NUM=15  #0.5.8   => 15
#[ $OPENVIM_VER_NUM -ge 5009 ] && DATABASE_TARGET_VER_NUM=16  #0.5.9   => 16
#[ $OPENVIM_VER_NUM -ge 5010 ] && DATABASE_TARGET_VER_NUM=17  #0.5.10  => 17
#[ $OPENVIM_VER_NUM -ge 5013 ] && DATABASE_TARGET_VER_NUM=18  #0.5.13  => 18
#[ $OPENVIM_VER_NUM -ge 5015 ] && DATABASE_TARGET_VER_NUM=19  #0.5.15  => 19
#[ $OPENVIM_VER_NUM -ge 5017 ] && DATABASE_TARGET_VER_NUM=20   #0.5.17  => 20
#[ $OPENVIM_VER_NUM -ge 5018 ] && DATABASE_TARGET_VER_NUM=21   #0.5.18  => 21
#[ $OPENVIM_VER_NUM -ge 5021 ] && DATABASE_TARGET_VER_NUM=22   #0.5.21  => 22
#[ $OPENVIM_VER_NUM -ge 5024 ] && DATABASE_TARGET_VER_NUM=23   #0.5.24  => 23
# TODO ... put next versions here

function upgrade_to_1(){
    # echo "    upgrade database from version 0.0 to version 0.1"
    echo "      CREATE TABLE \`schema_version\`"
    sql "CREATE TABLE \`schema_version\` (
        \`version_int\` INT NOT NULL COMMENT 'version as a number. Must not contain gaps',
        \`version\` VARCHAR(20) NOT NULL COMMENT 'version as a text',
        \`openvim_ver\` VARCHAR(20) NOT NULL COMMENT 'openvim version',
        \`comments\` VARCHAR(2000) NULL COMMENT 'changes to database',
        \`date\` DATE NULL,
        PRIMARY KEY (\`version_int\`)
        )
        COMMENT='database schema control version'
        COLLATE='utf8_general_ci'
        ENGINE=InnoDB;"
    sql "INSERT INTO \`schema_version\` (\`version_int\`, \`version\`, \`openvim_ver\`, \`comments\`, \`date\`) "\
	    "VALUES (1, '0.1', '0.2.00', 'insert schema_version; alter nets with last_error column', '2015-05-05');"
    echo "      ALTER TABLE \`nets\`, ADD COLUMN \`last_error\`"
    sql "ALTER TABLE \`nets\` ADD COLUMN \`last_error\` VARCHAR(200) NULL AFTER \`status\`;"
}
function downgrade_from_1(){
    # echo "    downgrade database from version 0.1 to version 0.0"
    echo "      ALTER TABLE \`nets\` DROP COLUMN \`last_error\`"
    sql "ALTER TABLE \`nets\` DROP COLUMN \`last_error\`;"
    echo "      DROP TABLE \`schema_version\`"
    sql "DROP TABLE \`schema_version\`;"
}
function upgrade_to_2(){
    # echo "    upgrade database from version 0.1 to version 0.2"
    echo "      ALTER TABLE \`of_ports_pci_correspondence\` \`resources_port\` \`ports\` ADD COLUMN \`switch_dpid\`"
    for table in of_ports_pci_correspondence resources_port ports
    do
        sql "ALTER TABLE \`${table}\` "\
            "ADD COLUMN \`switch_dpid\` CHAR(23) NULL DEFAULT NULL AFTER \`switch_port\`; "
        sql "ALTER TABLE ${table} CHANGE COLUMN switch_port switch_port VARCHAR(24) NULL DEFAULT NULL;"
        [ $table == of_ports_pci_correspondence ] ||
            sql "ALTER TABLE ${table} DROP INDEX vlan_switch_port, ADD UNIQUE INDEX vlan_switch_port "\
                "(vlan, switch_port, switch_dpid);"
    done
    echo "      UPDATE procedure UpdateSwitchPort"
    sql "DROP PROCEDURE IF EXISTS UpdateSwitchPort;
        delimiter //
        CREATE PROCEDURE UpdateSwitchPort() MODIFIES SQL DATA SQL SECURITY INVOKER
        COMMENT 'Load the openflow switch ports from of_ports_pci_correspondece into resoureces_port and ports'
        BEGIN
            #DELETES switch_port entry before writing, because if not it fails for key constrains
            UPDATE ports
            RIGHT JOIN resources_port as RP on ports.uuid=RP.port_id
            INNER JOIN resources_port as RP2 on RP2.id=RP.root_id
            INNER JOIN numas on RP.numa_id=numas.id
            INNER JOIN hosts on numas.host_id=hosts.uuid
            INNER JOIN of_ports_pci_correspondence as PC on hosts.ip_name=PC.ip_name and RP2.pci=PC.pci
            SET ports.switch_port=null, ports.switch_dpid=null, RP.switch_port=null, RP.switch_dpid=null;
            #write switch_port into resources_port and ports
            UPDATE ports
            RIGHT JOIN resources_port as RP on ports.uuid=RP.port_id
            INNER JOIN resources_port as RP2 on RP2.id=RP.root_id
            INNER JOIN numas on RP.numa_id=numas.id
            INNER JOIN hosts on numas.host_id=hosts.uuid
            INNER JOIN of_ports_pci_correspondence as PC on hosts.ip_name=PC.ip_name and RP2.pci=PC.pci
            SET ports.switch_port=PC.switch_port, ports.switch_dpid=PC.switch_dpid, RP.switch_port=PC.switch_port, "\
                "RP.switch_dpid=PC.switch_dpid;
        END//
        delimiter ;"
    sql "INSERT INTO \`schema_version\` (\`version_int\`, \`version\`, \`openvim_ver\`, \`comments\`, \`date\`) "\
	    "VALUES (2, '0.2', '0.2.03', 'update Procedure UpdateSwitchPort', '2015-05-06');"
}
function upgrade_to_3(){
    # echo "    upgrade database from version 0.2 to version 0.3"
    echo "     change size of source_name at table resources_port"
    sql "ALTER TABLE resources_port CHANGE COLUMN source_name source_name VARCHAR(24) NULL DEFAULT NULL AFTER port_id;"
    echo "     CREATE PROCEDURE GetAllAvailablePorts"
    sql "delimiter //
        CREATE PROCEDURE GetAllAvailablePorts(IN Numa INT) CONTAINS SQL SQL SECURITY INVOKER
        COMMENT 'Obtain all -including those not connected to switch port- ports available for a numa'
        BEGIN
        SELECT port_id, pci, Mbps, Mbps - Mbps_consumed as Mbps_free, totalSRIOV - coalesce(usedSRIOV,0) as
            availableSRIOV, switch_port, mac
        FROM
        (
           SELECT id as port_id, Mbps, pci, switch_port, mac
           FROM resources_port
            WHERE numa_id = Numa AND id=root_id AND status = 'ok' AND instance_id IS NULL
        ) as A
        INNER JOIN
        (
           SELECT root_id, sum(Mbps_used) as Mbps_consumed, COUNT(id)-1 as totalSRIOV
            FROM resources_port
            WHERE numa_id = Numa AND status = 'ok'
            GROUP BY root_id
        ) as B
        ON A.port_id = B.root_id
        LEFT JOIN
        (
           SELECT root_id,  COUNT(id) as usedSRIOV
            FROM resources_port
            WHERE numa_id = Numa AND status = 'ok' AND instance_id IS NOT NULL
            GROUP BY root_id
        ) as C
        ON A.port_id = C.root_id
        ORDER BY Mbps_free, availableSRIOV, pci;
        END//
        delimiter ;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (3, '0.3', '0.2.5', 'New Procedure GetAllAvailablePorts', '2015-07-09');"
}

function upgrade_to_4(){
    # echo "    upgrade database from version 0.3 to version 0.4"
    echo "     remove unique VLAN index at 'resources_port', 'ports'"
    sql "ALTER TABLE resources_port DROP INDEX vlan_switch_port;"
    sql "ALTER TABLE ports          DROP INDEX vlan_switch_port;"
    echo "     change table 'ports'"
    sql "ALTER TABLE ports CHANGE COLUMN model model VARCHAR(12) NULL DEFAULT NULL COMMENT 'driver model for bridge "\
        "ifaces; PF,VF,VFnotShared for data ifaces' AFTER mac;"
    sql "ALTER TABLE ports DROP COLUMN vlan_changed;"
    sql "ALTER TABLE resources_port DROP COLUMN vlan;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (4, '0.4', '0.3.1', 'Remove unique index VLAN at resources_port', '2015-09-04');"
}

function upgrade_to_X(){
    #TODO, this change of foreign key does not work
    # echo "    upgrade database from version 0.X to version 0.X"
    sql "ALTER TABLE instances DROP FOREIGN KEY FK_instances_flavors, DROP INDEX FK_instances_flavors, "\
        "DROP FOREIGN KEY FK_instances_images, DROP INDEX FK_instances_flavors,;" 
    sql "ALTER TABLE instances ADD CONSTRAINT FK_instances_flavors FOREIGN KEY (flavor_id, tenant_id) "\
        "REFERENCES tenants_flavors (flavor_id, tenant_id), ADD CONSTRAINT FK_instances_images FOREIGN KEY "\
        "(image_id, tenant_id) REFERENCES tenants_images (image_id, tenant_id);"
}

function downgrade_from_2(){
    # echo "    downgrade database from version 0.2 to version 0.1"
    echo "      UPDATE procedure UpdateSwitchPort"
    sql "DROP PROCEDURE IF EXISTS UpdateSwitchPort;
        delimiter //
        CREATE PROCEDURE UpdateSwitchPort() MODIFIES SQL DATA SQL SECURITY INVOKER
        BEGIN
        UPDATE
            resources_port INNER JOIN (
                SELECT resources_port.id,KK.switch_port
                FROM resources_port INNER JOIN numas on resources_port.numa_id=numas.id
                    INNER JOIN hosts on numas.host_id=hosts.uuid
                    INNER JOIN of_ports_pci_correspondence as KK on hosts.ip_name=KK.ip_name and resources_port.pci=KK.pci
                ) as TABLA
            ON  resources_port.root_id=TABLA.id
        SET resources_port.switch_port=TABLA.switch_port
        WHERE resources_port.root_id=TABLA.id;
        END//
        delimiter ;"
    echo "      ALTER TABLE \`of_ports_pci_correspondence\` \`resources_port\` \`ports\` DROP COLUMN \`switch_dpid\`"
    for table in of_ports_pci_correspondence resources_port ports
    do
        [ $table == of_ports_pci_correspondence ] ||
            sql "ALTER TABLE ${table} DROP INDEX vlan_switch_port, ADD UNIQUE INDEX vlan_switch_port (vlan, switch_port);"
        sql "ALTER TABLE \`${table}\` DROP COLUMN \`switch_dpid\`;"
        switch_port_size=12
        [ $table == of_ports_pci_correspondence ] && switch_port_size=50
        sql "ALTER TABLE ${table} CHANGE COLUMN switch_port switch_port VARCHAR(${switch_port_size}) NULL DEFAULT NULL;"
    done
    sql "DELETE FROM \`schema_version\` WHERE \`version_int\` = '2';"
}
function downgrade_from_3(){
    # echo "    downgrade database from version 0.3 to version 0.2"
    echo "     change back size of source_name at table resources_port"
    sql "ALTER TABLE resources_port CHANGE COLUMN source_name source_name VARCHAR(20) NULL DEFAULT NULL AFTER port_id;"
    echo "      DROP PROCEDURE GetAllAvailablePorts"
    sql "DROP PROCEDURE GetAllAvailablePorts;"
    sql "DELETE FROM schema_version WHERE version_int = '3';"
}
function downgrade_from_4(){
    # echo "    downgrade database from version 0.4 to version 0.3"
    echo "     adding back unique index VLAN at 'resources_port','ports'"
    sql "ALTER TABLE resources_port ADD COLUMN vlan SMALLINT(5) UNSIGNED NULL DEFAULT NULL  AFTER Mbps_used;"
    sql "UPDATE resources_port SET vlan= 99+id-root_id WHERE id != root_id;"
    sql "ALTER TABLE resources_port ADD UNIQUE INDEX vlan_switch_port (vlan, switch_port, switch_dpid);"
    sql "ALTER TABLE    ports ADD UNIQUE INDEX vlan_switch_port (vlan, switch_port, switch_dpid);"
    echo "     change back table 'ports'"
    sql "ALTER TABLE ports CHANGE COLUMN model model VARCHAR(12) NULL DEFAULT NULL AFTER mac;"
    sql "ALTER TABLE ports ADD COLUMN vlan_changed SMALLINT(5) NULL DEFAULT NULL COMMENT '!=NULL when original vlan "\
        "have been changed to match a pmp net with all ports in the same vlan' AFTER switch_port;"
    sql "DELETE FROM schema_version WHERE version_int = '4';"
}


function upgrade_to_5(){
    # echo "    upgrade database from version 0.4 to version 0.5"
    echo "     add 'ip_address' to ports'"
    sql "ALTER TABLE ports ADD COLUMN ip_address VARCHAR(64) NULL DEFAULT NULL AFTER mac;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (5, '0.5', '0.4.1', 'Add ip_address to ports', '2015-09-04');"
}
function downgrade_from_5(){
    # echo "    downgrade database from version 0.5 to version 0.4"
    echo "     removing 'ip_address' from 'ports'"
    sql "ALTER TABLE ports DROP COLUMN ip_address;"
    sql "DELETE FROM schema_version WHERE version_int = '5';"
}

function upgrade_to_6(){
    # echo "    upgrade database from version 0.5 to version 0.6"
    echo "      Enlarge name, description to 255 at all database"
    for table in flavors images instances tenants
    do
        name_length=255
        [[ $table == tenants ]] || name_length=64
        echo -en "        $table               \r"
        sql "ALTER TABLE $table CHANGE COLUMN name name VARCHAR($name_length) NOT NULL, CHANGE COLUMN description "\
            "description VARCHAR(255) NULL DEFAULT NULL;"
    done
    echo -en "        hosts               \r"
    sql "ALTER TABLE hosts CHANGE COLUMN name name VARCHAR(255) NOT NULL, CHANGE COLUMN ip_name ip_name VARCHAR(64) "\
        "NOT NULL, CHANGE COLUMN user user VARCHAR(64) NOT NULL, CHANGE COLUMN password password VARCHAR(64) NULL "\
        "DEFAULT NULL, CHANGE COLUMN description description VARCHAR(255) NULL DEFAULT NULL, CHANGE COLUMN features "\
        "features VARCHAR(255) NULL DEFAULT NULL;"
    echo -en "        nets                \r"
    sql "ALTER TABLE nets CHANGE COLUMN name name VARCHAR(255) NOT NULL, CHANGE COLUMN last_error last_error "\
        "VARCHAR(255) NULL DEFAULT NULL, CHANGE COLUMN bind bind VARCHAR(36) NULL DEFAULT NULL;"
    echo -en "        instances           \r"
    sql "ALTER TABLE instances CHANGE COLUMN last_error last_error VARCHAR(255) NULL DEFAULT NULL;"
    echo -en "        ports               \r"
    sql "ALTER TABLE ports CHANGE COLUMN name name VARCHAR(64) NOT NULL, CHANGE COLUMN switch_port switch_port "\
        "VARCHAR(64) NULL DEFAULT NULL, CHANGE COLUMN switch_dpid switch_dpid VARCHAR(64) NULL DEFAULT NULL;"
    echo -en "        of_flows            \r"
    sql "ALTER TABLE of_flows CHANGE COLUMN name name VARCHAR(64) NOT NULL, CHANGE COLUMN net_id net_id VARCHAR(36) "\
        "NULL DEFAULT NULL, CHANGE COLUMN actions actions VARCHAR(255) NULL DEFAULT NULL;"
    echo -en "        of_ports_pci_cor... \r"
    sql "ALTER TABLE of_ports_pci_correspondence CHANGE COLUMN ip_name ip_name VARCHAR(64) NULL DEFAULT NULL, CHANGE "\
        "COLUMN switch_port switch_port VARCHAR(64) NULL DEFAULT NULL, CHANGE COLUMN switch_dpid switch_dpid "\
        "VARCHAR(64) NULL DEFAULT NULL;"
    echo -en "        resources_port      \r"
    sql "ALTER TABLE resources_port CHANGE COLUMN source_name source_name VARCHAR(64) NULL DEFAULT NULL, CHANGE "\
        "COLUMN switch_port switch_port VARCHAR(64) NULL DEFAULT NULL, CHANGE COLUMN switch_dpid switch_dpid "\
        "VARCHAR(64) NULL DEFAULT NULL;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) VALUES "\
        "(6, '0.6', '0.4.2', 'Enlarging name at database', '2016-02-01');"
}
function downgrade_from_6(){
    # echo "    downgrade database from version 0.6 to version 0.5"
    echo "      Change back name,description to shorter length at all database"
    for table in flavors images instances tenants
    do
         name_length=50
         [[ $table == flavors ]] || [[ $table == images ]] || name_length=36 
         echo -en "        $table               \r"
         sql "ALTER TABLE $table CHANGE COLUMN name name VARCHAR($name_length) NOT NULL, CHANGE COLUMN description "\
            "description VARCHAR(100) NULL DEFAULT NULL;"
    done
    echo -en "        hosts               \r"
    sql "ALTER TABLE hosts CHANGE COLUMN name name VARCHAR(36) NOT NULL, CHANGE COLUMN ip_name ip_name VARCHAR(36) "\
        "NOT NULL, CHANGE COLUMN user user VARCHAR(36) NOT NULL, CHANGE COLUMN password password VARCHAR(36) NULL "\
        "DEFAULT NULL, CHANGE COLUMN description description VARCHAR(100) NULL DEFAULT NULL, CHANGE COLUMN features "\
        "features VARCHAR(50) NULL DEFAULT NULL;"
    echo -en "        nets                \r"
    sql "ALTER TABLE nets CHANGE COLUMN name name VARCHAR(50) NOT NULL, CHANGE COLUMN last_error last_error "\
        "VARCHAR(200) NULL DEFAULT NULL, CHANGE COLUMN bind bind VARCHAR(36) NULL DEFAULT NULL;"
    echo -en "        instances           \r"
    sql "ALTER TABLE instances CHANGE COLUMN last_error last_error VARCHAR(200) NULL DEFAULT NULL;"
    echo -en "        ports               \r"
    sql "ALTER TABLE ports CHANGE COLUMN name name VARCHAR(25) NULL DEFAULT NULL, CHANGE COLUMN switch_port "\
        "switch_port VARCHAR(24) NULL DEFAULT NULL, CHANGE COLUMN switch_dpid switch_dpid VARCHAR(23) NULL DEFAULT NULL;"
    echo -en "        of_flows            \r"
    sql "ALTER TABLE of_flows CHANGE COLUMN name name VARCHAR(50) NULL DEFAULT NULL, CHANGE COLUMN net_id net_id "\
        "VARCHAR(50) NULL DEFAULT NULL, CHANGE COLUMN actions actions VARCHAR(100) NULL DEFAULT NULL;"
    echo -en "        of_ports_pci_cor... \r"
    sql "ALTER TABLE of_ports_pci_correspondence CHANGE COLUMN ip_name ip_name VARCHAR(50) NULL DEFAULT NULL, CHANGE "\
        "COLUMN switch_port switch_port VARCHAR(24) NULL DEFAULT NULL, CHANGE COLUMN switch_dpid switch_dpid "\
        "VARCHAR(23) NULL DEFAULT NULL;"
    echo -en "        resources_port      \r"
    sql "ALTER TABLE resources_port CHANGE COLUMN source_name source_name VARCHAR(24) NULL DEFAULT NULL, CHANGE "\
        "COLUMN switch_port switch_port VARCHAR(24) NULL DEFAULT NULL, CHANGE COLUMN switch_dpid switch_dpid "\
        "VARCHAR(23) NULL DEFAULT NULL;"
    sql "DELETE FROM schema_version WHERE version_int='6';"
}

function upgrade_to_7(){
    # echo "    upgrade database from version 0.6 to version 0.7"
    echo "     add 'bind_net','bind_type','cidr','enable_dhcp' to 'nets'"
    sql "ALTER TABLE nets ADD COLUMN cidr VARCHAR(64) NULL DEFAULT NULL AFTER bind, ADD COLUMN enable_dhcp "\
        "ENUM('true','false') NOT NULL DEFAULT 'false' after cidr, ADD COLUMN dhcp_first_ip VARCHAR(64) NULL "\
        "DEFAULT NULL AFTER enable_dhcp, ADD COLUMN dhcp_last_ip VARCHAR(64) NULL DEFAULT NULL AFTER dhcp_first_ip;"
    sql "ALTER TABLE nets CHANGE COLUMN bind provider VARCHAR(36) NULL DEFAULT NULL AFTER vlan;"
    sql "ALTER TABLE nets ADD COLUMN bind_net VARCHAR(36) NULL DEFAULT NULL COMMENT 'To connect with other net' "\
        "AFTER provider, ADD COLUMN bind_type VARCHAR(36)  NULL DEFAULT NULL COMMENT 'VLAN:<tag> to insert/remove' "\
        "after bind_net;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (7, '0.7', '0.4.5', 'Add bind_net to net table', '2016-02-12');"
}
function downgrade_from_7(){
    # echo "    downgrade database from version 0.7 to version 0.6"
    echo "     removing 'bind_net','bind_type','cidr','enable_dhcp' from 'nets'"
    sql "ALTER TABLE nets CHANGE COLUMN provider bind NULL DEFAULT NULL AFTER vlan;"
    sql "ALTER TABLE nets DROP COLUMN cidr, DROP COLUMN enable_dhcp, DROP COLUMN bind_net, DROP COLUMN bind_type, "\
        "DROP COLUMN dhcp_first_ip, DROP COLUMN dhcp_last_ip;"
    sql "DELETE FROM schema_version WHERE version_int = '7';"
}

function upgrade_to_8(){
    # echo "    upgrade database from version 0.7 to version 0.8"
    echo "     add column 'checksum' to 'images'"
    sql "ALTER TABLE images ADD COLUMN checksum VARCHAR(32) NULL AFTER name;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (8, '0.8', '0.4.10', 'add column checksum to images', '2016-09-30');"
}
function downgrade_from_8(){
    # echo "    downgrade database from version 0.8 to version 0.7"
    echo "     remove column 'checksum' from 'images'"
    sql "ALTER TABLE images DROP COLUMN checksum;"
    sql "DELETE FROM schema_version WHERE version_int = '8';"
}

function upgrade_to_9(){
    # echo "    upgrade database from version 0.8 to version 0.9"
    echo "     change length of columns 'path' and 'name' to 255 in table 'images', and change length of column "\
        "'name' to 255 in table 'flavors'"
    sql "ALTER TABLE images CHANGE COLUMN path path VARCHAR(255) NOT NULL AFTER uuid, CHANGE COLUMN name name "\
        "VARCHAR(255) NOT NULL AFTER path;"
    sql "ALTER TABLE flavors CHANGE COLUMN name name VARCHAR(255) NOT NULL AFTER uuid;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (9, '0.9', '0.5.1','increase length of columns path and name to 255 in table images, "\
        "and change length of column name to 255 in table flavors', '2017-01-10');"
}
function downgrade_from_9(){
    # echo "    downgrade database from version 0.9 to version 0.8"
    echo "     change length of columns 'path' and 'name' to 100 and 64 in table 'images'"
    sql "ALTER TABLE images CHANGE COLUMN path path VARCHAR(100) NOT NULL AFTER uuid, CHANGE COLUMN name name "\
        "VARCHAR(64) NOT NULL AFTER path;"
    sql "ALTER TABLE flavors CHANGE COLUMN name name VARCHAR(64) NOT NULL AFTER uuid;"
    sql "DELETE FROM schema_version WHERE version_int = '9';"
}

function upgrade_to_10(){
    # echo "    upgrade database from version 0.9 to version 0.10"
    echo "     change types at 'ports'"
    sql "ALTER TABLE ports CHANGE COLUMN type type ENUM('instance:bridge','instance:data','external','instance:ovs',"\
        "'controller:ovs') NOT NULL DEFAULT 'instance:bridge' AFTER status;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (10, '0.10', '0.5.2', 'change ports type, adding instance:ovs', '2017-02-01');"
}
function downgrade_from_10(){
    # echo "    downgrade database from version 0.10 to version 0.9"
    echo "     change back types at 'ports'"
    sql "ALTER TABLE ports CHANGE COLUMN type type ENUM('instance:bridge','instance:data','external') "\
        "NOT NULL DEFAULT 'instance:bridge' AFTER status;"
    sql "DELETE FROM schema_version WHERE version_int = '10';"
}

function upgrade_to_11(){
    # echo "    upgrade database from version 0.10 to version 0.11"
    echo "    Add gateway_ip colum to 'nets'"
    sql "ALTER TABLE nets ADD COLUMN gateway_ip VARCHAR(64) NULL DEFAULT NULL AFTER dhcp_last_ip;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (11, '0.11', '0.5.4', 'Add gateway_ip colum to nets', '2017-02-13');"
}
function downgrade_from_11(){
    # echo "    downgrade database from version 0.11 to version 0.10"
    echo "    Delete gateway_ip colum from 'nets'"
    sql "ALTER TABLE nets DROP COLUMN gateway_ip;"
    sql "DELETE FROM schema_version WHERE version_int = '11';"
}
function upgrade_to_12(){
    # echo "    upgrade database from version 0.11 to version 0.12"
    echo "    Create of_controller table "
    sql "CREATE TABLE ofcs (
        uuid VARCHAR(36) NOT NULL,
        name VARCHAR(255) NOT NULL,
        dpid VARCHAR(64) NOT NULL,
        ip VARCHAR(64) NOT NULL,
        port INT(5) NOT NULL,
        type VARCHAR(64) NOT NULL,
        version VARCHAR(12) NULL DEFAULT NULL,
        user VARCHAR(64) NULL DEFAULT NULL,
        password VARCHAR(64) NULL DEFAULT NULL,
        PRIMARY KEY (uuid)
        )
        COLLATE='utf8_general_ci'
        ENGINE=InnoDB;"
    echo "    Modify user_at for uuids table"
    sql "ALTER TABLE uuids  CHANGE COLUMN used_at used_at VARCHAR(64) NULL DEFAULT NULL "\
        "COMMENT 'Table that uses this UUID' ;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (12, '0.12', '0.5.5', 'Add of_controller table', '2017-02-17');"
}

function downgrade_from_12(){
    # echo "    downgrade database from version 0.12 to version 0.11"
    echo "    Delete ofcs table"
    sql "DROP TABLE ofcs;"
    sql "ALTER TABLE uuids  CHANGE COLUMN used_at used_at ENUM('flavors', 'hosts', 'images', 'instances', "\
        "'nets', 'ports', 'tenants') NULL DEFAULT NULL COMMENT 'Table that uses this UUID' ;"
    sql "DELETE FROM schema_version WHERE version_int = '12';"
}

function upgrade_to_13(){
    # echo "    upgrade database from version 0.12 to version 0.13"
    echo "    Create of_port_mapings table "
    sql "CREATE TABLE of_port_mappings (
        uuid VARCHAR(36) NOT NULL,
        ofc_id VARCHAR(36) NULL DEFAULT NULL,
        region VARCHAR(64) NULL DEFAULT NULL,
        compute_node VARCHAR(64) NULL DEFAULT NULL,
        pci VARCHAR(50) NULL DEFAULT NULL,
        switch_dpid VARCHAR(64) NULL DEFAULT NULL,
        switch_port VARCHAR(64) NULL DEFAULT NULL,
        switch_mac CHAR(18) NULL DEFAULT NULL,
        UNIQUE INDEX switch_dpid_switch_port (switch_dpid, switch_port),
        UNIQUE INDEX switch_dpid_switch_mac (switch_dpid, switch_mac),
        UNIQUE INDEX region_compute_node_pci (region, compute_node, pci),
        INDEX FK_of_port_mappings_ofcs (ofc_id),
        CONSTRAINT FK_of_port_mappings_ofcs FOREIGN KEY (ofc_id) REFERENCES ofcs (uuid) ON UPDATE CASCADE
        ON DELETE CASCADE)
        COLLATE='utf8_general_ci'
        ENGINE=InnoDB;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (13, '0.13', '0.5.6', 'Add of_port_mapings table', '2017-03-09');"
}

function downgrade_from_13(){
    # echo "    downgrade database from version 0.13 to version 0.12"
    echo "    Delete of_port_mappings table"
    sql "DROP TABLE of_port_mappings;"
    sql "DELETE FROM schema_version WHERE version_int = '13';"
}

function upgrade_to_14(){
    # echo "    upgrade database from version 0.13 to version 0.14"
    echo "    Add switch_mac, ofc_id colum to 'ports' and 'resources_port'"
    sql "ALTER TABLE ports
        ADD COLUMN switch_mac VARCHAR(18) NULL DEFAULT NULL AFTER switch_port,
        ADD COLUMN ofc_id VARCHAR(36) NULL DEFAULT NULL AFTER switch_dpid,
        ADD CONSTRAINT  FK_port_ofc_id  FOREIGN KEY (ofc_id) REFERENCES ofcs (uuid);"
    sql "ALTER TABLE resources_port
        ADD COLUMN switch_mac VARCHAR(18) NULL DEFAULT NULL AFTER switch_port,
        ADD COLUMN ofc_id VARCHAR(36) NULL DEFAULT NULL AFTER switch_dpid,
        ADD CONSTRAINT FK_resource_ofc_id FOREIGN KEY (ofc_id) REFERENCES ofcs (uuid);"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (14, '0.14', '0.5.7', 'Add switch_mac, ofc_id colum to ports and resources_port tables', '2017-03-09');"
}

function downgrade_from_14(){
    # echo "    downgrade database from version 0.14 to version 0.13"
    echo "    Delete switch_mac, ofc_id colum to 'ports'"
    sql "ALTER TABLE ports DROP COLUMN switch_mac, DROP COLUMN ofc_id, DROP FOREIGN KEY FK_port_ofc_id;"
    sql "ALTER TABLE resources_port DROP COLUMN switch_mac, DROP COLUMN ofc_id, DROP FOREIGN KEY FK_resource_ofc_id;"
    sql "DELETE FROM schema_version WHERE version_int = '14';"
}

function upgrade_to_15(){
    # echo "    upgrade database from version 0.14 to version 0.15"
    echo "    Add ofc_id colum to 'of_flows'"
    sql "ALTER TABLE of_flows ADD COLUMN ofc_id VARCHAR(36) NULL DEFAULT NULL AFTER net_id, ADD CONSTRAINT "\
        "FK_of_flows_ofcs FOREIGN KEY (ofc_id) REFERENCES ofcs (uuid) ON UPDATE CASCADE ON DELETE SET NULL;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (15, '0.15', '0.5.8', 'Add ofc_id colum to of_flows', '2017-03-15');"
}

function downgrade_from_15(){
    # echo "    downgrade database from version 0.15 to version 0.14"
    echo "    Delete ofc_id to 'of_flows'"
    sql "ALTER TABLE of_flows DROP COLUMN ofc_id, DROP FOREIGN KEY FK_of_flows_ofcs;"
    sql "DELETE FROM schema_version WHERE version_int = '15';"
}


function upgrade_to_16(){
    # echo "    upgrade database from version 0.15 to version 0.16"
    echo "    Add last_error and status colum to 'ofcs'"
    sql "ALTER TABLE ofcs ADD COLUMN last_error VARCHAR(255) NULL DEFAULT NULL AFTER password, "\
	    "ADD COLUMN status ENUM('ACTIVE','INACTIVE','ERROR') NULL DEFAULT 'ACTIVE' AFTER last_error;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (16, '0.16', '0.5.9', 'Add last_error and status colum to ofcs', '2017-03-17');"
}

function downgrade_from_16(){
    # echo "    downgrade database from version 0.16 to version 0.15"
    echo "    Delete last_error and status colum to 'ofcs'"
    sql "ALTER TABLE ofcs DROP COLUMN last_error, DROP COLUMN status;"
    sql "DELETE FROM schema_version WHERE version_int = '16';"
}

function upgrade_to_17(){
    # echo "    upgrade database from version 0.16 to version 0.17"
    echo "    Add pci to the unique indexes switch_dpid_switch_port switch_dpid_switch_mac at of_port_mappings"
    sql "ALTER TABLE of_port_mappings DROP INDEX switch_dpid_switch_port, "\
        "ADD UNIQUE INDEX switch_dpid_switch_port (switch_dpid, switch_port, pci);"
    sql "ALTER TABLE of_port_mappings DROP INDEX switch_dpid_switch_mac, "\
        "ADD UNIQUE INDEX switch_dpid_switch_mac (switch_dpid, switch_mac, pci);"
    echo "    Add nets_with_same_vlan to table ofcs"
    sql "ALTER TABLE ofcs ADD COLUMN nets_with_same_vlan ENUM('true','false') NOT NULL DEFAULT 'false' AFTER status;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (17, '0.17', '0.5.10', 'Add pci to unique index dpid port/mac at of_port_mappings', '2017-04-05');"
}

function downgrade_from_17(){
    # echo "    downgrade database from version 0.17 to version 0.16"
    echo "    Delete pci fromthe unique indexes switch_dpid_switch_port switch_dpid_switch_mac at of_port_mappings"
    sql "ALTER TABLE of_port_mappings DROP INDEX switch_dpid_switch_port, "\
        "ADD UNIQUE INDEX switch_dpid_switch_port (switch_dpid, switch_port);"
    sql "ALTER TABLE of_port_mappings DROP INDEX switch_dpid_switch_mac, "\
        "ADD UNIQUE INDEX switch_dpid_switch_mac (switch_dpid, switch_mac);"
    echo "    Remove nets_with_same_vlan from table ofcs"
    sql "ALTER TABLE ofcs DROP COLUMN nets_with_same_vlan;"
    sql "DELETE FROM schema_version WHERE version_int = '17';"
}

function upgrade_to_18(){
    echo "    Add 'region' at 'nets' and change unique index vlan+region"
    sql "ALTER TABLE nets ADD COLUMN region VARCHAR(64) NULL DEFAULT NULL AFTER admin_state_up, DROP INDEX type_vlan;"
    echo "    Fill 'region' with __OVS__/__DATA__ for OVS/openflow provider at nets"
    sql "UPDATE nets set region='__OVS__' where provider like 'OVS%';"
    sql "UPDATE nets set region='__DATA__' where type='data' or type='ptp';"
    echo "    Create new index region_vlan at nets"
	sql "ALTER TABLE nets ADD UNIQUE INDEX region_vlan (region, vlan);"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (18, '0.18', '0.5.13', 'Add region to nets, change vlan unique index', '2017-05-03');"
}

function downgrade_from_18(){
    echo "    Delete 'region' at 'nets' and change back unique index vlan+type"
    sql "ALTER TABLE nets DROP INDEX region_vlan, DROP COLUMN region;"
    echo "    Create back index type_vlan at nets"
	sql "ALTER TABLE nets ADD UNIQUE INDEX type_vlan (type, vlan);"
    sql "DELETE FROM schema_version WHERE version_int = '18';"
}

function upgrade_to_19(){
    echo "    Add 'keyfile' to 'hosts'"
    sql "ALTER TABLE hosts ADD COLUMN keyfile VARCHAR(255) NULL DEFAULT NULL AFTER password;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (19, '0.19', '0.5.15', 'Add keyfile to hosts', '2017-05-23');"
}

function downgrade_from_19(){
    echo "    Delete 'keyfile' from 'hosts'"
    sql "ALTER TABLE hosts DROP COLUMN keyfile;"
    sql "DELETE FROM schema_version WHERE version_int = '19';"
}

function upgrade_to_20(){
    echo "    Add 'image_size' to 'instance_devices'"
    sql "ALTER TABLE instance_devices ADD COLUMN image_size INT NULL DEFAULT NULL AFTER dev;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (20, '0.20', '0.5.17', 'Add image_size to instance_devices', '2017-06-01');"
}

function downgrade_from_20(){
    echo "    Delete 'image_size' from 'instance_devices'"
    sql "ALTER TABLE instance_devices DROP COLUMN image_size;"
    sql "DELETE FROM schema_version WHERE version_int = '20';"
}

function upgrade_to_21(){
    echo "    Add 'routes', 'links' and 'dns' to 'nets'"
    sql "ALTER TABLE nets ADD COLUMN dns VARCHAR(255) NULL AFTER gateway_ip, "\
        "ADD COLUMN links TEXT(2000)  NULL AFTER dns, "\
        "ADD COLUMN routes TEXT(2000)  NULL AFTER links;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (21, '0.21', '0.5.18', 'Add routes, links and dns to inets', '2017-06-21');"
}

function downgrade_from_21(){
    echo "    Delete 'routes', 'links' and 'dns' to 'nets'"
    sql "ALTER TABLE nets DROP COLUMN dns, DROP COLUMN links, DROP COLUMN routes;"
    sql "DELETE FROM schema_version WHERE version_int = '21';"
}

function upgrade_to_22(){
    echo "    Changed type of ram in 'flavors' from SMALLINT to MEDIUMINT"
    sql "ALTER TABLE flavors CHANGE COLUMN ram ram MEDIUMINT(7) UNSIGNED NULL DEFAULT NULL AFTER disk;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (22, '0.22', '0.5.21', 'Changed type of ram in flavors from SMALLINT to MEDIUMINT', '2017-11-14');"
}

function downgrade_from_22(){
    echo "    Changed type of ram in 'flavors' from MEDIUMINT to SMALLINT"
    sql "ALTER TABLE flavors CHANGE COLUMN ram ram SMALLINT(5) UNSIGNED NULL DEFAULT NULL AFTER disk;"
    sql "DELETE FROM schema_version WHERE version_int = '22';"
}

function upgrade_to_23(){
    echo "    Add 'hypervisor' and 'os_type' column to 'instances' table"
    sql "ALTER TABLE instances ADD COLUMN hypervisor enum('kvm','xen-unik','xenhvm') NOT NULL DEFAULT 'kvm' AFTER flavor_id;"
    sql "ALTER TABLE instances ADD COLUMN os_image_type VARCHAR(24) NOT NULL DEFAULT 'other' AFTER hypervisor;"
    echo "    Add 'hypervisors' column to 'hosts' table"
    sql "ALTER TABLE hosts ADD COLUMN hypervisors VARCHAR(255) NOT NULL DEFAULT 'kvm' AFTER features;"
    sql "INSERT INTO schema_version (version_int, version, openvim_ver, comments, date) "\
        "VALUES (23, '0.23', '0.5.24', 'Add hypervisor, os_type to instances and add hypervisors to hosts', '2018-03-20');"
}

function downgrade_from_23(){
    echo "    Remove 'hypervisor' and 'os_type' column from 'instances' table"
    sql "ALTER TABLE instances DROP COLUMN hypervisor;"
    sql "ALTER TABLE instances DROP COLUMN os_image_type;"
    echo "    Remove 'hypervisors' column from 'hosts' table"
    sql "ALTER TABLE hosts DROP COLUMN hypervisors;"
    sql "DELETE FROM schema_version WHERE version_int = '23';"
}

# TODO ... put functions here

# echo "db version = "${DATABASE_VER_NUM}
[ $DB_VERSION -eq $DATABASE_VER_NUM ] && echo "    current database version '$DATABASE_VER_NUM' is ok" && exit 0

# Create a backup database content
TEMPFILE2="$(mktemp -q --tmpdir "backupdb.XXXXXX.sql")"
trap 'rm -f "$TEMPFILE2"' EXIT
mysqldump $DEF_EXTRA_FILE_PARAM --add-drop-table --add-drop-database --routines --databases $DBNAME > $TEMPFILE2

function rollback_db()
{
    cat $TEMPFILE2 | mysql $DEF_EXTRA_FILE_PARAM && echo "    Aborted! Rollback database OK" ||
        echo "    Aborted! Rollback database FAIL"
    exit 1
}

function sql()    # send a sql command
{
    echo "$*" | $DBCMD || ! echo "    ERROR with command '$*'" || rollback_db
    return 0
}

#UPGRADE DATABASE step by step
while [ $DB_VERSION -gt $DATABASE_VER_NUM ]
do
    echo "    upgrade database from version '$DATABASE_VER_NUM' to '$((DATABASE_VER_NUM+1))'"
    DATABASE_VER_NUM=$((DATABASE_VER_NUM+1))
    upgrade_to_${DATABASE_VER_NUM}
    #FILE_="${DIRNAME}/upgrade_to_${DATABASE_VER_NUM}.sh"
    #[ ! -x "$FILE_" ] && echo "Error, can not find script '$FILE_' to upgrade" >&2 && exit -1
    #$FILE_ || exit -1  # if fail return
done

#DOWNGRADE DATABASE step by step
while [ $DB_VERSION -lt $DATABASE_VER_NUM ]
do
    echo "    downgrade database from version '$DATABASE_VER_NUM' to '$((DATABASE_VER_NUM-1))'"
    #FILE_="${DIRNAME}/downgrade_from_${DATABASE_VER_NUM}.sh"
    #[ ! -x "$FILE_" ] && echo "Error, can not find script '$FILE_' to downgrade" >&2 && exit -1
    #$FILE_ || exit -1  # if fail return
    downgrade_from_${DATABASE_VER_NUM}
    DATABASE_VER_NUM=$((DATABASE_VER_NUM-1))
done

#echo done

