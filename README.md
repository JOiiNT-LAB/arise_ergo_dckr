# ARISE Ergo — ROS2 Ergonomic Analysis Pipeline

A complete stack for real-time human ergonomic assessment using a RealSense camera, ROS2, FIWARE Orion-LD, CrateDB, and Grafana.

---

## Table of Contents

1. [Docker Setup](#1-docker-setup)
2. [ROS2 Workspace Setup](#2-ros2-workspace-setup)
3. [Launching the ROS2 Pipeline](#3-launching-the-ros2-pipeline)
4. [FIWARE Stack](#4-fiware-stack)
5. [NGSI-LD Subscription](#5-ngsi-ld-subscription)
6. [Verify Data in CrateDB](#6-verify-data-in-cratedb)
7. [Grafana Dashboard](#7-grafana-dashboard)
8. [Appendix: Why We Don't Use Orion-LD's Native DDS Module](#appendix-why-we-dont-use-orion-lds-native-dds-module)

---

## 1. Docker Setup

> **Prerequisites**: an X11 session must be available on the host (this is a desktop/workstation setup, not a headless server) — `$DISPLAY` and `$HOME` are used by `docker-compose.yml` to forward the display into the container for GUI tools like RViz2. On a headless or SSH-only host, the RViz2 node started by [section 3](#3-launching-the-ros2-pipeline)'s launch file will fail silently with no clear error.

Fetch the ROS2 package submodules under `components/` (required before the first build — an empty `components/` tree will make later steps fail with confusing errors):

```bash
git submodule update --init --recursive
```

Copy `.env.example` to `.env` if you need to change `ROS_DOMAIN_ID` (default `26`) — it's the single source of truth read by both `docker-compose.yml` and the Dockerfile build, so it only needs to be set in one place. (`conf/orionld/config-dds.json`'s own `domain: 26` is a separate, currently-unused reference config — see the [Appendix](#appendix-why-we-dont-use-orion-lds-native-dds-module) — and is intentionally not wired to `.env`.)

Build the Docker image from scratch (no cache), then start the whole stack — both the ROS2 container and the FIWARE services (Orion-LD, CrateDB, QuantumLeap, Grafana) are defined in the same `docker-compose.yml`, so this one command brings up everything:

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

## 3. Launching the ROS2 Pipeline

Everything below used to require 6 separate terminals (camera, body detection, RViz2 with 3 manual panel setup steps, 2 calculator nodes, and the Orion bridge). It's now a single command, run inside the container:

```bash
ros2 launch /home/ros_user/catkin_ws/launch/arise_ergo.launch.py
```

This ([launch/arise_ergo.launch.py](launch/arise_ergo.launch.py)) starts, in order:

1. **RealSense camera** (`realsense2_camera`'s `rs_launch.py`) — publishes RGB/depth/pointcloud topics.
2. **Body tracking** (`hri_body_detect`'s `hri_body_detect_with_args.launch.py`) — detects skeleton keypoints from the camera stream.
3. **RViz2**, pre-loaded with [components/human_description/config/human.rviz](components/human_description/config/human.rviz) — no manual panel setup needed. Note the Fixed Frame is `body_default` (the actual published frame name; the pipeline just calls it "body" informally).
4. **`ergodata_calculator`** — computes joint angles (neck, trunk, arms, elbows, shoulders) and speed, publishing `/ergo_data`.
5. **`rula_calculator`** — runs the RULA (Rapid Upper Limb Assessment) scoring algorithm on top of `/ergo_data`.
6. **`orion_bridge.py`** — sends `/ergo_data` to the FIWARE Orion-LD context broker. (Not a registered `ros2 run` entry point yet, so the launch file invokes it directly via `python3`.)

> **Optional debug check**: `ros2 topic echo /ergo_data` in a separate terminal to inspect the live data without affecting the running pipeline.

> **Why a bridge node and not Orion-LD's native DDS module?** We evaluated routing `/ergo_data` straight into Orion-LD via its embedded [DDS-Enabler](https://github.com/eProsima/DDS-Enabler)-based DDS module ([conf/orionld/config-dds.json](conf/orionld/config-dds.json), still present but currently unused). It requires resolving the DDS message's structure at runtime via XTypes, and that resolution never completes between Vulcanexus Humble's Fast DDS (2.6.1) and the Fast DDS bundled in Orion-LD — confirmed on two Orion-LD releases, and affecting even built-in ROS2 types, not just `ErgoData`. `orion_bridge.py` sidesteps this entirely: it's a ROS2 node using the same Fast DDS 2.6.1 as the rest of the pipeline, so no dynamic type discovery is ever needed. See the [Appendix](#appendix-why-we-dont-use-orion-lds-native-dds-module) for the full investigation, including why aligning Fast DDS versions isn't a viable fix either.

---

## 4. FIWARE Stack

Nothing to do here — the FIWARE stack (Orion-LD, CrateDB, QuantumLeap, Grafana) was already started by `docker compose up -d` in [section 1](#1-docker-setup), since all services live in this repo's own `docker-compose.yml`.

---

## 5. NGSI-LD Subscription

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

## 6. Verify Data in CrateDB

> **Note:** The table is named `etergodata` (not `mtergodata`).

Query the most recent 3 records to confirm data is flowing:

```bash
curl -s "http://localhost:4200/_sql" \
  -H "Content-Type: application/json" \
  -d '{"stmt": "SELECT * FROM etergodata ORDER BY time_index DESC LIMIT 3"}' \
  | python3 -m json.tool
```

---

## 7. Grafana Dashboard

The CrateDB data source and the `AriseDashboard` dashboard are both auto-provisioned (see `conf/grafana/datasources/datasource.yaml` and `conf/grafana/dashboards/AriseDashboard.json`, mounted in `docker-compose.yml`) — no manual setup needed.

Open [http://localhost:3000](http://localhost:3000), log in with `admin` / `admin`, and open **AriseDashboard** from the dashboard list. Set the time range in the top-right corner to match your recording session.

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

---

## Appendix: Why We Don't Use Orion-LD's Native DDS Module

Before settling on `orion_bridge.py`, we tried to route `/ergo_data` straight into Orion-LD without any bridge process, using Orion-LD's experimental DDS module, which is built on eProsima's [DDS-Enabler](https://github.com/eProsima/DDS-Enabler). This section documents that investigation and why it was abandoned, so nobody re-attempts it without knowing the outcome.

### The idea

Orion-LD ships with a work-in-progress DDS module (enabled via the `-wip dds` CLI flag) that can act as a DDS participant, subscribe directly to DDS topics, and map them to NGSI-LD entities/attributes via a JSON config file (kept at [conf/orionld/config-dds.json](conf/orionld/config-dds.json) for reference, currently unused). In theory this removes the need for any custom code: ROS2 already publishes `/ergo_data` as a plain DDS topic (`rt/ergo_data`) under the hood, so Orion-LD could listen to it natively.

### What we configured

- `domain: 26` in `config-dds.json`, matching `ROS_DOMAIN_ID=26` used by the ROS2 container.
- A topic mapping `rt/ergo_data → ErgoData.ergoData` (the DDS module maps one DDS topic to one NGSI-LD attribute — it cannot split a single topic's fields into multiple flat attributes the way `orion_bridge.py` does).
- `ddsenabler.initial-publish-wait: 500`, matching the schema documented in the upstream [DDS-Enabler reference config](https://github.com/eProsima/DDS-Enabler/blob/main/ddsenabler/DDS_ENABLER_CONFIGURATION.json) (the value shipped with the Orion-LD image was `null`).

### What worked

- DDS-level discovery: the Orion-LD DDS participant reliably found the ROS2 participants on domain 26 and matched the `rt/ergo_data` topic (confirmed via `ros2 topic pub` no longer blocking on "Waiting for at least 1 matching subscription(s)...").
- Topic/type name recognition: the resulting NGSI-LD entity correctly showed `"ddsTypeName": "jntlb_fwk_msgs::msg::dds_::ErgoData_"`.

### What didn't work

The actual field values never arrived. The `ergoData` attribute stayed permanently at:

```json
"ergoData": {
    "type": "Property",
    "value": "uninitialized",
    "ddsTypeName": { "type": "Property", "value": "jntlb_fwk_msgs::msg::dds_::ErgoData_" }
}
```

Orion-LD's logs repeated the same warning for every single published sample, instead of progressing to a value write:

```
W: ... Handler.cpp[127]: add_data: Schema for type jntlb_fwk_msgs::msg::dds_::ErgoData_ not available.
```

We tested this on **two Orion-LD releases** — the pinned `1.8.0-PRE-1645` and a freshly pulled `1.13.0-PRE-1858` — with identical results.

### Root cause

The DDS module needs to resolve the DDS message's full structure *at runtime* via XTypes (since it has no message definitions compiled in — that's what makes it generic). That resolution never completes between **Vulcanexus Humble's Fast DDS (2.6.1)**, used by the whole ROS2 pipeline, and the (much newer) Fast DDS bundled inside the Orion-LD image. Crucially, the exact same "Schema ... not available" warning also appeared for **built-in ROS2 types** (`rmw_dds_common::msg::dds_::ParticipantEntitiesInfo_`, `rcl_interfaces::msg::dds_::ParameterEvent_`), not just our custom `ErgoData` message — proving this is a structural Fast DDS version/XTypes incompatibility, not a config mistake or a limitation specific to our message type.

### Decision

`orion_bridge.py` sidesteps this entirely: it's a plain ROS2 node using the exact same Fast DDS 2.6.1 as the rest of the pipeline, so no dynamic type discovery ever happens — it's statically compiled in, like any other ROS2 node talking to another ROS2 node. `config-dds.json` and the DDS module are left disabled (`-wip dds` removed from the `orion` service command in [docker-compose.yml](docker-compose.yml)) but the config file is kept in the repo for reference, in case a future Orion-LD/Fast-DDS release resolves the XTypes gap and this is worth revisiting.

### Update (2026-07-31): why "just pin the same Fast DDS version" doesn't work either

A natural follow-up idea is to fix the version mismatch directly — rebuild Orion-LD's DDS stack pinned to Fast DDS 2.6.1 (matching Vulcanexus Humble) instead of whatever newer version it bundles. We investigated this and it is a **dead end**, for reasons more fundamental than a simple version bump:

- `fiware/orion-ld:1.13.0-PRE-1858` is not a tagged release at all — it corresponds to an ad-hoc CI build off `develop` for PR [#1858](https://github.com/FIWARE/context.Orion-LD/pull/1858) ("Removed two macros from CMakeLists.txt.orion"). Its DDS stack is built by `docker/build-ubi/07.install-fastdds.sh`, which pins: Fast-CDR v2.3.0, **Fast-DDS v3.3.0**, dev-utils v1.3.0, DDS-Pipe v1.3.0, and `DDS-Enabler` on branch `append_action_infix`.
- Fast DDS 3.x (Aug 2024) is a breaking rewrite of 2.x (namespace `fastrtps`→`fastdds`, Fast-CDR v2 required, Dynamic Types API rewritten, XTypes bumped to 1.3) — not a drop-in swap.
- The blocker isn't just "which version to pick" — it's that **eProsima's DDS-Enabler, the actual component implementing the Orion-LD↔DDS bridge that `Handler.cpp` calls into, has never supported Fast DDS 2.x at any point in its history.** Its repo was created 2024-09-13, over a month *after* Fast DDS 3.0.0 shipped and more than two years after Fast DDS 2.6.1 (June 2022). Every commit and dependency pin in its history (`ddsenabler.repos`) targets Fast DDS 3.x branches/tags — tag `v1.0.0` (2025-08-19) explicitly pins Fast-DDS v3.3.0 / Fast-CDR v2.3.0, identical to what Orion-LD bundles today.
- `dev-utils` and `DDS-Pipe` *did* once support Fast DDS 2.x (dev-utils v0.1.0, Oct 2022, pinned Fast-DDS v2.8.0; DDS-Pipe v0.2.0, Jul 2023, pinned Fast-DDS v2.11.0), so those two links in the chain aren't the problem. DDS-Enabler is.

**Conclusion**: aligning Fast DDS versions would require writing a Fast-DDS-2.x-compatible version of DDS-Enabler from scratch (a new engineering effort against eProsima's old `fastrtps`-namespace API and XTypes 1.2), not a version pin or config change. This is out of scope here. **Do not re-attempt the native DDS module path** unless eProsima ships a DDS-Enabler release that targets Fast DDS 2.x, or the ROS2 side moves to a distro whose `rmw_fastrtps` supports Fast DDS 3.x (not the case for Humble, and not yet true for any released ROS2 distro as of this writing). `orion_bridge.py` remains the supported, permanent path.