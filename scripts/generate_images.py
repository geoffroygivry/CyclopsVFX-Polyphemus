import os
import subprocess

def banner_and_thumb(filename, shot_name):
    tmp_folder = "/home/cabox/workspace/CyclopsVFX-Polyphemus/tmp"
    dest_folder = "/home/cabox/workspace/CyclopsVFX-Polyphemus/static/polyphemus/assets/img/banners"
    if os.path.isfile(os.path.join(tmp_folder, filename)):
        shot_banner = "%s_banner.jpg" % shot_name.get('name')
        shot_thumb = "%s_thumb.jpg" % shot_name.get('name')
        subprocess.check_call("convert -resize 700 %s/%s %s/%s" % (tmp_folder, filename, dest_folder, shot_banner), shell=True)
        subprocess.check_call("convert -resize 290 %s/%s %s/%s" % (tmp_folder, filename, dest_folder, shot_thumb), shell=True)
