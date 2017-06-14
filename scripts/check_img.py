import os
from flask import url_for


def banner(shot_name):
    check = False
    static_img_folder = "./static/polyphemus/assets/img/banners"
    for n in os.listdir(static_img_folder):
        if n in "{}_banner.jpg".format(shot_name):
            check = True
            
    if check:
        return url_for('static', filename='polyphemus/assets/img/banners/{}_banner.jpg'.format(shot_name))
    else:
        return url_for('static', filename='polyphemus/assets/img/cyc_placeholder.png')
    
   
def thumb(shot_name):
    check = False
    static_img_folder = "./static/polyphemus/assets/img/banners"
    for n in os.listdir(static_img_folder):
        if n in "{}_thumb.jpg".format(shot_name):
            check = True
            
    if check:
        return url_for('static', filename='polyphemus/assets/img/banners/{}_thumb.jpg'.format(shot_name))
    else:
        return url_for('static', filename='polyphemus/assets/img/cyc_placeholder.png')
