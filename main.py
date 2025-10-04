# File: main.py
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

import argparse
import esper
import time 
import sys

import hal.common
import ipc.clientserver

from yaspin import yaspin

# MARK: Clinician interface

def prompt_user(last_command_successful, associated_message=""):
    prompt = "[*]" if last_command_successful else "[!]"
    if associated_message != "": print(associated_message)

    new_input = ""
    while new_input == "":
        print(f"{prompt} > ", end="", flush=True)
        try: new_input = input().strip()
        except EOFError: sys.exit(0)
    
    if new_input != "":
        esper.dispatch_event(ipc.clientserver.IPC_CLIENT_FORWARD_INPUT, new_input)

# MARK: Bootstrap

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="FreeFocus",
        description="A device-agnostic platform for oculomotor screening in resource-diverse settings",
        epilog="FreeFocus is free software; you are welcome to redistribute it. See `LICENSE.txt` for details."
    )
    
    parser.add_argument(
        "-d",
        "--device",
        choices=hal.common.HAL_DEVICES,
        required=True,
        help="peripheral to display stimuli and collect eye data"
    )
    
    args = parser.parse_args(); device = args.device

    sp = yaspin(text="Initializing FreeFocus", color="cyan"); sp.start()
    def initialization_is_complete(*_args):
        global sp
        if sp is not None: sp.ok("✔"); sp = None

    esper.set_handler(ipc.clientserver.IPC_CLIENT_RECEIVED_RESPONSE, initialization_is_complete)
    esper.set_handler(ipc.clientserver.IPC_CLIENT_RECEIVED_RESPONSE, prompt_user)

    esper.dispatch_event(ipc.clientserver.IPC_FORK_ENGINE, device)
    while True: esper.process()