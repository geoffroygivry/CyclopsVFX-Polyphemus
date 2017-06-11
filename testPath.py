import os

dir_path = os.path.dirname(os.path.realpath(__file__))
UPLOAD_FOLDER = os.path.join(dir_path, 'tmp')

print UPLOAD_FOLDER

print os.path.exists(UPLOAD_FOLDER)