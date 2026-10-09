# Branch notes — `feature/ros4hri-ergo-advisor`

Status: 2026-10-09. This file records what changed on this branch compared with
`main_integration`, why, how it was checked and what is still open. The README
describes the pipeline as it is now; this file explains how it got there. The
package-level notes are in
[components/ergo_pkg_py/docs/BRANCH_NOTES.md](../components/ergo_pkg_py/docs/BRANCH_NOTES.md).

## What the branch does

| Area | Change | Commits |
|---|---|---|
| ROS4HRI layout | Every ergonomic topic is per body, `/humans/bodies/<body_id>/…`; nodes follow `/humans/bodies/tracked` | earlier work, `20a2961`, `735a2a3` |
| Messages | `jntlb_fwk_msgs` submodule replaced by the `hri_ergonomics_msgs` package of this repo | `735a2a3` |
| Advisor | `ergo_advisor` explains alerts with a local LLM (Ollama, optional profile `llm`) | `20a2961` |
| Subscription | The NGSI-LD subscription Orion → QuantumLeap is created at QuantumLeap start; a paused subscription is resumed | `5d4a308`, `911acad` |
| Scores in FIWARE | RULA/REBA partial scores and the alert state reach Orion, CrateDB and Grafana (new risk panels) | `20ea68b` (+ `ergo_pkg_py` `0f9e7a4`) |
| Short-lived ids | A new body id is acted upon only after `body_min_age` seconds (default 1.0) | `bb871e2` (+ `ergo_pkg_py` `b91d298`) |
| Body detector | `hri_body_detect` is now upstream `ros4hri/hri_body_detect` 3.4.1, not the JOiiNT fork; `hri_msgs` 2.3.2 is a submodule built from source | `cc74a19` |
| Depth | RealSense runs with `align_depth.enable`; the detector reads the aligned depth | `41a8e35` |
| RViz | Own config `launch/human_ros4hri.rviz`, also used by the test launch | `cc74a19`, `ac5c5d9` |

## Decisions and why

**Upstream `hri_body_detect` instead of the fork.** The JOiiNT fork (3.1.4 plus one
commit) generates a random id for each track and then overwrites it with
`"default"` (`multibody_detector.py`, line 1195 of that version). Every person
therefore shared one id and the pipeline could follow a single person. Upstream
3.4.1 keeps the ids, up to five people (`MP_MAX_NUM_PEOPLE`). The module sources
were not edited: only the submodule URL/pointer changed.

**`hri_msgs` from source.** The image ships `hri_msgs` 2.1.0; the upstream detector
needs `Gesture.CLOSED_FIST` (2.3). The `components/hri_msgs` submodule is mounted
in the workspace and overrides the installed package.

**Own launch of the detector.** Upstream's `hri_body_detect.launch.py` needs PAL's
`launch_pal` and `diagnostic_aggregator`, which are not in the image, and the
fork's `hri_body_detect_with_args.launch.py` no longer exists. `arise_ergo.launch.py`
starts the node as a lifecycle node (configure then activate) with `use_depth: true`
and the RealSense topics.

**Own RViz config.** `human_description`'s `human.rviz` is written for the id
`default` (frames `*_default`, Fixed Frame `body_default`) and shows nothing with
real ids. `launch/human_ros4hri.rviz` uses the `hri_rviz` displays `Humans`,
`Skeletons3D` and `TF_HRI`, Fixed Frame `camera_link`. `Skeletons3D` needs the
URDF of each body, which only the real detector publishes, so with the test
fixture only `TF_HRI` shows something.

**Depth.** With `use_depth: true` the detector reads the depth at the colour-image
pixel of the hips (`rgb_to_xyz`); if that fails it falls back to a face-size
estimate, then to zero. The depth must therefore be registered on the colour
image, hence `align_depth.enable`. Without depth the position comes from the face
only. The joint angles use relative skeleton positions, so the camera distance
matters mostly for `speed`.

**Orion updates.** `orion_bridge` merges the latest scores into each `ergo_data`
sample (one Orion update, one notification and one CrateDB row per sample) and
updates with `POST /attrs` (append), because `PATCH` refuses attributes the entity
does not have yet.

**Subscription automation.** `inject.sh` never worked: empty subscriptions folder,
container names that do not resolve under `network_mode: host`, only `201`
accepted. A second problem showed up in the first real test: Orion-LD pauses a
subscription after three failed notifications (e.g. QuantumLeap restarting) and
never resumes it, so data silently stops reaching CrateDB. `inject.sh` now waits
for QuantumLeap (`/version`) and, on `409`, resumes a paused subscription.

## How it was checked

| Check | Result |
|---|---|
| Unit tests of `ergo_pkg_py` (`python3 -m pytest test` in the container) | 99 passed, 2 skipped |
| `inject.sh` on a throw-away Docker network: first start, restart (`409`), pause then restart, data reaches CrateDB | works |
| Same on the real stack after rebuilding QuantumLeap | subscription resumed, rows flowing |
| Scores in Orion/CrateDB with the synthetic fixture (`alice`, `bob`) | RULA 2–5, REBA up to 5, alert level 1 with description |
| Grafana: the six new panel queries through Grafana's query API | run and return values |
| Upstream detector on test videos (see below) | runs, several people, ids not stable |
| Full launch without camera (`use_camera:=false use_orion:=false`, a video republished on the RealSense topics) | detector active, `ergo_data` / `rula_score` per body id |

**Not checked yet**
- Anything with the real RealSense. The camera linked at USB 2.1 (480 Mbit/s) with
  every cable and port tried, and produced corrupted frames; it needs a USB 3 cable.
- The topic names `aligned_depth_to_color/image_raw` and `…/camera_info`: taken from
  the driver, exercised only with a video republished on them. The depth in those
  tests was a constant fake value, so depth accuracy is untested.
- How the new Grafana panels look in the browser (queries verified, rendering not).
- `ergo_advisor` with a real model (only the template fallback was run).

## Findings about the upstream detector (test clips, no camera)

- It follows several people at once, each under its own id, but **ids are not
  stable**: the tracker creates a new random id whenever it loses and finds a person
  again. On a 10 s clip of two people walking toward the camera, 14 distinct ids
  appeared in 40 s; two people were tracked together in about 13 % of the samples.
  A clip with three workers and a clip with a couple walking arm in arm gave one
  person most of the time.
- Ids can live for a fraction of a second (false or reborn tracks) and have no tf
  frame yet. `body_min_age` cut the bodies created from 21 to 10 in 40 s.
- The clips were short, looped and filmed with a moving camera, so these numbers say
  little about a fixed station with people standing in view.

## Known limitations and open items

1. **Entity model (decision pending).** Orion has one entity per tracker id
   (`urn:ngsi-ld:ErgoData:<body_id>`); ids change when the tracker loses someone, so
   the same person becomes several entities and ended tracks stay in Orion with
   their last values. Options discussed: (A) one entity per workstation, (B) keep
   one entity per id and add a `station` attribute, delete the entity from Orion
   when the id disappears, and let Grafana select by station and compare sessions,
   (C) both. The proposal is B with anonymous sessions: it answers whether a risk
   comes from the station (all sessions high) or from how a person works (only
   some). A persistent identity (face recognition, badge) is deliberately out of
   scope: it needs a data-protection and works-council decision.
2. **Neck angle `-4e-14`.** A real tracker sample gave `neck_angle` = −4.3e-14. RULA
   and REBA read any negative neck angle as extension, so rounding noise changes the
   score. The fixture was fixed for this; `ergo_lib` is not yet.
3. **Samples lost while QuantumLeap is down** are not recovered.
4. **Slides.** `documents/` is git-ignored; the deck there still describes the old
   structure (`jntlb_fwk_msgs`, global topics, "trunk 45° → RULA 6", id `default`).
5. **Posture regression test.** The six-posture check of the fixture is run by hand
   (README table), not by CI.
6. **Test with the real camera**, with the depth aligned and a few people in view.
