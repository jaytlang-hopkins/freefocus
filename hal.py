# File: hal.py
# Copyright 2025 Jay Lang
# 
# This file is part of the EyeMotion project. EyeMotion is free software: you
# can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# EyeMotion is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with
# EyeMotion. If not, see <https://www.gnu.org/licenses/>. 

import ctypes
import datetime
import os
import sys
import inspect

from dataclasses import dataclass

import esper
import requests

import resources

# MARK: Helpers
# This is particularly useful for this module...
def remove_component_if_present(entity, component_type):
    if esper.has_component(entity, component_type):
        esper.remove_component(entity, component_type)

# MARK: Events

HAL_DATA_PUBLISHED = "hal_data_published"
HAL_PUSH_FRAME_AND_VSYNC = "hal_push_frame"

# MARK: FFI
FOVE_SDK_URL = "https://github.com/FoveHMD/FoveCppSample/raw/refs/heads/master/FOVE%20SDK%201.3.1/FoveClient.dll"
FOVE_DLL_NAME = "FoveClient.dll"

class FoveSDKException(Exception):
    def __init__(self, method, error_code):
        self.method = method
        self.error_code = error_code

        message = f"{method} returned error code {error_code}. Please consult the FoveAPI.h error enums for more information"
        super().__init__(message)

class FoveSDKHandle:
    def __init__(self):
        dll_path = os.path.join(resources.RESOURCES_DIR, FOVE_DLL_NAME)
        if not os.path.isfile(dll_path):
            response = requests.get(FOVE_SDK_URL, stream=True)
    
            with open(dll_path, 'wb') as fp:
                for chunk in response.iter_content(chunk_size=16384):
                    fp.write(chunk)
    
        self._sdk_handle = ctypes.CDLL(dll_path)
    
    def call(self, method, *args):
        f = getattr(self._sdk_handle, method)
        err = f(*args)

        if err != 0: raise FoveSDKException(method, err)

# Is a global here an antipattern? I don't think so, especially 
# given that it's accessed only through this sdk() ensure-style function..
_shared_sdk_handle = None
def sdk():
    global _shared_sdk_handle

    if _shared_sdk_handle is None:
        _shared_sdk_handle = FoveSDKHandle()
    return _shared_sdk_handle

FOVE_ERROR_API_NOTREGISTERED = 104
FOVE_ERROR_DATA_NOUPDATE = 1003

FOVE_ERROR_DATA_UNRELIABLE = 1006
FOVE_ERROR_DATA_LOWACCURACY = 1007
FOVE_POOR_DATA_ERRORS = (FOVE_ERROR_DATA_UNRELIABLE, FOVE_ERROR_DATA_LOWACCURACY)

FOVE_CLIENTCAPABILITIES_ORIENTATIONTRACKING = 1 << 0
FOVE_CLIENTCAPABILITIES_POSITIONTRACKING = 1 << 1
FOVE_CLIENTCAPABILITIES_EYETRACKING = 1 << 3
FOVE_CLIENTCAPABILITIES_GAZEDEPTH = 1 << 4
FOVE_CLIENTCAPABILITIES_USERPRESENCE = 1 << 5
FOVE_CLIENTCAPABILITIES_USERATTENTIONSHIFT = 1 << 6
FOVE_CLIENTCAPABILITIES_EYESIMAGE = 1 << 11

FOVE_RELEVANT_CAPABILITIES = (
    FOVE_CLIENTCAPABILITIES_ORIENTATIONTRACKING |
    FOVE_CLIENTCAPABILITIES_POSITIONTRACKING |
    FOVE_CLIENTCAPABILITIES_EYETRACKING |
    FOVE_CLIENTCAPABILITIES_GAZEDEPTH |
    FOVE_CLIENTCAPABILITIES_USERPRESENCE |
    FOVE_CLIENTCAPABILITIES_USERATTENTIONSHIFT |
    FOVE_CLIENTCAPABILITIES_EYESIMAGE
)

FOVE_ALPHAMODE_SAMPLE = 2
FOVE_COMPOSITORLAYERTYPE_BASE = 0x0000
FOVE_GRAPHICSAPI_OPENGL = 1

FOVE_EYE_LEFT = 0
FOVE_EYE_RIGHT = 1

def eye_enum_values_to_names():
    return {
        FOVE_EYE_LEFT: "left",
        FOVE_EYE_RIGHT: "right",
    }

FOVE_EYESTATE_OPEN = 1
FOVE_EYESTATE_CLOSED = 2

# MARK: C Structures
class FoveLicenseInfo(ctypes.Structure):
    _fields_ = [
        ("uuid", ctypes.c_uint8 * 16),
        ("expirationYear", ctypes.c_int),
        ("expirationMonth", ctypes.c_int),
        ("expirationDay", ctypes.c_int),
        ("licenseType", ctypes.c_char * 256),
        ("licensee", ctypes.c_char * 256),
    ]

class FoveFrameTimestamp(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_uint64),
        ("timestamp", ctypes.c_uint64)
    ]

class FoveVec2(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float)
    ]

class FoveVec3(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("z", ctypes.c_float)
    ]

class FoveBuffer(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.c_void_p),
        ("length", ctypes.c_size_t)
    ]

class FoveBitmap(ctypes.Structure):
    _fields_ = [
        ("timestamp", ctypes.c_uint64),
        ("buffer", FoveBuffer),
    ]

# I disclaim responsibility for any and all clunky SDK design by the FOVE team
# Sorry guys, i just don't like when we try to force OOP on people

class FoveCompositorLayerCreateInfo(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("disableTimeWarp", ctypes.c_bool),
        ("alphaMode", ctypes.c_int),
        ("disableFading", ctypes.c_bool),
        ("disableDistortion", ctypes.c_bool)
    ]

class FoveCompositorLayer(ctypes.Structure):
    _fields_ = [
        ("layerId", ctypes.c_int),
        ("idealResolutionPerEye", ctypes.c_int * 2)
    ]

class FoveTextureBounds(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_float),
        ("top", ctypes.c_float),
        ("right", ctypes.c_float),
        ("bottom", ctypes.c_float),
    ]

class FoveCompositorTexture(ctypes.Structure):
    _fields_ = [
        ("graphicsAPI", ctypes.c_int)
    ]

class FoveGLTexture(ctypes.Structure):
    _fields_ = [
        ("textureId", ctypes.c_uint32),
        ("parent", FoveCompositorTexture),
        ("context", ctypes.c_void_p)
    ]

class FoveCompositorLayerEyeSubmitInfo(ctypes.Structure):
    _fields_ = [
        ("texInfo", ctypes.POINTER(FoveGLTexture)),
        ("bounds", FoveTextureBounds)
    ]

class FovePose(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_uint64),
        ("timestamp", ctypes.c_uint64),
        ("orientation", ctypes.c_float * 4),
        ("angularVelocity", FoveVec3),
        ("angularAcceleration", FoveVec3),
        ("position", FoveVec3),
        ("standingPosition", FoveVec3),
        ("velocity", FoveVec3),
        ("acceleration", FoveVec3),
    ]

class FoveCompositorLayerSubmitInfo(ctypes.Structure):
    _fields_ = [
        ("layerId", ctypes.c_int),
        ("pose", FovePose),
        ("left", FoveCompositorLayerEyeSubmitInfo),
        ("right", FoveCompositorLayerEyeSubmitInfo)
    ]

# MARK: Headset Init
class HeadsetHandle(ctypes.c_void_p): pass

@dataclass
class RenderTarget:
    compositor: ctypes.c_void_p
    layer: FoveCompositorLayer

def ensure_headset_license(handle):
    array_size = ctypes.c_int(5)
    license_array = (FoveLicenseInfo * array_size.value)()

    sdk().call("fove_Headset_queryLicenses", handle, license_array, ctypes.byref(array_size)) 

    for i in range(array_size.value):
        this_license = license_array[i]
        expiration_date = datetime.date(
            this_license.expirationYear,
            this_license.expirationMonth,
            this_license.expirationDay
        )

        if datetime.date.today() < expiration_date: return

    raise IndexError("No active FOVE license found! You should get a new one")

def create_headset():
    handle = HeadsetHandle()

    sdk().call("fove_createHeadset", 0, ctypes.byref(handle))
    sdk().call("fove_Headset_checkSoftwareVersions", handle)
    sdk().call("fove_Headset_registerCapabilities", handle, FOVE_RELEVANT_CAPABILITIES)
    ensure_headset_license(handle)

    return handle

def create_render_target(handle):
    # 1. Create the compositor
    rt = RenderTarget(ctypes.c_void_p(), FoveCompositorLayer())
    sdk().call("fove_Headset_createCompositor", handle, ctypes.byref(rt.compositor))

    compositor_ready = ctypes.c_bool(False)
    while not compositor_ready:
        sdk().call("fove_Compositor_isReady", rt.compositor, ctypes.byref(compositor_ready))
    
    # 2. Create our layer
    layer_params = FoveCompositorLayerCreateInfo(
        type=FOVE_COMPOSITORLAYERTYPE_BASE,
        alphaMode=FOVE_ALPHAMODE_SAMPLE
    )

    sdk().call("fove_Compositor_createLayer", rt.compositor, ctypes.byref(layer_params), ctypes.byref(rt.layer))
    return rt

handle = create_headset()
render_target = create_render_target(handle)
esper.create_entity(handle, render_target)

# MARK: Connectivity

class TetheredConnection: pass

class Connectivity(esper.Processor):
    def _is_connected(self, handle):
        try:
            status = ctypes.c_bool()
            sdk().call("fove_Headset_isHardwareConnected", handle, ctypes.byref(status))
            return status.value
        except FoveSDKException as e:
            if e.error_code == FOVE_ERROR_DATA_NOUPDATE: return False
            else: raise
        
    def process(self):
        for ent, handle in esper.get_component(HeadsetHandle):
            if self._is_connected(handle): esper.add_component(ent, TetheredConnection())
            else: remove_component_if_present(ent, TetheredConnection)

# MARK: Data presence

class UpdateTime(int): pass
class Datum(dict): pass

class Availability(esper.Processor):
    def _most_recent_update_time(self, handle):
        try:
            frameinfo = FoveFrameTimestamp()
            sdk().call("fove_Headset_fetchEyeTrackingData", handle, ctypes.byref(frameinfo))
        except FoveSDKException as e:
            if e.error_code == FOVE_ERROR_API_NOTREGISTERED: pass
            elif e.error_code == FOVE_ERROR_DATA_NOUPDATE: pass
            else: raise

        return UpdateTime(frameinfo.timestamp)
    
    def _user_present(self, handle):
        try:
            sdk_output = ctypes.c_bool()
            sdk().call("fove_Headset_isUserPresent", handle, ctypes.byref(sdk_output))
        except FoveSDKException as e:
            if e.error_code == FOVE_ERROR_DATA_NOUPDATE: pass
            else: raise

        return sdk_output.value

    def process(self):
        for ent, (handle, _) in esper.get_components(HeadsetHandle, TetheredConnection):
            # 1. Poll the headset
            last_update_time = self._most_recent_update_time(handle)
            new_data_available = self._user_present(handle)

            # 2. New data is available if the user is present AND our timestamp has changed
            if last_recorded_update_time := esper.try_component(ent, UpdateTime):
                new_data_available &= last_update_time != last_recorded_update_time
            esper.add_component(ent, last_update_time)
            
            # 3. Commit!
            if new_data_available:
                esper.add_component(ent, Datum({"timestamp": last_update_time}))
            else: remove_component_if_present(ent, Datum)

# MARK: Data intake
# Want more data? Define a function here that starts with `intake_`.

class PoorDataSuppression:
    def __enter__(self): pass
    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type == FoveSDKException:
            if exc_val.error_code in FOVE_POOR_DATA_ERRORS: return True

def intake_gaze_vectors(handle, datum):
    result = {}

    for fove_eye, eye_name in eye_enum_values_to_names().items():
        data_is_reliable = False
        with PoorDataSuppression():
            c_vector = FoveVec3()
            sdk().call("fove_Headset_getGazeVector", handle, fove_eye, ctypes.byref(c_vector))
            data_is_reliable = True

        for dimension in "x", "y", "z":
            datum[f"raw_gaze_{eye_name}_eye_{dimension}"] = getattr(c_vector, dimension)
            datum[f"{eye_name}_eye_data_is_reliable"] = data_is_reliable

def intake_eyes_are_open(handle, datum):
    for fove_eye, eye_name in eye_enum_values_to_names().items():
        state_out = ctypes.c_int() 
        sdk().call("fove_Headset_getEyeState", handle, fove_eye, ctypes.byref(state_out))

        if state_out.value == FOVE_EYESTATE_OPEN: datum_value = True
        elif state_out.value == FOVE_EYESTATE_CLOSED: datum_value = False
        else: datum_value = None

        datum[f"{eye_name}_eye_open"] = datum_value

def intake_hmd_needs_adjustment(handle, datum):
    adjustment_result = ctypes.c_bool()
    sdk().call("fove_Headset_isHmdAdjustmentGuiVisible", handle, ctypes.byref(adjustment_result))

    datum["hmd_needs_adjustment"] = adjustment_result.value

def intake_saccade_in_progress(handle, datum):
    saccade_result = ctypes.c_bool()
    with PoorDataSuppression():
        sdk().call("fove_Headset_isUserShiftingAttention", handle, ctypes.byref(saccade_result))

    datum["saccade_in_progress"] = saccade_result.value

def intake_eye_image(handle, datum):
    image = FoveBitmap()
    sdk().call("fove_Headset_fetchEyesImage", handle, 0)
    sdk().call("fove_Headset_getEyesImage", handle, ctypes.byref(image))

    datum["image_bytes"] = bytearray(ctypes.string_at(image.buffer.data, image.buffer.length))

# MARK: Data publication

INTAKE_FUNCTIONS = []
for name, obj in inspect.getmembers(sys.modules[__name__]):
    if not inspect.isfunction(obj): continue
    if obj.__module__ != __name__: continue
    if "intake_" not in name: continue

    INTAKE_FUNCTIONS.append(obj)

class Publication(esper.Processor):
    def process(self):
        for ent, (handle, datum) in esper.get_components(HeadsetHandle, Datum):
            # 1. Data is newly available! Record it
            for f in INTAKE_FUNCTIONS: f(handle, datum)

            # 2. Event the data out!
            esper.dispatch_event(HAL_DATA_PUBLISHED, datum)

            # 3. Clean up locally
            esper.remove_component(ent, Datum)

# MARK: Rendering

def push_frame(texture_id):
    for _, rt in esper.get_component(RenderTarget):
        submission_pose = FovePose()

        # NOTE: This is where blocking comes from
        sdk().call("fove_Compositor_waitForRenderPose", rt.compositor, ctypes.byref(submission_pose))

        texture = FoveGLTexture(
            parent=FoveCompositorTexture(FOVE_GRAPHICSAPI_OPENGL),
            textureId=texture_id,
        )

        submission = FoveCompositorLayerSubmitInfo(layerId=rt.layer.layerId, pose=submission_pose)
        for eye in "left", "right":
            per_eye_submission = FoveCompositorLayerEyeSubmitInfo(
                texInfo=ctypes.pointer(texture),
                bounds=FoveTextureBounds(top=0, bottom=1, left=0, right=1)
            )
            setattr(submission, eye, per_eye_submission)

        sdk().call("fove_Compositor_submit", rt.compositor, ctypes.byref(submission), 1)

esper.set_handler(HAL_PUSH_FRAME_AND_VSYNC, push_frame)

# MARK: Main

processors = [
    Connectivity,
    Availability,
    Publication
]

for processor in processors:
    esper.add_processor(processor())