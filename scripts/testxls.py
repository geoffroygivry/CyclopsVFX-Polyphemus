import xlrd


class xls_to_mongodb2():
    def __init__(self, path_to_xls, db):
        self.db = db
        self.workbook = xlrd.open_workbook(path_to_xls)

    def populate_shows(self):
        worksheet = self.workbook.sheet_by_index(0)
        first_row = []  # The row where we stock the name of the column
        for col in range(worksheet.ncols):
            first_row.append(worksheet.cell_value(0, col))
        # transform the workbook to a list of dictionaries
        data = []
        for row in range(1, worksheet.nrows):
            elm = {}
            for col in range(worksheet.ncols):
                elm[first_row[col]] = worksheet.cell_value(row, col)
                elm['sequences'] = []
                elm['ptuid'] = 1
                elm['active'] = False
                elm['assets'] = []
            data.append(elm)
        for document in data:
            if db.shows.find({"name": document['name']}).count() > 0:
                print("{} already exists!".format(document['name']))
            else:
                print("let's insert this bad boy! {}".format(document['name']))
                print("doing it...")
                db.shows.insert_one(document)
                print("bad boy inserted!")


load_xls = xls_to_mongodb2("/home/geoff/Downloads/cyc-template.xlsx", db)
load_xls.populate_shows()
