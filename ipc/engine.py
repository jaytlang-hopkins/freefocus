# File: ipc/engine.py
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

import importlib
import sys
import esper

from . import clientserver
import hal.common
import ui
import recorder

# MARK: FSM glue
def push_frame(texture_id): esper.dispatch_event(hal.common.HAL_PUSH_FRAME_AND_VSYNC, texture_id)
esper.set_handler(ui.UI_FRAME_READY, push_frame)

def data_available(datum): esper.dispatch_event(recorder.RECORDER_DATA_AVAILABLE, datum)
esper.set_handler(hal.common.HAL_DATA_PUBLISHED, data_available)

def recording_complete(output_path): esper.dispatch_event(clientserver.IPC_SERVER_RESPONSE_READY, True, output_path)
esper.set_handler(recorder.RECORDER_COMPLETE, recording_complete)

def start_ui(window_size, context=None): esper.dispatch_event(ui.UI_START, window_size, context)
esper.set_handler(hal.common.HAL_RENDER_CONTEXT_READY, start_ui)

# MARK: Command parsing

def parse_show(args):
    elements_to_ui_actions = {
        "okn": ui.UI_START_OKN,
        "idle": ui.UI_GO_IDLE,
        "saccades": ui.UI_START_SACCADES,
    }
    usage = f"usage: show {list(elements_to_ui_actions.keys())}"

    if len(args) != 1 or args[0] not in elements_to_ui_actions:
        esper.dispatch_event(clientserver.IPC_SERVER_RESPONSE_READY, False, usage)
    else: 
        esper.dispatch_event(elements_to_ui_actions[args[0]])
        esper.dispatch_event(clientserver.IPC_SERVER_RESPONSE_READY, True)

esper.dispatch_event(clientserver.IPC_SERVER_ADD_PARSER, "show", "display an ocular test", parse_show)

def parse_exit(_args):
    print("Stopped by client")
    sys.exit(0)

esper.dispatch_event(clientserver.IPC_SERVER_ADD_PARSER, "exit", "stop the FreeFocus service", parse_exit)

def parse_record(args):
    usage = "usage: record duration[unit]. supported units are s(econds, e.g. 10s), m(inutes, e.g. 1m)"
    seconds_per_unit = {"s": 1, "m": 60}

    try:
        seconds = args[0]
        recording_duration = int(seconds[:-1]) * seconds_per_unit[seconds[-1]]
    except (KeyError, ValueError):
        esper.dispatch_event(clientserver.IPC_SERVER_RESPONSE_READY, False, usage)

    esper.dispatch_event(recorder.RECORDER_START, recording_duration)

esper.dispatch_event(clientserver.IPC_SERVER_ADD_PARSER, "record", "analyze eye movements for a given duration", parse_record)

# MARK: Entry

ENGINE_START_RUNLOOP = "engine_start_runloop"

def start_runloop(target_device):
    importlib.import_module(f"hal.{target_device}")
    while True: esper.process()

esper.set_handler(ENGINE_START_RUNLOOP, start_runloop)