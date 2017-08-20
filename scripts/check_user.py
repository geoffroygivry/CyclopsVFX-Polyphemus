from scripts import connect_db as con
db = con.server.hydra


class Check_user():
    def __init__(self, user_name, show_name, DB):
        self.user_name = user_name
        self.show_name = show_name
        self.DB = DB
        self.user_session = self.DB.users.find_one({"name": self.user_name})
        self.is_admin = self.user_session.get("role")

    def check_show(self):
        if self.is_admin != "admin":
            if self.show_name in [x for x in self.user_session.get("shows")]:
                return True
            else:
                return False
        else:
            return True

    def check_seq(self, seq_name):
        if self.is_admin != "admin":
            seq = db.seqs.find_one({"name": seq_name})
            if seq is not None:
                try:
                    if seq.get("show") in [x for x in self.user_session.get("shows")]:
                        return True
                    else:
                        return False
                except AttributeError:
                    return False
            else:
                return False
        else:
            return True

    def check_shot(self, shot_name):
        if self.is_admin != "admin":
            shot = db.shots.find_one({"name": shot_name})
            if shot is not None:
                try:
                    if shot.get("show") in [x for x in self.user_session.get("shows")]:
                        return True
                    else:
                        return False
                except AttributeError:
                    return False
            else:
                return False
        else:
            return True


testq = Check_user("Geoffroy", "RBY", db)
print(testq.check_show())
print(testq.check_seq("MANORs"))
print(testq.check_shot("MANOR_018"))
