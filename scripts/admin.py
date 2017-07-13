# The MIT License (MIT)
#
# Copyright (c) 2015 Geoffroy Givry
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys
import bcrypt

from scripts import connect_db as con


def modify_shot(shot_name, status, task_type, task_assignee, task_status, iso_target_date, frame_in, frame_out):
    db = con.server.hydra
    if status != "NOT-STARTED":
        db.shots.update({"name": shot_name}, {"$set": {"status": status}})
    if task_type != "Choose...":
        if task_assignee != "Choose...":
            db.shots.update(
                {"name": shot_name},
                {"$push":
                 {"tasks": {"task": task_type, "assignee": task_assignee, "status": task_status}}
                 }
            )
    if iso_target_date is not None:
        db.shots.update({"name": shot_name}, {"$set": {"target_date": iso_target_date}})
    if frame_in != "":
        db.shots.update({"name": shot_name}, {"$set": {"frame_in": frame_in}})
    if frame_out != "":
        db.shots.update({"name": shot_name}, {"$set": {"frame_out": frame_out}})

            
def modify_password(login_user, current_password, new_password):
            db = con.server.hydra
            if bcrypt.hashpw(current_password.encode('utf-8'), login_user['password'].encode('utf-8')) == login_user['password'].encode('utf-8'):
                hashpass = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                db.users.update({'name': login_user['name']}, {"$set": {'password': hashpass.decode('utf-8')}})
            
            
            
            
            
            
            
            