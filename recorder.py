import csv
import inspect
import os
import sys
import time
import tempfile

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from PIL import Image, ImageDraw
from pyffmpeg import FFmpeg
from tqdm import tqdm
from typing import List, IO
from yaspin import yaspin

import esper
import resources

import logging
logging.getLogger('pyffmpeg').setLevel(logging.ERROR)

# MARK: Events

RECORDER_START = "recorder_start"
RECORDER_DATA_AVAILABLE = "recorder_data_available"
RECORDER_COMPLETE = "recorder_complete"

# MARK: Recording

DATA_CSV_NAME = "data.csv"

class DataReader:
    def __init__(self, recording_directory):
        self._recording_directory = recording_directory
    
    def __enter__(self):
        self._fp = open(os.path.join(self._recording_directory, DATA_CSV_NAME), newline='')
        self._reader = csv.DictReader(self._fp)
        return self._reader
    
    def __exit__(self, _exc_type, _exc_val, _traceback): self._fp.close()

@dataclass
class Recording:
    target_dir: str
    data_file: IO
    data_writer: csv.DictWriter        
    end_time: float

def record_with_duration(duration_seconds):
    target_dir = tempfile.TemporaryDirectory(
        dir=resources.TEMPORARY_DIR,
        prefix="EyeRecording-",
        delete=False
    ).name

    fp = open(os.path.join(target_dir, DATA_CSV_NAME), 'w', newline='')
    r = Recording(target_dir, fp, None, time.time() + duration_seconds)
    esper.create_entity(r)

esper.set_handler(RECORDER_START, record_with_duration)

def flush_images_to_disk(target_dir, datum):
    for k, v in datum.items():
        if type(v) != bytearray: continue

        fp = tempfile.NamedTemporaryFile(
            dir=target_dir,
            suffix=".bmp",
            delete=False
        )

        fp.write(v); datum[k] = fp.name

def receive_datum(datum):
    for _, recorder in esper.get_component(Recording):
        # 1. If any images arrive in the datum, flush those to disk
        flush_images_to_disk(recorder.target_dir, datum)

        # 2. ...then flush out elementary data to disk
        if recorder.data_writer is None:
            recorder.data_writer = csv.DictWriter(recorder.data_file, fieldnames=datum.keys())
            recorder.data_writer.writeheader()
        
        recorder.data_writer.writerow(datum)

esper.set_handler(RECORDER_DATA_AVAILABLE, receive_datum)

# MARK: Annotation

def _annotate_image(csv_data):
    image_path = csv_data["image_bytes"]
    annotation_lines = []
    for key, value in csv_data.items():
        if "image_bytes" == key: continue

        try: compact = f"{key}: {round(float(value), 2)}"
        except ValueError: compact = f"{key}: {value}"
        annotation_lines.append(compact)
    
    annotation = "\n".join(annotation_lines)

    image = Image.open(image_path)
    ImageDraw.Draw(image).text((10, 10), annotation)
    image.save(image_path)

def postprocess_images(recording_directory):
    with DataReader(recording_directory) as reader:
        image_rows = [r for r in reader if r.get("image_bytes") is not None]
        for image_row in tqdm(image_rows, "Annotating images...", leave=False):
            _annotate_image(image_row)

# MARK: Movie

MOVIE_NAME = "AnnotatedEyeVideo.mp4"

class FFMpegConfiguration:
    def _intake_frame_paths_from_csv(self, csv_reader):
        for row in csv_reader:
            try: self._frame_paths.append(row["image_bytes"])
            except KeyError: continue
        
    def __init__(self, csv_reader, fps=70):
        self._frame_paths = []
        self._frame_duration = 1 / fps

        self._intake_frame_paths_from_csv(csv_reader)

    def __enter__(self):
        self._fp = tempfile.NamedTemporaryFile('w', dir=resources.TEMPORARY_DIR, suffix='.txt', delete=False)
        for frame in self._frame_paths:
            print(f"""
                  file '{os.path.join(resources.TEMPORARY_DIR, frame)}'
                  duration {round(self._frame_duration, 5)}
                  """, file=self._fp)

        self._fp.flush()
        return self._fp.name

    def __exit__(self, _exc_type, _exc_val, _traceback):
        self._fp.close()
        os.unlink(self._fp.name)

def postprocess_movie(recording_directory):
    with DataReader(recording_directory) as reader:
        with FFMpegConfiguration(reader) as config:
            ff = FFmpeg(enable_log=False)
            options = " ".join((
                "-safe 0", f"-f concat -i {config}",
                "-c:v libx264", "-pix_fmt yuv420p",
                os.path.join(recording_directory, MOVIE_NAME)
            ))

            with yaspin() as sp:
                sp.text = "Encoding movie..."
                ff.options(options)

# MARK: Post-processing
# Want more post-processing? Define a function that starts with `postprocess_`
# These run alphabetically in serial.

POSTPROCESS_FUNCTIONS = []
for name, obj in inspect.getmembers(sys.modules[__name__]):
    if not inspect.isfunction(obj): continue
    if obj.__module__ != __name__: continue
    if "postprocess_" not in name: continue

    POSTPROCESS_FUNCTIONS.append(obj)

POSTPROCESS_FUNCTIONS.sort(key=lambda f: f.__name__)

@dataclass
class PostProcessor:
    target_dir: str
    executor: object
    futures: List

class FinishRecording(esper.Processor):
    def process(self):
        for ent, recording in esper.get_component(Recording):
            if time.time() >= recording.end_time:
                # 1. Flush the recording
                recording.data_file.close()
                esper.remove_component(ent, Recording)

                # 1. Line up post-processing work...
                executor = ThreadPoolExecutor(max_workers=1)
                futures = [executor.submit(f, recording.target_dir) for f in POSTPROCESS_FUNCTIONS]
                
                # 2. ...and formally switch states
                esper.add_component(ent, PostProcessor(recording.target_dir, executor, futures))

class FinishProcessing(esper.Processor):
    def process(self):
        for ent, postproc in esper.get_component(PostProcessor):
            [f.result() for f in postproc.futures if f.done()]
            postproc.futures = [f for f in postproc.futures if not f.done()]

            if len(postproc.futures) == 0:
                esper.delete_entity(ent)
                esper.dispatch_event(RECORDER_COMPLETE, f"Recording available at {postproc.target_dir}")

# MARK: Main

processors = [
    FinishRecording,
    FinishProcessing
]

for processor in processors:
    esper.add_processor(processor())