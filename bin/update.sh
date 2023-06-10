#!/usr/bin/env bash

# make sure we are root
DIR="$(dirname "$(readlink -f "$0")")"
echo "${DIR}"

userid="$(id -u)"
if [ ! "$userid" = "0" ]; then
   echo "You have to run this script as root. eg."
   echo "  sudo $0"
   echo "Exiting."
   exit 9
fi

# find ini file

if [ -f /usr/local/etc/dshield.ini ]; then
    inifile="/usr/local/etc/dshield.ini"
fi
if [ -f /etc/dshield.ini ]; then
    inifile="/etc/dshield.ini"
fi
if [ -f ~/etc/dshield.ini ]; then
    inifile="$HOME/etc/dshield.ini"
fi
if [ -f ~/.dshield.ini ]; then
    inifile="$HOME/.dshield.ini"
fi

# shellcheck disable=SC2283,SC2086,SC1090
source <(grep = $inifile)

if [ "$1" == "--cron" ]; then
    if [ -n "$manualupdates" ]; then
        if [ "$manualupdates" == 1 ]; then
        exit
        fi
    fi
fi



if [ -z "$version" ]; then
    version=0;
fi

if [ -z "${email}" ]; then
    echo "No email configured! Check ${inifile} for the 'email' entry."
    exit 1
fi
if [ -z "${apikey}" ]; then
    echo "No API key configured! Check ${inifile} for the 'apikey' entry."
    exit 1
fi
if [ -z "${piid}" ]; then
    echo "piid is not set in the config! Check ${inifile} for the 'piid' entry."
    exit 1
fi

echo "Currently configured for $email userid $userid"
echo "Version installed: $version"
user=$(echo "$email" | sed 's/+/%2b/' | sed 's/@/%40/')
nonce=$(openssl rand -hex 10)
hash=$(echo -n "$email:$apikey" | openssl dgst -hmac "$nonce" -sha512 -hex | cut -f2 -d'=' | tr -d ' ')
checkapikey=$(curl -s "https://isc.sans.edu/api/checkapikey/$user/$nonce/$hash/$version/$piid")
if echo "$checkapikey" | grep -q '<result>ok</result>'; then
    echo "API Key OK"
    newversion=$(echo "$checkapikey" | grep -E -o '<version>[^<]+</version>'| grep -E -o '[0-9]+')
else
    echo "Bad API Key. check API key in /etc/dshield.ini"
    exit 1
fi

echo "Current Version: $newversion"

if [ "$newversion" -gt "$version" ]; then
    echo "Update"
    git checkout main
    git pull
    ./install.sh --update
else
    echo "No Update Required"
fi
