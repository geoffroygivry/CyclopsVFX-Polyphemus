import datetime


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
