# File: hal/screen.py
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

import esper
import moderngl
import moderngl_window
import sys

from . import common

WINDOW = moderngl_window.create_window_from_settings()
WINDOW.title = "EyeMotion"
moderngl_window.activate_context(ctx=WINDOW.ctx)

def push_frame(texture_id):
    if WINDOW.is_closing: sys.exit(0)
    else: WINDOW.swap_buffers(); WINDOW.clear()

esper.set_handler(common.HAL_PUSH_FRAME_AND_VSYNC, push_frame)
esper.dispatch_event(common.HAL_RENDER_CONTEXT_READY, WINDOW.buffer_size, WINDOW.ctx)

# Fun fact: I spent approximately three weeks on this piece of code