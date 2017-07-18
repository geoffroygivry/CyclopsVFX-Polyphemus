import xlrd
from scripts import db_actions as dba


class xls_to_mongodb():
    def __init__(self, path_to_xls, db):
        self.db = db
        self.workbook = xlrd.open_workbook(path_to_xls)
        
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
#                 dba.create_show(document['long_name'], document['name'])
                print("{} will be inserted".format(document['name']))



# load_xls = xls_to_mongodb("/home/geoff/Downloads/cyc-template.xlsx", db)
# load_xls.populate_shows()
