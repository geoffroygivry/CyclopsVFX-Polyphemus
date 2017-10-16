import datetime
import re
import xlrd
from scripts import db_actions as dba


def convert_isotime_to_datetime(isotime_format):
    """ Description:
    all the timestamps in CycplopsVFX's Unity are formated in ISO 8601.
    This function is helping to convert iso's string into a datetime object.

    Example of use:

    now = datetime.datetime.utcnow()
    >>> now
    datetime.datetime(2017, 5, 14, 1, 59, 39, 292000)
    now_isoformat = now.isoformat()
    >>> '2017-05-14T01:59:39.292000'
    dateNow = utils.convert_isotime_to_datetime(now_isoformat)
    >>> datetime.datetime(2017, 5, 14, 1, 59, 39, 292000)
    format = "%a %d %b %Y at %H:%M:%S"
    formated_dateNow = dateNow.strftime(format)
    print formated_dateNow
    >>> Sun 14 May 2017 at 01:59:39
    """
    dt, _, us = isotime_format.partition(".")
    dt = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")
    us = int(us.rstrip("Z"), 10)
    return dt + datetime.timedelta(microseconds=us)


def convert_datepicker_to_isotime(date_picker_format):
    """the date_picker_format argument comes from the html forms and it should looks like this: MM/DD/YYYY.
       We want to transform them into our standart ISO format like this :
       YYYY-MM-DDThh:mm:ss.ms
    """
    try:
        year = date_picker_format.split('/')[-1]
        month = date_picker_format.split('/')[0]
        day = date_picker_format.split('/')[1]
        iso_format = "{}-{}-{}T18:00:00.000000".format(year, month, day)
        return iso_format
    except IndexError:
        return None


def sort_by_date(shots):
    overdueList = []
    todayList = []
    tomorrowList = []
    thisWeekList = []
    nextWeekList = []
    laterList = []
    for shot in shots:
        if shot.get("target_date") is not None:
            datetime_target_date = convert_isotime_to_datetime(shot.get("target_date"))
            now = datetime.datetime.utcnow()
            now_week = now.date().isocalendar()[1]
            datetime_target_date_week = datetime_target_date.date().isocalendar()[1]

            time_diff = datetime_target_date - now
            time_diff_days = time_diff.days
            if time_diff_days < 0:
                overdueList.append(shot)
            elif time_diff_days == 0:
                todayList.append(shot)
            elif time_diff_days == 1:
                tomorrowList.append(shot)
            elif 2 <= time_diff_days <= 6:
                if now_week == datetime_target_date_week:
                    thisWeekList.append(shot)
                else:
                    nextWeekList.append(shot)
            elif 7 <= time_diff_days:
                if now_week + 1 == datetime_target_date_week:
                    nextWeekList.append(shot)
                if now_week + 2 <= datetime_target_date_week:
                    laterList.append(shot)

    return {"today": todayList, "tomorrow": tomorrowList, "thisWeek": thisWeekList, "nextWeek": nextWeekList, "later": laterList, "overdue": overdueList}


def get_users_from_shot(db, shot_name):
    shot = db.shots.find_one({"name": shot_name})
    tasks = shot.get('tasks')
    users = [x['assignee'] for x in tasks]
    return users


class Xls_to_mongodb():
    """ Description:
        Class that takes the CyclopsVFX's Excel template and populate the db with entities in bulk.

        Example of usage:

        xx = xls.xls_to_mongodb("/home/geoff/Downloads/cyc-template.xlsx", db)
        xx.populate_shots()
    """

    def __init__(self, path_to_xls, db):
        self.db = db
        self.workbook = xlrd.open_workbook(path_to_xls)

    def convert_xlsDate_to_datetime(self, xls_date):
        if xls_date != "":
            year, month, day, hour, minute, second = xlrd.xldate_as_tuple(xls_date, self.workbook.datemode)
            iso_date = datetime.datetime(year, month, day, hour, minute, second).isoformat()
            return str("{}.000000".format(iso_date))
        else:
            return None

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
                if document['frame_in'] == "":
                    frame_in = 1001
                else:
                    frame_in = document['frame_in']
                if document['frame_out'] == "":
                    frame_out = 1001
                else:
                    frame_out = document['frame_out']
                if document['status'] == "":
                    status = "NOT-STARTED"
                else:
                    status = document['status']
                dba.create_shot(document['show'], document['seq'], document['name'], frame_in=int(frame_in), frame_out=int(frame_out), status=status, target_date=self.convert_xlsDate_to_datetime(document['target_date']))
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
                print("{} has been inserted in the database".format(document['name']))

    def populate_all(self):
        self.populate_shows()
        self.populate_seqs()
        self.populate_shots()
        self.populate_assets()


def join_show(user_name, show_name, db):
    check_join = False
    check_show = False
    user = db.users.find_one({"name": user_name})
    shows = [x['name'] for x in db.shows.find()]
    print(shows)
    for show in shows:
        if show_name in shows:
            print("The show {} exists. User is being added to it.".format(show_name))
        else:
            check_show = True
    for show in user['shows']:
        if show == show_name:
            check_join = True
            break

    if check_join:
        print("User already has joined the show {}".format(show_name))
    else:
        if check_show:
            print("show {} does not exist".format(show_name))
        else:
            db.users.update(
                {"name": user_name},
                {"$push": {"shows": show_name}}
            )


def check_user_show(user_name, show_name, db):
    check = False
    user = db.users.find_one({"name": user_name})
    for show in user['shows']:
        if show_name == show:
            check = True

    return check


def find(key, dictionary):
    for ky, val in dictionary.items():
        if ky == key:
            yield val
        elif isinstance(val, dict):
            for result in find(key, val):
                yield result
        elif isinstance(val, list):
            for dd in val:
                if isinstance(dd, dict):
                    for result2 in find(key, dd):
                        yield result2


class UUID():
    """
    Direction of use:
    publish_uuid_pattern_asset = "RBY_awning01_for_me-I-think_MOD_v03_2017-10-06T23:05:47.17900"
    publish_uuid_pattern_shot = "RBY_MANOR_010_rubbishboy_Final_09_CMP_v04_2017-10-03T22:43:43.17900"

    pub_uuid_asset = UUID(publish_uuid_pattern_asset, "asset")
    pub_uuid_shot = UUID(publish_uuid_pattern_shot, "shot")
    """

    def __init__(self, uuid_pattern, uuid_type):
        self.uuid = uuid_pattern
        self.uuid_type = uuid_type
        self.match_pattern = self.match()

    def compiled_uuid_asset(self):
        return re.compile('^(?P<show_name>[A-Za-z0-9]+)_(?P<asset_name>[A-Za-z0-9_\-]+)_(?P<task_name>[A-Z]{3})_[Vv](?P<version>\d+)_(?P<iso_date>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{5})')

    def compiled_uuid_shot(self):
        return re.compile('^(?P<show_name>[A-Z0-9]{3})_(?P<shot_name>[a-zA-Z]+_[0-9]{3})_(?P<description>[A-Za-z_0-9]+)_(?P<task_name>[A-Z]{3})_[vV](?P<version>\d{2})_(?P<iso_date>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{5})')

    def match(self):
        if self.uuid_type == "asset":
            compiled_uuid_pattern = self.compiled_uuid_asset()
        else:
            compiled_uuid_pattern = self.compiled_uuid_shot()
        match = compiled_uuid_pattern.match(self.uuid)
        return match

    def check_uuid(self):
        if self.match_pattern:
            return True
        else:
            return False

    def show(self):
        if self.check_uuid():
            return self.match_pattern.group('show_name')

    def shot(self):
        if self.check_uuid():
            if self.uuid_type == 'shot':
                return self.match_pattern.group('shot_name')
            else:
                return None

    def name(self):
        if self.check_uuid():
            if self.uuid_type == 'asset':
                return self.match_pattern.group('asset_name')
            else:
                return self.match_pattern.group('description')

    def task(self):
        if self.check_uuid():
            return self.match_pattern.group('task_name')

    def version(self):
        if self.check_uuid():
            return self.match_pattern.group('version')

    def date(self):
        if self.check_uuid():
            return self.match_pattern.group('iso_date')


def get_uuids(kw, db_col):
    uid_list = []
    if isinstance(db_col, list):
        for db in db_col:
            for my_kw in find(kw, db):
                if isinstance(my_kw, list):
                    for y in my_kw:
                        uid_list.append(y)
                else:
                    uid_list.append(my_kw)
    else:
        for x in find(kw, db_col):
            if isinstance(x, list):
                for y in x:
                    uid_list.append(y)
            else:
                uid_list.append(x)
    return uid_list
