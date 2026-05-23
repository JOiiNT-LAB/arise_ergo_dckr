# ARISE Ergo — ROS2 Ergonomic Analysis Pipeline

A complete stack for real-time human ergonomic assessment using a RealSense camera, ROS2, FIWARE Orion-LD, CrateDB, and Grafana.

---

## Table of Contents

1. [Docker Setup](#1-docker-setup)
2. [ROS2 Workspace Setup](#2-ros2-workspace-setup)
3. [Launching the ROS2 Stack](#3-launching-the-ros2-stack)
4. [Visualization with RViz2](#4-visualization-with-rviz2)
5. [Ergonomic Data Nodes](#5-ergonomic-data-nodes)
6. [FIWARE Stack](#6-fiware-stack)
7. [NGSI-LD Subscription](#7-ngsi-ld-subscription)
8. [Verify Data in CrateDB](#8-verify-data-in-cratedb)
9. [Grafana Dashboard](#9-grafana-dashboard)

---

## 1. Docker Setup

Build the Docker image from scratch (no cache), then start the container:

```bash
# Full rebuild without cache
docker compose build --no-cache

# Standard build (uses cache)
docker compose build

# Allow Docker to access the local display (needed for GUI tools like RViz2)
xhost +local:docker

# Start the container in detached mode
docker compose up -d

# Open an interactive shell inside the container
docker exec -it arise_ergo_dckr bash
```

---

## 2. ROS2 Workspace Setup

Inside the container, install dependencies and build the workspace:

```bash
# Update apt packages
apt update

# Update rosdep index
rosdep update

# Install all ROS dependencies declared in the workspace packages
rosdep install --from-paths src --ignore-src -y

# Build the workspace with symlink-install for faster iteration
colcon build --symlink-install

# Source the workspace overlay
source install/setup.bash
```

---

## 3. Launching the ROS2 Stack

Each of the following commands runs in a **separate terminal** (all inside the container).

### Terminal 1 — RealSense Camera Node

```bash
ros2 launch realsense2_camera rs_launch.py
```

Starts the Intel RealSense camera driver and publishes RGB, depth, and pointcloud topics.

### Terminal 2 — Body Tracking Node

```bash
ros2 launch hri_body_detect hri_body_detect_with_args.launch.py
```

Detects human body keypoints from the camera stream and publishes skeleton data.

---

## 4. Visualization with RViz2

### Terminal 3 — RViz2

```bash
rviz2
```

Once open, add the following displays in the RViz2 panel:

| Display Type | Configuration |
|---|---|
| **Humans** | Set topic to `camera/color/` |
| **Skeleton Display** | Add and enable |
| **Fixed Frame** | Set to `body` (default) |

---

## 5. Ergonomic Data Nodes

### Terminal 4 — Ergo Data Calculator

```bash
ros2 run ergo_pkg_py ergodata_calculator
```

Computes joint angles (neck, trunk, arms, elbows, shoulders) and speed from the skeleton data.

### Terminal 5 — RULA Calculator

```bash
ros2 run ergo_pkg_py rula_calculator
```

Runs the RULA (Rapid Upper Limb Assessment) scoring algorithm on top of the computed angles.

### Terminal 6 — Verify & Bridge

```bash
# Inspect the live ergo_data topic
ros2 topic echo /ergo_data

# Send ergonomic data to the FIWARE Orion-LD context broker
python3 src/ergo_pkg_py/ergo_pkg_py/orion_bridge.py
```

---

## 6. FIWARE Stack

From a **new terminal** on the host machine, start the FIWARE stack (Orion-LD, CrateDB, Grafana, etc.):

```bash
cd ergo_dev
docker compose up -d
```

All services in the FIWARE stack will start automatically.

---

## 7. NGSI-LD Subscription

Create a subscription so Orion-LD notifies the QuantumLeap/CrateDB sink whenever `ErgoData` entities are updated:

```bash
curl -X POST http://localhost:1026/ngsi-ld/v1/subscriptions \
  -H "Content-Type: application/ld+json" \
  -d '{
    "id": "urn:ngsi-ld:Subscription:ErgoData",
    "type": "Subscription",
    "entities": [{"type": "ErgoData"}],
    "notification": {
      "endpoint": {
        "uri": "http://127.0.0.1:8668/v2/notify",
        "accept": "application/json"
      }
    },
    "@context": ["https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"]
  }'
```

---

## 8. Verify Data in CrateDB

> **Note:** The table is named `etergodata` (not `mtergodata`).

Query the most recent 3 records to confirm data is flowing:

```bash
curl -s "http://localhost:4200/_sql" \
  -H "Content-Type: application/json" \
  -d '{"stmt": "SELECT * FROM etergodata ORDER BY time_index DESC LIMIT 3"}' \
  | python3 -m json.tool
```

---

## 9. Grafana Dashboard

### Access Grafana

Open [http://localhost:3000](http://localhost:3000) and log in with `admin` / `admin`.

### Add the CrateDB Data Source

Go to **Connections → Data sources → Add new → PostgreSQL** and fill in the following:

| Field | Value |
|---|---|
| Host | `localhost:5432` |
| Database | `doc` |
| User | `crate` |
| Password | *(leave empty)* |
| TLS/SSL | `disable` |

Click **Save & Test** — you should see **"Database Connection OK"**.

### Create the Dashboard

1. Click **+** → **New dashboard** → **Add visualization**
2. Select the **CrateDB** data source you just added
3. Switch to **Code** mode and paste the following query:

```sql
SELECT
  to_timestamp(time_index / 1000.0) AS "time",
  neck_angle,
  trunk_angle,
  trunk_bending_angle,
  left_arm_angle,
  right_arm_angle,
  left_elbow_angle,
  right_elbow_angle,
  left_shoulder_angle,
  right_shoulder_angle,
  speed
FROM etergodata
WHERE to_timestamp(time_index / 1000.0) >= $__timeFrom()
  AND to_timestamp(time_index / 1000.0) <= $__timeTo()
ORDER BY time_index ASC
```

4. Set the time range in the top-right corner to match your recording session and click **Apply**.

---

## Architecture Overview

```
RealSense Camera
      │
      ▼
realsense2_camera (ROS2)
      │
      ▼
hri_body_detect  ──►  RViz2 (visualization)
      │
      ▼
ergodata_calculator
      │
      ▼
rula_calculator
      │
      ▼  /ergo_data topic
orion_bridge.py
      │
      ▼
Orion-LD (FIWARE)
      │  NGSI-LD Subscription
      ▼
QuantumLeap  ──►  CrateDB  ──►  Grafana
```