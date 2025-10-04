# File: hal/screen.py
# Copyright 2025 Jay Lang
#
# This file is part of the FreeFocus project. FreeFocus is free software: you
# can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# FreeFocus is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# FreeFocus. If not, see <https://www.gnu.org/licenses/>.

import atexit
import io
import os
import sys
import time
import threading
from dataclasses import dataclass

import cv2
import esper
import mediapipe as mp
import moderngl_window
import requests
from PIL import Image

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

import resources
from . import common

# MARK: nEuRAL nEtWoRK

MP_LANDMARKER_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
MP_LANDMARKER_TASK = "face_landmarker.task"

@dataclass
class ModelOutput:
    timestamp_ms: int
    input_image: mp.Image
    result: object

class Model:
    def _download_model(self):
        model_path = os.path.join(resources.RESOURCES_DIR, MP_LANDMARKER_TASK)
        if os.path.isfile(model_path):
            return model_path

        response = requests.get(MP_LANDMARKER_URL, stream=True)
        with open(model_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=16384):
                handle.write(chunk)

        return model_path
    
    def __init__(self):
        creation_options = mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=self._download_model()),
            running_mode=mp_vision.RunningMode.LIVE_STREAM,
            result_callback=lambda result, image, ts: esper.create_entity(ModelOutput(ts, image, result)),
            output_face_blendshapes=True,
            num_faces=1,
        )

        self._model = mp_vision.FaceLandmarker.create_from_options(creation_options)

    def detect(self, timestamp_ms, frame):
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        self._model.detect_async(mp_image, timestamp_ms)

    def close(self): self._model.close()

MODEL = Model()
atexit.register(MODEL.close)

# MARK: Model input
# Why is OpenCV's read() blocking?!?!? ):

NS_PER_MS = 1000000
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

class ReadyForInput: pass
class CaptureThread(threading.Thread): pass

@dataclass
class Camera:
    c: cv2.VideoCapture
    current_frame: object
    mutex: threading.Lock

def capture_thread(camera):
    while True:
        success, frame = camera.c.read()
        if not success: continue

        with camera.mutex:
            if camera.current_frame is None:
                camera.current_frame = frame

def ensure_camera():
    camera = Camera(
        c=cv2.VideoCapture(0),
        current_frame=None,
        mutex=threading.Lock(),
    )

    camera.c.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    camera.c.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    assert camera.c.isOpened(), "I don't have permission to access your webcam. Try again?"

    background_thread = threading.Thread(
        target=capture_thread,
        args=(camera, ),
        name="FreeFocus Webcam Capture Thread",
        daemon=True
    )
    background_thread.start()

    atexit.register(camera.c.release)
    esper.create_entity(camera, ReadyForInput())

ensure_camera()

class Input(esper.Processor):
    def process(self):
        for ent, (camera, _) in esper.get_components(Camera, ReadyForInput):
            input_frame = None
            with camera.mutex:
                if camera.current_frame is not None:
                    input_frame = camera.current_frame.copy()
                    camera.current_frame = None

            if input_frame is not None:
                cv2.cvtColor(input_frame, cv2.COLOR_BGR2RGB, dst=input_frame)
                MODEL.detect(time.time_ns() // NS_PER_MS, input_frame)
                
                esper.remove_component(ent, ReadyForInput)

# MARK: Model output

IRIS_LEFT_CENTER_INDEX = 468
IRIS_RIGHT_CENTER_INDEX = 473

@common.intake(common.Field.PER_EYE_RAW_GAZE, common.Field.PER_EYE_DATA_IS_RELIABLE)
def intake_landmarks(model_output):
    try:
        raw_landmarks = model_output.result.face_landmarks[0]
        l, r = raw_landmarks[IRIS_LEFT_CENTER_INDEX], raw_landmarks[IRIS_RIGHT_CENTER_INDEX]
        return ((l.x, l.y), (r.x, r.y)), [True] * 2
    except IndexError:
        return [[0] * 2] * 2, [False] * 2

LEFT_EYE_CLOSED_CATEGORY = "eyeBlinkLeft"
RIGHT_EYE_CLOSED_CATEGORY = "eyeBlinkRight"
EYE_CLOSED_SCORE_THRESHOLD = 0.7

@common.intake(common.Field.PER_EYE_IS_OPEN)
def intake_blendshapes(model_output):
    output = [False] * 2
    try:
        for blendshape in model_output.result.face_blendshapes[0]:
            if blendshape.category_name == LEFT_EYE_CLOSED_CATEGORY:
                output[0] = blendshape.score < EYE_CLOSED_SCORE_THRESHOLD
            elif blendshape.category_name == RIGHT_EYE_CLOSED_CATEGORY:
                output[1] = blendshape.score < EYE_CLOSED_SCORE_THRESHOLD
    except IndexError: pass

    return output

@common.intake(supplies_image=True)
def passthrough_image(model_output):
    array_view = model_output.input_image.numpy_view()
    image = Image.fromarray(array_view)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80, optimize=True)
    return bytearray(buffer.getvalue())

class Output(esper.Processor):
    def process(self):
        for ent, callback_data in esper.get_component(ModelOutput):
            output = common.run_intake(callback_data, callback_data.timestamp_ms)
            esper.dispatch_event(common.HAL_DATA_PUBLISHED, output)

            esper.delete_entity(ent)
            for ent, _ in esper.get_component(Camera):
                esper.add_component(ent, ReadyForInput())

for p in Input, Output:
    esper.add_processor(p())

# MARK: Rendering

WINDOW = moderngl_window.create_window_from_settings()
WINDOW.title = "FreeFocus"
moderngl_window.activate_context(ctx=WINDOW.ctx)
atexit.register(WINDOW.close)

def push_frame(texture_id):
    if WINDOW.is_closing: sys.exit(0)
    else:
        WINDOW.swap_buffers()
        WINDOW.clear()

esper.set_handler(common.HAL_PUSH_FRAME_AND_VSYNC, push_frame)
esper.dispatch_event(common.HAL_RENDER_CONTEXT_READY, WINDOW.buffer_size, WINDOW.ctx)
