# File: hal/common.py
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

import enum
import glob
import os

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

# MARK: Events

HAL_DATA_PUBLISHED = "hal_data_published"
HAL_PUSH_FRAME_AND_VSYNC = "hal_push_frame"
HAL_RENDER_CONTEXT_READY = "hal_render_context_ready"

# MARK: Supported Hardware
# If you want to target a new device for stimulus display and/or
# data acquisition, add an appropriately named *.py file to this directory!

hal_directory = os.path.dirname(os.path.realpath(__file__))
available_files = glob.glob(f"{hal_directory}/[a-z]*.py")

HAL_DEVICES = []
for f in available_files:
    filename = os.path.basename(f)
    if filename != os.path.basename(__file__):
        HAL_DEVICES.append(os.path.splitext(filename)[0])

# MARK: Data Fields

class Field(enum.StrEnum):
    HMD_NEEDS_ADJUSTMENT = enum.auto()
    SACCADE_IN_PROGRESS = enum.auto()
    PER_EYE_DATA_IS_RELIABLE = enum.auto()
    PER_EYE_IS_OPEN = enum.auto()
    PER_EYE_RAW_GAZE = enum.auto()

# MARK: Data Intake

@dataclass
class IntakeDescriptor:
    fn: Callable[[object], object]
    fields: Tuple[str]
    supplies_image: bool

INTAKE_REGISTRY = []

def intake(*fields, supplies_image=False):
    def wrap(fn):
        assert len(fields) > 0 or supplies_image
        if supplies_image:
            for registered_function in INTAKE_REGISTRY:
                assert not registered_function.supplies_image

        INTAKE_REGISTRY.append(IntakeDescriptor(fn, fields, supplies_image))
        return fn
    return wrap

@dataclass
class DataPacket:
    timestamp: int
    payload: Dict[str, object]
    image: Optional[bytearray]

def run_intake(context, timestamp):
    packet = DataPacket(timestamp=timestamp, payload={}, image=None)

    for desc in INTAKE_REGISTRY:
        result = desc.fn(context)
        if not isinstance(result, tuple): result = (result, )

        if desc.supplies_image:
            assert len(result) == len(desc.fields) + 1
            packet.image = result[-1]
        else: assert len(result) == len(desc.fields)

        for field, value in zip(desc.fields, result):
            packet.payload[field] = value
    
    return packet

