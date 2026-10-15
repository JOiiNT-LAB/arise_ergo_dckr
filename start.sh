#!/usr/bin/env bash
# Starts the FIWARE stack + ROS container, then launches the ergonomics pipeline
# in the foreground. Ctrl+C stops the pipeline; the containers stay up (./stop.sh).
#
# Extra arguments are passed to the launch file and override the defaults:
#   ./start.sh use_rviz:=false use_orion:=false body_min_age:=1.0 single_body:=false
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

# Let the container open RViz on this X session (harmless if there is no X11).
xhost +local:docker >/dev/null 2>&1 || true

docker compose up -d --no-build

# Orion-LD takes a few seconds to accept requests.
echo -n "Waiting for Orion-LD"
for _ in $(seq 1 30); do
  curl -sf http://localhost:1026/version >/dev/null && break
  echo -n "."; sleep 1
done
echo

# Open the Grafana dashboard in the browser once Grafana answers (login: admin / admin
# the first time). Set NO_BROWSER=1 to skip it.
if [ -z "${NO_BROWSER:-}" ] && command -v xdg-open >/dev/null; then
  (
    for _ in $(seq 1 60); do
      curl -sf http://localhost:3000/api/health >/dev/null && break
      sleep 1
    done
    xdg-open "http://localhost:3000/d/edw7n9k3jc4cge2/arisedashboard?refresh=5s" >/dev/null 2>&1
  ) &
fi

exec docker exec -it arise_ergo_dckr bash -lc '
  source /opt/ros/humble/setup.bash
  source /home/ros_user/catkin_ws/install/setup.bash
  exec ros2 launch /home/ros_user/catkin_ws/launch/arise_ergo.launch.py body_min_age:=4.0 "$@"
' _ "$@"
