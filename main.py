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
import importlib
import sys
import esper

import cli
import hal.common
import ui
import recorder

# MARK: FSM glue

def push_frame(texture_id): esper.dispatch_event(hal.common.HAL_PUSH_FRAME_AND_VSYNC, texture_id)
esper.set_handler(ui.UI_FRAME_READY, push_frame)

def data_available(datum): esper.dispatch_event(recorder.RECORDER_DATA_AVAILABLE, datum)
esper.set_handler(hal.common.HAL_DATA_PUBLISHED, data_available)

def recording_complete(output_path): esper.dispatch_event(cli.CLI_RESPONSE_READY, True, output_path)
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
        esper.dispatch_event(cli.CLI_RESPONSE_READY, False, usage)
    else: 
        esper.dispatch_event(elements_to_ui_actions[args[0]])
        esper.dispatch_event(cli.CLI_RESPONSE_READY, True)

esper.dispatch_event(cli.CLI_ADD_PARSER, "show", "display an ocular test", parse_show)

def parse_exit(_args):
    print("Stopped by client")
    sys.exit(0)

esper.dispatch_event(cli.CLI_ADD_PARSER, "exit", "stop the EyeMotion service", parse_exit)

def parse_record(args):
    usage = "usage: record duration[unit]. supported units are s(econds, e.g. 10s), m(inutes, e.g. 1m)"
    seconds_per_unit = {"s": 1, "m": 60}

    try:
        seconds = args[0]
        recording_duration = int(seconds[:-1]) * seconds_per_unit[seconds[-1]]
    except (KeyError, ValueError):
        esper.dispatch_event(cli.CLI_RESPONSE_READY, False, usage)

    esper.dispatch_event(recorder.RECORDER_START, recording_duration)

esper.dispatch_event(cli.CLI_ADD_PARSER, "record", "analyze eye movements for a given duration", parse_record)

# MARK: Main

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

args = parser.parse_args()
importlib.import_module(f"hal.{args.device}")

while True: esper.process()
