import xlrd
from scripts import db_actions as dba
import datetime


class xls_to_mongodb():
    """ Description:
        Class that takes the CyclopsVFX's Excel template and populate the db in bulk.

        Example of usage:

        xx = xls.xls_to_mongodb("/home/geoff/Downloads/cyc-template.xlsx", db)
        xx.populate_shots()
    """
    def __init__(self, path_to_xls, db):
        self.db = db
        self.workbook = xlrd.open_workbook(path_to_xls)

    def convert_xlsDate_to_datetime(self, xls_date):
        year, month, day, hour, minute, second = xlrd.xldate_as_tuple(xls_date, self.workbook.datemode)
        iso_date = datetime.datetime(year, month, day, hour, minute, second).isoformat()
        return iso_date

    def pull_data(self, sheet_page):
        worksheet = self.workbook.sheet_by_index(sheet_page)
        first_row = []  # The row where we stock the name of the column
        for col in range(worksheet.ncols):
            first_row.append(worksheet.cell_value(0, col))
        # transform the workbook to a list of dictionaries
        data = []
        for row in range(1, worksheet.nrows):
            elm = {}
            for col in range(worksheet.ncols):
                elm[first_row[col]] = worksheet.cell_value(row, col)
            data.append(elm)
        return data

    def populate_shows(self):
        data = self.pull_data(0)
        for document in data:
            if self.db.shows.find({"name": document['name']}).count() > 0:
                print("{} already exists!".format(document['name']))
            else:
                dba.create_show(document['long_name'], document['name'])
                print("{} will be inserted".format(document['name']))

    def populate_seqs(self):
        data = self.pull_data(1)
        for document in data:
            if self.db.seqs.find({"name": document['name']}).count() > 0:
                print("{} already exists!".format(document['name']))
            else:
                dba.create_seq(document['show'], document['name'])
                print("{} is inserted".format(document['name']))

    def populate_shots(self):
        data = self.pull_data(2)
        for document in data:
            if self.db.shots.find({"name": document['name']}).count() > 0:
                print("{} already exists!".format(document['name']))
            else:
                dba.create_shot(document['show'], document['seq'], document['name'], frame_in=int(document.get('frame_in', 1001)), frame_out=int(document.get('frame_out', 1001)), status=document['status'], target_date=self.convert_xlsDate_to_datetime(document['target_date']))
                print("{} is inserted".format(document['name']))

    def populate_assets(self):
        data = self.pull_data(3)
        for document in data:
            if self.db.assets.find({"name": document['name']}).count() > 0:
                print("{} already exists!".format(document['name']))
            else:
                if document['hero'] == "Hero":
                    hero_type = True
                else:
                    hero_type = False
                dba.create_asset(document['show'], document['name'], document['type'], hero_type, self.convert_xlsDate_to_datetime(document['target_date']))

    def populate_all(self):
        self.populate_shows()
        self.populate_seqs()
        self.populate_shots()
        self.populate_assets()


"""
# For testing purpose:
from scripts import testxls as xls
from scripts import connect_db as con
from importlib import reload
reload(xls)
db = con.server.hydra

xx = xls.xls_to_mongodb("/home/geoff/Downloads/cyc-template.xlsx", db)
xx.populate_shots()
"""
