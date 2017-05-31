from flask import Flask, render_template, url_for, request, session, redirect
from flask_pymongo import PyMongo
from flask_gravatar import Gravatar
from datetime import datetime
from scripts import utils
from scripts.flask_celery import make_celery
import bcrypt

from cyc_config import cyc_config as cfg

app = Flask(__name__)
app.config['MONGO_DBNAME'] = 'hydra'
app.config['MONGO_URI'] = cfg.MONGODB
app.jinja_env.globals['datetime'] = datetime
app.jinja_env.globals['utils'] = utils

mongo = PyMongo(app)
celery = make_celery(app)
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


@celery.task(name="cyclops.reset_notification")
def reset_notification(name):
    user_list = [x for x in mongo.db.users.find()]
    for user in user_list:
        if user['name'] == name:
            mongo.db.users.update({"name": name},
                                  {"$set": {"notifications": 0}}
                                  )

    return "Notification reset to 0 for {}!".format(name)


def get_current_route():
    rule = request.url_rule
    current_route = rule.rule.split('/')[-1]
    return current_route


@app.route('/')
def index():
    if 'username' in session:
        return render_template("index.html", user_session=session['username'])
    else:
        return render_template("index.html")


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        users = mongo.db.users
        login_user = users.find_one({'name': request.form['username']})

        if login_user:
            if bcrypt.hashpw(request.form['password'].encode('utf-8'), login_user['password'].encode('utf-8')) == login_user['password'].encode('utf-8'):
                session['username'] = request.form['username']
                return redirect(url_for('polyphemus'))

        return 'Invalid username/password combination'

    return render_template('login.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'name': request.form['username']})

        if existing_user is None:
            hashpass = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
            users.insert({'name': request.form['username'], 'password': hashpass, 'email': request.form['email']})
            session['username'] = request.form['username']
            return redirect(url_for('index'))

        return 'That username already exists!'

    return render_template('register.html')


@app.route('/polyphemus')
def polyphemus():
    if 'username' in session:
        subs = [x for x in mongo.db.dailies_submissions.find()]
        user_session = mongo.db.users.find_one({"name": session['username']})
        show_infos = [x for x in mongo.db.show_infos.find()]
        shots = [x for x in mongo.db.shots.find()]
        username_shotList = []
        notifications = [x for x in mongo.db.notifications.find()]
        for n in shots:
            for task in n['tasks']:
                for assignee in task:
                    if session['username'] in task[assignee]:
                        username_shotList.append(n)
        target_shots = utils.sort_by_date(username_shotList)
        todo_coll = [x for x in mongo.db.todolist.find()]
        iso_time = datetime.utcnow()
        current_route = get_current_route()
        for n in todo_coll:
            if n['name'] == session['username']:
                todolist = n['todo']
            else:
                todolist = []
        if user_session['role'] == 'admin':
            shows = [x for x in mongo.db.shows.find()]
        else:
            shows = []
            shows_user_artist = user_session.get("shows")
            for n in shows_user_artist:
                new_show = mongo.db.shows.find_one(n)
                shows.append(new_show)

        return render_template("polyphemus.html", subs=subs, user_session=user_session, shows=shows, show_infos=show_infos, shots=username_shotList, target_shots=target_shots, todolist=todolist, iso_time=iso_time, notifications=notifications, current_route=current_route)
    else:
        return render_template("login.html")


def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)


@app.route('/dev')
def dev():
    publisher = {"publisher": {"name": "Geoffroy", "email": "geoff.givry@gmail.com"}}
    return render_template("dev.html", publisher=publisher)


@app.route("/process/<current_route>/<username>")
def process(current_route, username):
    reset_notification.delay(username)
    return redirect(url_for(current_route))


if __name__ == "__main__":
    app.secret_key = cfg.FLASK_APP_SECRET_KEY
    app.run(debug=True, host="0.0.0.0")
