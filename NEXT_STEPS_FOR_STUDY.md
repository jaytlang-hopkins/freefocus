# Steps to prepare for our study :alembic:

## Additional adapters :heavy_plus_sign:
You know this one. We need to port recording capability to at _least_:
* Webcam (with a whole lot of CV code in there or some 3P library)
* Microsoft HoloLens II
* [OPTIONAL] Tobii Pro Spectrum / whatever we've got in the clinic.

The case for the Tobii isn't as strong, because it's _super_ expensive so including
it might undermine our equity arguments.

As a reminder, we don't need to implement eye image acquisition. The paper just
requires monocular (right eye, let's say) gaze x/y per-frame alongside a relative
analysis (see below for the stats discussion, but TL;DR it's time independent
spectral methods).

**Technical recommendations**:
* :white_check_mark: *Let's make a `hal` _directory_ with its own `__init__.py` and then pick what
  device the user should input based on a command-line `--device` flag.*
* :white_check_mark: *Let's isolate out common code to open a full-screen window and shove a texture
  into it, since all two-three new ports will need that capability. This should
  be straightforward, especially if we drop `moderngl` and go full `pyopengl`.*

## Recorder :camera_flash:
We're going to be able to dump a lot of post-processing logic that we don't need
(namely video). I'm thinking, however, that we should add new stuff in its place:
namely something that listens for `UI_FRAME_READY` and dumps the result to a file
in `resources.TEMPORARY_DIR`. This allows us to assert frame-perfection as required
by my present KPIs.

Alongside this could go basic cross-platform checks for resource utilization via a
3P library.

However, *most important* here is on-device data analysis. We need to do a `scipy.welch`
in here to strip out beat frequency, and then apply trigonometry + `scipy.find_peaks`
to get beat amplitude based on known parameters of the screen + study room. While
we're allowed to dump raw gaze data into `resources`, that's technically PII (yes, PII,
_not_ just PHI) so we **cannot** send it anywhere.

## Stimuli :necktie:

Messing with the UI state machine to add a five-point calibration routine seems smart.
This would be _very_ simple to implement using existing primitives -- just use
`TargetPoint` five times. This way we can learn the bounds of the display along with
where the center is without resorting to device-specific measures, and that also helps
with our trigonometric analysis in `recorder.py`.

## Commands :lock:
In addition to some code to create or input a 64-bit pseudo-random key
(needed for study identifier generation), which is obviously trivial, we need
to `import requests` in here and upload derived/de-identified participant data
to a remote cloud-based endpoint. Given that this runs within Hopkins IT infrastructure,
a SAFE-based instance can then poll it for new data over and over again, and all
requirements specified in the paper are met without any P2P hole punching / the SSH forwarding
I originally envisioned.

*(We should also blow away the storage of this HTTP server with some timeout e.g. 5 minutes
to make sure PHI (not PII at this point) doesn't accumulate where we don't want it.
Bridging that data through trusted Hopkins infrastructure is fine, losing track of it isn't.)*

The hardest part of this is not `import requests`, but:
* Doing all the diplomacy to get at least three certificates under the Hopkins CA for mTLS
* Setting up an instance that abides by all the requirements for PHI stuff; if you can call
  linked study data PHI...
* Writing the requisite tiny little flask server or similar for the server / intermediary side

...and I will happily write these emails when I have spare cycles.
