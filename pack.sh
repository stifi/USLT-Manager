#!/bin/bash

VERSION=`grep "^# *Version:" uslt_manager.py | cut -d ":" -f2 | sed 's/ //g'`
echo -n "Enter new verion (old ${VERSION}): "
read VERSION

sed -i 's/\(^#   Version: \).*$/\1'${VERSION}'/g' uslt_manager.py

./release.sh

tar --exclude='__pycache__' -czf ./releases/uslt_manager_v${VERSION}.tar.gz *.md uslt_manager.* *.py usltmodules mutagen 
chmod a-w ./releases/uslt_manager_v${VERSION}.tar.gz

echo -e "\e[31mDo not forget to run \e[1mgit tag v${VERSION}\e[0m"
