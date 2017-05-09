import connect_db as con

server = con.server
db = server.hydra


def get_all_shows():
    shows = [x for x in db.shows.find()]
    print shows


def get_user_shows(user_name):
    user = db.users.find_one({"name": user_name})
    shows = db.shows.find()


get_all_shows()
