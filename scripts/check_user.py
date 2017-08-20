from scripts import connect_db as con
db = con.server.hydra


class Check_user():
    def __init__(self, user_name, show_name, DB):
        self.user_name = user_name
        self.show_name = show_name
        self.DB = DB
        self.user_session = self.DB.users.find_one({"name": self.user_name})
        if self.user_session.get("role") == "admin":
            self.is_admin = True
        else:
            self.is_admin = False

    def check_show(self):
        if self.is_admin:
            return True
        else:
            if self.show_name in [x for x in self.user_session.get("shows")]:
                return True
            else:
                return False

    def check_seq(self, seq_name):
        if self.is_admin:
            return True
        else:
            seq = db.seqs.find_one({"name": seq_name})
            if seq is not None:
                if seq.get("show") in [x for x in self.user_session.get("shows")]:
                    return True
                else:
                    return False
            else:
                return False

    def check_shot(self, shot_name):
        if self.is_admin:
            return True
        else:
            shot = db.shots.find_one({"name": shot_name})
            if shot is not None:
                if shot.get("show") in [x for x in self.user_session.get("shows")]:
                    return True
                else:
                    return False
            else:
                return False
