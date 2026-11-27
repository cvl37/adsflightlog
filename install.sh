#!/usr/bin/env bash
# Install adsflightlog as two systemd services (collector + web UI).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
USER_NAME="${SUDO_USER:-$(id -un)}"

if [[ ! -f "$DIR/config.toml" ]]; then
  cp "$DIR/config.example.toml" "$DIR/config.toml"
  if [[ -r /run/readsb/receiver.json ]]; then
    read -r LAT LON < <(python3 -c 'import json;d=json.load(open("/run/readsb/receiver.json"));print(d["lat"],d["lon"])')
    sed -i "s|^# lat = .*|lat = $LAT|; s|^# lon = .*|lon = $LON|" "$DIR/config.toml"
  fi
  echo "Created config.toml — check location and max_distance_km before continuing."
fi

for svc in collector web; do
  sed "s|@DIR@|$DIR|g; s|@USER@|$USER_NAME|g" "$DIR/systemd/adsflightlog-$svc.service" \
    | sudo tee "/etc/systemd/system/adsflightlog-$svc.service" >/dev/null
done
sudo systemctl daemon-reload
sudo systemctl enable --now adsflightlog-collector adsflightlog-web
PORT=$(python3 -c "import sys;sys.path.insert(0,'$DIR');from adsflightlog import config;print(config.load('$DIR/config.toml').web_port)")
echo "Done. Open http://$(hostname -I | awk '{print $1}'):$PORT/"
