# /usr/bin/bash
set -eux

[ "$UID" -eq 0 ] || exec sudo bash "$0" "$@"

cp -f arkly-arweave-api.service /etc/systemd/system/arkly-arweave-api.service
systemctl daemon-reload
service arkly-arweave-api restart
systemctl enable arkly-arweave-api
service arkly-arweave-api status
