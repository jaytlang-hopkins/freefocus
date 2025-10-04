# File: main.py
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

import argparse
import esper

import hal.common
import ipc.clientserver

# MARK: Bootstrap

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="EyeMotion",
        description="A device-agnostic platform for oculomotor screening in resource-diverse settings",
        epilog="EyeMotion is free software; you are welcome to redistribute it. See `LICENSE.txt` for details."
    )
    
    parser.add_argument(
        "-d",
        "--device",
        choices=hal.common.HAL_DEVICES,
        required=True,
        help="peripheral to display stimuli and collect eye data"
    )
    
    args = parser.parse_args(); device = args.device
    esper.dispatch_event(ipc.clientserver.IPC_FORK_ENGINE, device)
    
    # TODO: add back the CLI here
    import time 
    while True: time.sleep(1)
    