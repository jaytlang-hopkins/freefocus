import os
import tempfile

RESOURCES_DIR = "resources"

if not os.path.exists(RESOURCES_DIR): os.makedirs(RESOURCES_DIR)
if not os.path.isdir(RESOURCES_DIR):
    raise FileExistsError("A file named {RESOURCES_DIR} exists in the working directory. Please remove it")

TEMPORARY_DIR = tempfile.TemporaryDirectory(delete=False).name
