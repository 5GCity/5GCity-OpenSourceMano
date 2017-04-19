#!/bin/bash

function usage(){
    echo -e "usage: sudo $0 [OPTIONS]"
    echo -e "Install openmano database server"
    echo -e "On a Ubuntu 16.04 it configures openmano as a service"
    echo -e "  OPTIONS"
    echo -e "     -u USER:    database admin user. 'root' by default. Prompts if needed"
    echo -e "     -p PASS:    database admin password to be used or installed. Prompts if needed"
    echo -e "     -q --quiet: install in unattended mode"
    echo -e "     -h --help:  show this help"
    echo -e "     --forcedb:  reinstall mano_db DB, deleting previous database if exists and creating a new one"
    echo -e "     --no-install-packages: use this option to skip updating and installing the requires packages. This avoid wasting time if you are sure requires packages are present e.g. because of a previous installation"
}

function install_packages(){
    [ -x /usr/bin/apt-get ] && apt-get install -y $*
    [ -x /usr/bin/yum ]     && yum install     -y $*   
    
    #check properly installed
    for PACKAGE in $*
    do
        PACKAGE_INSTALLED="no"
        [ -x /usr/bin/apt-get ] && dpkg -l $PACKAGE            &>> /dev/null && PACKAGE_INSTALLED="yes"
        [ -x /usr/bin/yum ]     && yum list installed $PACKAGE &>> /dev/null && PACKAGE_INSTALLED="yes" 
        if [ "$PACKAGE_INSTALLED" = "no" ]
        then
            echo "failed to install package '$PACKAGE'. Revise network connectivity and try again" >&2
            exit 1
       fi
    done
}

function db_exists() {
    RESULT=`mysqlshow --defaults-extra-file="$2" | grep -v Wildcard | grep -o $1`
    if [ "$RESULT" == "$1" ]; then
        echo " DB $1 exists"
        return 0
    fi
    echo " DB $1 does not exist"
    return 1
}


DBUSER="root"
DBPASSWD=""
DBPASSWD_PARAM=""
QUIET_MODE=""
FORCEDB=""
NO_PACKAGES=""
while getopts ":u:p:hiq-:" o; do
    case "${o}" in
        u)
            export DBUSER="$OPTARG"
            ;;
        p)
            export DBPASSWD="$OPTARG"
            export DBPASSWD_PARAM="-p$OPTARG"
            ;;
        q)
            export QUIET_MODE=yes
            export DEBIAN_FRONTEND=noninteractive
            ;;
        h)
            usage && exit 0
            ;;
        -)
            [ "${OPTARG}" == "help" ] && usage && exit 0
            [ "${OPTARG}" == "forcedb" ] && FORCEDB="y" && continue
            [ "${OPTARG}" == "quiet" ] && export QUIET_MODE=yes && export DEBIAN_FRONTEND=noninteractive && continue
            [ "${OPTARG}" == "no-install-packages" ] && export NO_PACKAGES=yes && continue
            echo -e "Invalid option: '--$OPTARG'\nTry $0 --help for more information" >&2 
            exit 1
            ;; 
        \?)
            echo -e "Invalid option: '-$OPTARG'\nTry $0 --help for more information" >&2
            exit 1
            ;;
        :)
            echo -e "Option '-$OPTARG' requires an argument\nTry $0 --help for more information" >&2
            exit 1
            ;;
        *)
            usage >&2
            exit 1
            ;;
    esac
done

HERE=$(realpath $(dirname $0))
OPENMANO_BASEFOLDER=$(dirname $HERE)

#Discover Linux distribution
#try redhat type
[ -f /etc/redhat-release ] && _DISTRO=$(cat /etc/redhat-release 2>/dev/null | cut  -d" " -f1) 
#if not assuming ubuntu type
[ -f /etc/redhat-release ] || _DISTRO=$(lsb_release -is  2>/dev/null)            

if [[ -z "$NO_PACKAGES" ]]
then
    echo '
#################################################################
#####               INSTALL REQUIRED PACKAGES               #####
#################################################################'
    [ "$_DISTRO" == "Ubuntu" ] && install_packages "mysql-server"
    [ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ] && install_packages "mariadb mariadb-server"

    if [[ "$_DISTRO" == "Ubuntu" ]]
    then
        #start services. By default CentOS does not start services
        service mysql start >> /dev/null
        # try to set admin password, ignore if fails
        [[ -n $DBPASSWD ]] && mysqladmin -u $DBUSER -s password $DBPASSWD
    fi

    if [ "$_DISTRO" == "CentOS" -o "$_DISTRO" == "Red" ]
    then
        #start services. By default CentOS does not start services
        service mariadb start
        service httpd   start
        systemctl enable mariadb
        systemctl enable httpd
        read -e -p "Do you want to configure mariadb (recommended if not done before) (Y/n)" KK
        [ "$KK" != "n" -a  "$KK" != "no" ] && mysql_secure_installation

        read -e -p "Do you want to set firewall to grant web access port 80,443  (Y/n)" KK
        [ "$KK" != "n" -a  "$KK" != "no" ] && 
            firewall-cmd --permanent --zone=public --add-service=http &&
            firewall-cmd --permanent --zone=public --add-service=https &&
            firewall-cmd --reload
    fi
fi  #[[ -z "$NO_PACKAGES" ]]

#check and ask for database user password. Must be done after database installation
if [[ -n $QUIET_MODE ]]
then 
    echo -e "\nCheking database connection and ask for credentials"
    while ! mysqladmin -s -u$DBUSER $DBPASSWD_PARAM status >/dev/null
    do
        [ -n "$logintry" ] &&  echo -e "\nInvalid database credentials!!!. Try again (Ctrl+c to abort)"
        [ -z "$logintry" ] &&  echo -e "\nProvide database credentials"
        read -e -p "database user? ($DBUSER) " DBUSER_
        [ -n "$DBUSER_" ] && DBUSER=$DBUSER_
        read -e -s -p "database password? (Enter for not using password) " DBPASSWD_
        [ -n "$DBPASSWD_" ] && DBPASSWD="$DBPASSWD_" && DBPASSWD_PARAM="-p$DBPASSWD_"
        [ -z "$DBPASSWD_" ] && DBPASSWD=""           && DBPASSWD_PARAM=""
        logintry="yes"
    done
fi

echo '
#################################################################
#####        CREATE DATABASE                                #####
#################################################################'
echo -e "\nCreating temporary file form MYSQL installation and initialization"
TEMPFILE="$(mktemp -q --tmpdir "installopenmano.XXXXXX")"
trap 'rm -f "$TEMPFILE"' EXIT
chmod 0600 "$TEMPFILE"
echo -e "[client]\n user='$DBUSER'\n password='$DBPASSWD'">"$TEMPFILE"

if db_exists "mano_db" $TEMPFILE ; then
    if [[ -n $FORCEDB ]]; then
        echo "   Deleting previous database mano_db"
        DBDELETEPARAM=""
        [[ -n $QUIET_MODE ]] && DBDELETEPARAM="-f"
        mysqladmin --defaults-extra-file=$TEMPFILE -s drop mano_db $DBDELETEPARAM || ! echo "Could not delete mano_db database" || exit 1
        #echo "REVOKE ALL PRIVILEGES ON mano_db.* FROM 'mano'@'localhost';" | mysql --defaults-extra-file=$TEMPFILE -s || ! echo "Failed while creating user mano at database" || exit 1
        #echo "DELETE USER 'mano'@'localhost';"   | mysql --defaults-extra-file=$TEMPFILE -s || ! echo "Failed while creating user mano at database" || exit 1
        mysqladmin --defaults-extra-file=$TEMPFILE -s create mano_db || ! echo "Error creating mano_db database" || exit 1
        echo "CREATE USER 'mano'@'localhost' identified by 'manopw';"   | mysql --defaults-extra-file=$TEMPFILE -s || ! echo "Failed while creating user mano at database"
        echo "GRANT ALL PRIVILEGES ON mano_db.* TO 'mano'@'localhost';" | mysql --defaults-extra-file=$TEMPFILE -s || ! echo "Failed while creating user mano at database" || exit 1
        echo " Database 'mano_db' created, user 'mano' password 'manopw'"
    else
        echo "Database exists. Use option '--forcedb' to force the deletion of the existing one" && exit 1
    fi
else
    mysqladmin -u$DBUSER $DBPASSWD_PARAM -s create mano_db || ! echo "Error creating mano_db database" || exit 1 
    echo "CREATE USER 'mano'@'localhost' identified by 'manopw';"   | mysql --defaults-extra-file=$TEMPFILE -s || ! echo "Failed while creating user mano at database" || exit 1
    echo "GRANT ALL PRIVILEGES ON mano_db.* TO 'mano'@'localhost';" | mysql --defaults-extra-file=$TEMPFILE -s || ! echo "Failed while creating user mano at database" || exit 1
    echo " Database 'mano_db' created, user 'mano' password 'manopw'"
fi


echo '
#################################################################
#####        INIT DATABASE                                  #####
#################################################################'
su $SUDO_USER -c "${OPENMANO_BASEFOLDER}/database_utils/init_mano_db.sh -u mano -p manopw -d mano_db" || ! echo "Failed while initializing database" || exit 1
