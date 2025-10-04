# File: resources.py
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

import os
import tempfile

RESOURCES_DIR = "resources"

if not os.path.exists(RESOURCES_DIR): os.makedirs(RESOURCES_DIR)
if not os.path.isdir(RESOURCES_DIR):
    raise FileExistsError("A file named {RESOURCES_DIR} exists in the working directory. Please remove it")

TEMPORARY_DIR = tempfile.TemporaryDirectory(prefix=RESOURCES_DIR, delete=False).name
