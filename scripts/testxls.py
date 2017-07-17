import xlrd

workbook = xlrd.open_workbook('/home/cabox/workspace/cyc-template.xlsx')
worksheet = workbook.sheet_by_index(0)
first_row = [] # The row where we stock the name of the column
for col in range(worksheet.ncols):
    first_row.append( worksheet.cell_value(0,col) )
# transform the workbook to a list of dictionaries
data =[]
for row in range(1, worksheet.nrows):
    elm = {}
    for col in range(worksheet.ncols):
        elm[first_row[col]]=worksheet.cell_value(row,col)
    data.append(elm)
print(data)


class xls_to_mongodb():
    def __init__(self, path_to_xls, db):
        self.db = db
        self.workbook = xlrd.open_workbook(path_to_xls)
        
    def populate_shows(self):
        worksheet = self.workbook.sheet_by_index(0)
        first_row = [] # The row where we stock the name of the column
        for col in range(worksheet.ncols):
            first_row.append( worksheet.cell_value(0,col) )
        # transform the workbook to a list of dictionaries
        data =[]
        for row in range(1, worksheet.nrows):
            elm = {}
            for col in range(worksheet.ncols):
                elm[first_row[col]]=worksheet.cell_value(row,col)
            data.append(elm)
        for document in data:
            print(document)
