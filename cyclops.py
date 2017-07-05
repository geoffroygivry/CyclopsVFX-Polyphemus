import os
from flask import Flask, render_template, url_for, request, session, redirect, Response
from flask_pymongo import PyMongo
from flask_gravatar import Gravatar
from datetime import datetime
from scripts import utils
from scripts.flask_celery import make_celery
from scripts import aws_s3
from scripts import generate_images
from scripts import check_img as ci
from scripts.forms import ShotForm
import bcrypt
import json

from cyc_config import cyc_config as cfg

from werkzeug.utils import secure_filename

dir_path = os.path.dirname(os.path.realpath(__file__))
UPLOAD_FOLDER = os.path.join(dir_path, 'tmp')
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MONGO_DBNAME'] = 'hydra'
app.config['MONGO_URI'] = cfg.MONGODB
app.jinja_env.globals['datetime'] = datetime
app.jinja_env.globals['utils'] = utils
app.jinja_env.globals['aws_s3'] = aws_s3
app.jinja_env.globals['os'] = os
app.jinja_env.globals['ci'] = ci

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


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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


def redirect_url(default='index'):
    return request.args.get('next') or \
        request.referrer or \
        url_for(default)


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        users = mongo.db.users
        login_user = users.find_one({'name': request.form['username']})

        if login_user:
            if bcrypt.hashpw(request.form['password'].encode('utf-8'), login_user['password'].encode('utf-8')) == login_user['password'].encode('utf-8'):
                session['username'] = request.form['username']
                # return redirect(url_for('polyphemus'))
                return redirect(redirect_url())

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
        subs = [x for x in mongo.db.submissions.find()]
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


@app.route('/polyphemus/<show>/<seq>/<shot_name>', methods=['GET', 'POST'])
def shot(show, seq, shot_name):
    if 'username' in session:
        shot = mongo.db.shots.find_one({"name": shot_name})
        users = [x for x in mongo.db.users.find()]
#         subs = [x for x in mongo.db.submissions.find() if x.get('Shot') == shot_name]
        subs = [x for x in mongo.db.submissions.find()]
        user_session = mongo.db.users.find_one({"name": session['username']})
        notifications = [x for x in mongo.db.notifications.find()]
        iso_time = datetime.utcnow()
        collaborators = [x for x in shot.get('tasks')]
        current_route = get_current_route()
        assets = [x for x in shot.get('assets', [])]
        if user_session['role'] == 'admin':
            shows = [x for x in mongo.db.shows.find()]
        else:
            shows = []
            shows_user_artist = user_session.get("shows")
            for n in shows_user_artist:
                new_show = mongo.db.shows.find_one(n)
                shows.append(new_show)

        if request.method == 'POST':
                # check if the post request has the file part
            if 'file' not in request.files:
                flash('No file part')
                return redirect(request.url)
            file = request.files['file']
            # if user does not select file, browser also
            # submit a empty part without filename
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                generate_images.banner_and_thumb(filename, shot)

        return render_template("shot.html", show=show, seq=seq, subs=subs, user_session=user_session, shows=shows, iso_time=iso_time, notifications=notifications, current_route=current_route, shot=shot, collaborators=collaborators, users=users, assets=assets)
    else:
        return render_template("login.html")


@app.route('/polyphemus/<show>/<seq>')
def seq(show, seq):
    if 'username' in session:
        user_session = mongo.db.users.find_one({"name": session['username']})
        notifications = [x for x in mongo.db.notifications.find()]
        if user_session['role'] == 'admin':
            shows = [x for x in mongo.db.shows.find()]
        else:
            shows = []
            shows_user_artist = user_session.get("shows")
            for n in shows_user_artist:
                new_show = mongo.db.shows.find_one(n)
                shows.append(new_show)

        seq = mongo.db.seqs.find_one({"name": seq})
        shots = [x for x in mongo.db.shots.find() if x.get('seq') == seq.get('name')]
        subs = [x for x in mongo.db.submissions.find()]

        return render_template("sequence.html", show=show, seq=seq, user_session=user_session, shows=shows, notifications=notifications, shots=shots, subs=subs)
    else:
        return render_template("login.html")


@app.route('/polyphemus/<show>')
def show(show):
    return render_template("show.html", show=show)


@app.route('/polyphemus/users/<user_name>')
def user(user_name):
    if 'username' in session:
        user_name = mongo.db.users.find_one({"name": user_name})
        user_session = mongo.db.users.find_one({"name": session['username']})
        subs = [x for x in mongo.db.submissions.find()]
        notifications = [x for x in mongo.db.notifications.find()]
        shots = [x for x in mongo.db.shots.find()]
        if user_session['role'] == 'admin':
            shows = [x for x in mongo.db.shows.find()]
        else:
            shows = []
            shows_user_artist = user_session.get("shows")
            for n in shows_user_artist:
                new_show = mongo.db.shows.find_one(n)
                shows.append(new_show)

    return render_template("user.html", user_name=user_name, subs=subs, user_session=user_session,
                           notifications=notifications, shows=shows, shots=shots)


@app.route('/admin')
def admin():
    if 'username' in session:
        user_session = mongo.db.users.find_one({"name": session['username']})
        if user_session.get('role') == 'admin':
            subs = [x for x in mongo.db.submissions.find()]
            notifications = [x for x in mongo.db.notifications.find()]
            shows = [x for x in mongo.db.shows.find()]
            users = [x for x in mongo.db.users.find()]
            seqs = [x for x in mongo.db.seqs.find()]
            shots = [x for x in mongo.db.shots.find()]
            assets = [x for x in mongo.db.assets.find()]
            utilz = [x for x in mongo.db.utils.find()]

            return render_template("admin.html", user_session=user_session, shows=shows, subs=subs,
                                   users=users, seqs=seqs, shots=shots, assets=assets, notifications=notifications, utilz=utilz)
        else:
            return render_template("oops.html")
    else:
        return render_template('login.html')


@app.route('/modify-shot/<shot_name>', methods=['POST'])
def modify_shot(shot_name):
    task_to_modify = request.form['task-select']
    task_assignee = request.form['task-assignee']
    target_date = request.form['date-{}'.format(shot_name)]
    iso_target_date = utils.convert_datepicker_to_isotime(target_date)
    print("The shot you want to modify is: {}, the task is {}, the target date is {} and the assignee is {}".format(shot_name, task_to_modify, iso_target_date, task_assignee))
    return redirect(redirect_url())


@app.route('/modify-show/<show_name>', methods=['POST'])
def modify_show(show_name):
    show_is_active = request.form['show-active']
    print(show_is_active, show_name)
    return redirect(redirect_url())


def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)


@app.route("/get-users/<task>")
def get_user_by_task(task):
    assignee = []
    users = [x for x in mongo.db.users.find()]
    for user in users:
        for task_user in user.get('tasks'):
            print(user.get('tasks'))
            if task_user == task:
                assignee.append(user.get('name'))

    return Response(json.dumps(assignee), mimetype='application/json')


@app.route('/delete-shot/<shot_name>', methods=['POST'])
def delete_shot(shot_name):
    shot_to_delete = request.form['shotName']
    print("You are about to delete {}".format(shot_to_delete))
    return redirect(redirect_url())


@app.route('/remove-show/<show_name>', methods=['POST'])
def remove_show(show_name):
    show_to_delete = request.form['showName']
    print("You are about to delete {}".format(show_to_delete))
    return redirect(redirect_url())


@app.route('/remove-seq/<seq_name>', methods=['POST'])
def remove_seq(seq_name):
    seq_to_delete = request.form['seqName']
    print("You are about to delete {}".format(seq_to_delete))
    return redirect(redirect_url())


@app.route('/remove-user/<user_name>', methods=['POST'])
def remove_user(user_name):
    user_to_delete = request.form['userName']
    print("You are about to delete {}".format(user_to_delete))
    return redirect(redirect_url())


@app.route('/remove-sub/<ptuid>', methods=['POST'])
def remove_sub(ptuid):
    sub_to_delete = request.form['ptuid']
    print("You are about to delete {}".format(sub_to_delete))
    return redirect(redirect_url())


@app.route("/process/<current_route>/<username>")
def process(current_route, username):
    reset_notification.delay(username)
    return redirect(url_for(current_route))


if __name__ == "__main__":
    app.secret_key = cfg.FLASK_APP_SECRET_KEY
    app.run(debug=True, host="0.0.0.0")
