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

from scripts import connect_db as con
from pprint import pprint

db = con.server.hydra
   
def delete_seq(seq_name):
    seq_to_delete = db.seqs.find({"name": seq_name})
#     seq_to_delete = db.seqs.delete_many({"name": seq_name})
    shot_to_delete = db.shots.find({"seq": seq_name})
#     shot_to_delete = db.shots.delete_many({"seq": seq_name})
    for seq in seq_to_delete:
        pprint(seq)
    for shot in shot_to_delete:
        pprint(shot)
            
delete_seq("HRM")