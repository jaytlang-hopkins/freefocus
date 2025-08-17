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
# data acquisition, add it by name to one of these lists!

HAL_DISPLAYS = {"fove", "screen"}
HAL_RECORDERS = {"fove"}

# Sanity checking beyond this point...

hal_directory = os.path.dirname(os.path.realpath(__file__))
available_files = glob.glob(f"{hal_directory}/[a-z]*.py")
available_modules = [os.path.basename(os.path.splitext(f)[0]) for f in available_files]

for support_list in HAL_DISPLAYS, HAL_RECORDERS:
    for module in support_list: assert module in available_modules
