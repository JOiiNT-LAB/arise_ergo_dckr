# Branch notes — `feature/ros4hri-ergo-advisor`

Status: 2026-10-09. This file records what changed on this branch compared with
`main_integration`, why, how it was checked and the known limitations. The README
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
| One person | `single_body` (default): `body_selector` follows the body nearest to the camera, the nodes read `/humans/bodies/selected`, Orion gets the single entity `urn:ngsi-ld:ErgoData:operator` | not committed yet |
| Start / stop | `start.sh` starts the stack and the pipeline, `stop.sh` stops both | not committed yet |
| Measured posture | Trunk, neck and arms are measured by `ergodata_calculator` from `skeleton2d` and the aligned depth, relative to a neutral posture reference (`launch/posture_reference.json`) | not committed yet |
| RULA | Neck rounding fixed; arm abduction and muscle use (static posture) scored; `ergo_alert` critical threshold 6 in the launch | not committed yet |

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

**One person at a time (`single_body`).** Because the tracker ids change, one
operator in front of the camera left a trail of Orion entities and CrateDB
`entity_id`s. `body_selector` publishes on `/humans/bodies/selected` at most one id,
the body nearest to the camera, kept while it stays tracked (a new choice after
`switch_timeout`, 2 s); the ergonomic nodes read it (`tracked_topic`) and
`orion_bridge` writes to the single entity `operator` (`entity_name`). With
`single_body:=false` every id gets its own topics and entity, as before.

**Trunk, neck and arms measured in `ergo_pkg_py`.** The first test with the camera
showed trunk and neck stuck at "upright" whatever the person did, and RULA stuck at 6.
The detector fits a human URDF, but `jointstate.py` of `hri_body_detect` 3.4.1 always
publishes the `waist` and head joints at 0, and the `body_<id>` frame only turns
about the vertical: the URDF trunk and head are always upright. Its arms come from
inverse kinematics on the wrist only, for a fixed 1.65 m body with rigid shoulders;
with the real camera, hanging arms read 15–30° raised and one arm stayed stuck at a
joint limit. A patch of the detector was tried and reverted: the PAL / ros4hri
packages (`hri_body_detect`, `human_description`, …) are not edited. Instead,
`ergodata_calculator` reads `/humans/bodies/<id>/skeleton2d` (the 2D keypoints the
detector already publishes) and the aligned depth:

- trunk: pelvis and sternum (2D midpoints of the hips and of the shoulders)
  back-projected with the depth, about 0.5 m apart, so a few cm of depth noise matter
  little;
- neck: from the 2D face keypoints, more precise than the depth over the few cm of a
  neck. Head pitch from how far the nose is below the line of the ears (corrected for
  the line of sight), side bending from the slope of that line against the shoulders;
  both relative to the trunk. A first version measured the neck with the depth too and
  gave ±15° of noise and impossible values;
- arms: shoulder, elbow and wrist back-projected with the depth, relative to the
  measured trunk. Thin limbs take the nearest surface around the keypoint; a depth
  that is not plausible takes the sternum depth; a hand covering its elbow (forearm
  toward the camera) gets the elbow depth that fits the arm lengths; the depth step
  between joints is bounded by the arm lengths (ratios of the trunk length).

The angles keep the `ErgoData` conventions, so RULA/REBA are unchanged. They are
smoothed (One Euro filter); a value missing for less than 2 s keeps the last one;
impossible values (trunk outside −45…120°, neck outside −70…90° relative to the trunk)
are dropped. Without a measure the URDF values from tf are used, as before.

**Neutral posture reference.** The measure has fixed offsets: the camera is not level,
the nose is in front of the ears, the depth is that of the body surface (standing
upright the raw neck reads about 30°). They are measured once on a person standing
still, upright and facing the camera for 2 s, and subtracted from every posture. The
reference is per installation, not per person: `launch/posture_reference.json`,
loaded at start. If the file is missing, the first person standing still sets it and
it is saved; after moving the camera, delete it or call
`/ergodata_calculator/recalibrate_posture`. A per-person calibration was tried first
and dropped: it made the measure depend on how each person behaves when they arrive,
and nothing was measured until then.

**RULA could not reach 7.** Wrist, shoulder raise, load and muscle use were fixed to
neutral and arm abduction was switched off in `rula_lib`, so the arm score never
exceeded 4 and RULA never exceeded 6 (checked over all angle combinations): the
`critical` alert could never fire. Abduction is scored again, with a corrected
convention (the old one counted the left arm as abducted when it pointed at the other
shoulder), and muscle use is +1 for a posture held for more than 1 minute within 15°
(`StaticPosture`). Repeated actions, the other muscle-use case, are not detected.
Until these factors are validated, `arise_ergo.launch.py` sets `ergo_alert`'s
`critical_threshold` to 6 (the node default stays 7).

**Neck rounding.** A neck angle of −4.3e-14 (an upright head) was scored as extension
(RULA neck 4, +1 more for a side bending read with the wrong convention), which kept
RULA at 6 and the alert on. `rula_lib`/`reba_lib` now treat −5…0° as neutral and both
read `neck_bending_angle` as 90 = upright.

**Camera reconnected while the container runs.** The container sees only the USB
devices present when it started: after the D435 re-enumerated, the driver logged
"No RealSense devices were found!" in a loop. `./stop.sh && ./start.sh` recreates
the device nodes.

## How it was checked

| Check | Result |
|---|---|
| Unit tests of `ergo_pkg_py` (`python3 -m pytest test` in the container) | 161 passed (posture measure on synthetic depth images, arm angles with arms ±15 % of the nominal length, reference file, RULA abduction and muscle use) |
| `inject.sh` on a throw-away Docker network: first start, restart (`409`), pause then restart, data reaches CrateDB | works |
| Same on the real stack after rebuilding QuantumLeap | subscription resumed, rows flowing |
| Scores in Orion/CrateDB with the synthetic fixture (`alice`, `bob`) | RULA 2–5, REBA up to 5, alert level 1 with description |
| Grafana: the six new panel queries through Grafana's query API | run and return values |
| Upstream detector on test videos (see below) | runs, several people, ids not stable |
| Full launch without camera (`use_camera:=false use_orion:=false`, a video republished on the RealSense topics) | detector active, `ergo_data` / `rula_score` per body id |
| Real D435 at USB 3 (5000M), full stack | colour and aligned depth at ~27 Hz, detector active, `/humans/bodies/selected` with one id, data in Orion and CrateDB |
| Live, standing then bending forward (read back from CrateDB) | trunk 0–8° upright, 47–75° bent; RULA 2–3 upright, up to 7 with arms raised and trunk or neck bent |
| Live, posture reference | measured on a person standing still (`[1.5, -0.5, 32.2, 0.8]`), loaded from the file at the next start; no reference file: created and reloaded (synthetic data) |
| Test launch (fixture) after the changes | the six postures give the README table |

**Not checked yet**
- The arm angles posture by posture with the real camera: they were checked on
  synthetic images and live only with free movements, without a timed protocol.
- Side bending of the trunk and of the neck with the real camera (one forward bend
  read 40–50° of trunk side bending, unexplained).
- Several people with the new measure (all live tests had one person in view).
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

## Findings with the real camera

- The hips must be in the image: when they are below its edge, MediaPipe guesses them
  and there is no depth to read, so the trunk is not measured. The first setup cut
  them off; the person had to step back.
- The tracker changed the id of the one person in view 4 times in 100 s, mostly while
  bending; each change leaves a gap of `body_min_age` seconds.
- Standing still after the reference, the neck varies by about ±7°, the trunk by a few
  degrees.
- Bending deeply toward the camera, the face looks at the floor and the neck measure
  is not meaningful; it is now dropped.

## Known limitations

- **Ids are tracker ids, not persons.** Orion has one entity per body id
  (`urn:ngsi-ld:ErgoData:<body_id>`). The tracker creates a new id whenever it loses
  and finds a person again, so one person can become several entities, and the
  entity of an ended track stays in Orion with its last values.
- **The posture measure assumes a person roughly facing the camera**, with hips,
  shoulders and face in view. Turned away, part of the flexion is read as side
  bending; with the face hidden the neck falls back to the URDF value after 2 s.
- **The posture reference belongs to the camera mounting**: move the camera, redo it.
  It is taken on one person; others can differ by a few degrees on the neck.
- **Trunk twist, shoulder raise and wrists are not measured** (trunk twist and
  shoulders still come from the URDF, wrists are 0); external load, coupling, REBA
  activity and repeated actions are neutral. `critical` at RULA 6 is a provisional
  choice until the new factors are validated.
- **A missing measure is not flagged**: before the reference exists or after 2 s
  without hips in view, trunk and neck take the URDF values (upright), which look like
  a good posture in the data.
- **Samples sent while QuantumLeap is down are not recovered.** The subscription is
  resumed afterwards, nothing is replayed.
- **`Skeletons3D` shows nothing with the synthetic fixture**, which publishes no body
  URDF; only `TF_HRI` shows its frames.
- **The six-posture check of the fixture is run by hand** (README table), not by CI.
- The RULA/REBA tables, the margins added to their bands and the new scoring of
  abduction and muscle use have not been checked by an ergonomics expert.
