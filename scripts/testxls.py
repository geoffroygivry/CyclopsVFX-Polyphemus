# For testing purpose:
from scripts import utils as xls
from scripts import connect_db as con
from importlib import reload
reload(xls)
db = con.server.hydra

xx = xls.xls_to_mongodb("/home/cabox/workspace/cyc-template.xlsx", db)
xx.populate_all()

