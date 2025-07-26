import sys
import esper

import cli
import hal
import ui
import recorder

# MARK: FSM glue

def push_frame(texture_id): esper.dispatch_event(hal.HAL_PUSH_FRAME_AND_VSYNC, texture_id)
esper.set_handler(ui.UI_FRAME_READY, push_frame)

def data_available(datum): esper.dispatch_event(recorder.RECORDER_DATA_AVAILABLE, datum)
esper.set_handler(hal.HAL_DATA_PUBLISHED, data_available)

def recording_complete(output_path): esper.dispatch_event(cli.CLI_RESPONSE_READY, True, output_path)
esper.set_handler(recorder.RECORDER_COMPLETE, recording_complete)

# MARK: Command parsing

def parse_show(args):
    elements_to_ui_states = {
        "okn": ui.UI_STATE_CONVERGING,
        "pursuit": ui.UI_STATE_IDLE,
    }
    usage = f"usage: show {list(elements_to_ui_states.keys())}"

    if len(args) != 1 or args[0] not in elements_to_ui_states:
        esper.dispatch_event(cli.CLI_RESPONSE_READY, False, usage)
    else: 
        esper.dispatch_event(elements_to_ui_states[args[0]])
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

while True: esper.process()
