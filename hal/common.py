# File: hal/common.py
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

import glob
import os

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

