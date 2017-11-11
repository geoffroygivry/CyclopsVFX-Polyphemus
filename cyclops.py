import os
from flask import Flask, render_template, url_for, request, session, redirect, Response, flash
from flask_pymongo import PyMongo
from flask_gravatar import Gravatar
from datetime import datetime
from scripts import utils
from scripts.flask_celery import make_celery
from scripts import aws_s3
from scripts import generate_images
from scripts import admin as ad
from scripts import check_img as ci
from scripts import db_actions as dba
from scripts import check_user
from bson import json_util
import re
import bcrypt
import json

from cyc_config import cyc_config as cfg

from werkzeug.utils import secure_filename

dir_path = os.path.dirname(os.path.realpath(__file__))
UPLOAD_FOLDER = os.path.join(dir_path, 'tmp')
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
ALLOWED_XLS_EXTENSIONS = set(['xls', 'xlsx'])

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


def allowed_xls_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_XLS_EXTENSIONS


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


def dirs_to_watch(extras_dirs):
    from os import path

    extra_dirs = [extras_dirs, ]
    extra_files = extra_dirs[:]
    for extra_dir in extra_dirs:
        for dirname, dirs, files in os.walk(extra_dir):
            for filename in files:
                filename = path.join(dirname, filename)
                if path.isfile(filename):
                    extra_files.append(filename)
    return extra_files


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

        warning_header = "That username already exists!"
        warning_msg = "Please choose another username."
        return render_template("oops.html", warning_msg=warning_msg, warning_header=warning_header)

    return render_template('register.html')


@app.route('/logout')
def logout():
    if 'username' in session:
        session.pop('username', None)
        return redirect(url_for('index'))


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
            shows_user_artist = user_session['shows']
            for n in shows_user_artist:
                new_show = mongo.db.shows.find_one({"name": n})
                shows.append(new_show)

        return render_template("polyphemus.html", subs=subs, user_session=user_session, shows=shows, show_infos=show_infos, shots=username_shotList, target_shots=target_shots, todolist=todolist, iso_time=iso_time, notifications=notifications, current_route=current_route)
    else:
        return render_template("login.html")


@app.route('/polyphemus/<show>/<seq>/<shot_name>', methods=['GET', 'POST'])
def shot(show, seq, shot_name):
    if 'username' in session:
        user_session = mongo.db.users.find_one({"name": session['username']})
        check = check_user.Check_user(user_session.get("name"), show, mongo.db)
        check_for_shot = check.check_shot(shot_name)
        if check_for_shot:
            shot = mongo.db.shots.find_one({"name": shot_name})
            users = [x for x in mongo.db.users.find()]
            subs = [x for x in mongo.db.submissions.find()]
            notifications = [x for x in mongo.db.notifications.find()]
            iso_time = datetime.utcnow()
            collaborators = [x for x in shot.get('tasks', [])]
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
            warning_header = " Sorry this is a restricted area!".format(show)
            warning_msg = "We suggest you to contact your Admin if you think you can access to this page."
            return render_template("oops.html", warning_msg=warning_msg, warning_header=warning_header)

    else:
        return render_template("login.html")


@app.route('/polyphemus/<show>/<seq>')
def seq(show, seq):
    if 'username' in session:
        user_session = mongo.db.users.find_one({"name": session['username']})
        check = check_user.Check_user(user_session.get("name"), show, mongo.db)
        check_for_seq = check.check_seq(seq)
        if check_for_seq:
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
            warning_header = " Sorry this is a restricted area!".format(show)
            warning_msg = "We suggest you to contact your Admin if you think you can access to this page."
            return render_template("oops.html", warning_msg=warning_msg, warning_header=warning_header)
    else:
        return render_template("login.html")


@app.route('/polyphemus/<show>')
def show(show):
    if 'username' in session:
        user_session = mongo.db.users.find_one({"name": session['username']})
        check = check_user.Check_user(user_session.get("name"), show, mongo.db)
        check_for_shot = check.check_show()
        if check_for_shot:
            notifications = [x for x in mongo.db.notifications.find()]
            subs = [x for x in mongo.db.submissions.find()]
            shots = [x for x in mongo.db.shots.find()]
            assets = [x for x in mongo.db.assets.find() if x.get("show") == show]
            users = [x for x in mongo.db.users.find() if show in x.get("shows")]
            if user_session['role'] == 'admin':
                shows = [x for x in mongo.db.shows.find()]
            else:
                shows = []
                shows_user_artist = user_session.get("shows")
                for n in shows_user_artist:
                    new_show = mongo.db.shows.find_one({"name": n})
                    shows.append(new_show)
            print(shows)
            return render_template("show.html", show=show, user_session=user_session, shows=shows, shots=shots, notifications=notifications, subs=subs, assets=assets, users=users)
        else:
            shows = [x for x in mongo.db.shows.find()]
            if show in [show.get('name') for show in shows]:
                warning_header = " {} page is a restricted access.".format(show)
                warning_msg = "It seems you are not working on this show. Contact your Admin for more information"
            else:
                warning_header = " {} Does not exists!".format(show)
                warning_msg = "We suggest you to contact your Admin to get the list of the existing shows you are assigned in."
            return render_template("oops.html", warning_msg=warning_msg, warning_header=warning_header)
    else:
        return render_template("login.html")


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


@app.route('/polyphemus/profile/<user_name>')
def profile(user_name):
    if 'username' in session:
        if session['username'] == user_name:
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

            return render_template("user-profile.html", user_name=user_name, user_session=user_session,
                                   notifications=notifications, subs=subs, shots=shots, shows=shows)
        else:
            warning_header = "Restricted Area. Toxic!"
            warning_msg = "It seems you dont have all rights to do this action. Ask your Admin what to do next"
            return render_template("oops.html", warning_msg=warning_msg, warning_header=warning_header)
    else:
        return render_template("login.html")


@app.route('/update-profile', methods=['POST'])
def update_profile():
    pass_to_change = request.form['currentPassword']
    new_password = request.form['newPassword']
    login_user = mongo.db.users.find_one({'name': session['username']})

    ad.modify_password(login_user, pass_to_change, new_password)
    return redirect(redirect_url())


@app.route('/update-profile-detail', methods=['POST', 'GET'])
def update_profile_detail():
    if 'username' in session:
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
        if request.method == 'POST':
            # lets go!
            details_url = request.form['url']
            mongo.db.users.update({"name": session['username']}, {"$set": {"url": details_url}})

            details_email = request.form['email']
            mongo.db.users.update({"name": session['username']}, {"$set": {"email": details_email}})

            details_phone = request.form['phone']
            mongo.db.users.update({"name": session['username']}, {"$set": {"phone": details_phone}})

            details_skype = request.form['skype']
            mongo.db.users.update({"name": session['username']}, {"$set": {"skype": details_skype}})
            return redirect(redirect_url())

        user_session = mongo.db.users.find_one({"name": session['username']})
        return render_template("user.html", subs=subs, user_session=user_session, notifications=notifications, shows=shows, shots=shots)
    else:
        return render_template("login.html")


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
            warning_header = "Restricted Area. Toxic!"
            warning_msg = "It seems you are not an Admin Role User"
            return render_template("oops.html", warning_msg=warning_msg, warning_header=warning_header)

    else:
        return render_template('login.html')


@app.route('/system-dash')
def system_dash():
    return "<h1>This is sys dash</h1>"


@app.route('/modify-shot/<shot_name>', methods=['POST'])
def modify_shot(shot_name):
    status = request.form['shot-status']
    task_type = request.form['task-select']
    task_assignee = request.form['task-assignee']
    task_status = request.form['task-status']
    target_date = request.form['date-{}'.format(shot_name)]
    frame_in = request.form['frame-in']
    frame_out = request.form['frame-out']
    iso_target_date = utils.convert_datepicker_to_isotime(target_date)
    ad.modify_shot(shot_name, status, task_type, task_assignee, task_status, iso_target_date, frame_in, frame_out)
    print("The shot you want to modify is: {}, the task is {}, the target date is {} and the assignee is {}. frame in: {}, frame out: {}".format(shot_name, task_type, iso_target_date, task_assignee, frame_in, frame_out))
    return redirect(redirect_url())


@app.route('/modify-asset/<asset_name>', methods=['POST'])
def modify_asset(asset_name):
    hero_type = request.form['asset-hero-type']
    if hero_type == "Hero":
        hero = True
    else:
        hero = False
    task_type = request.form['task-select']
    task_assignee = request.form['task-assignee']
    task_status = request.form['task-status']
    target_date = request.form['date-{}'.format(asset_name)]
    iso_target_date = utils.convert_datepicker_to_isotime(target_date)
    ad.modify_asset(asset_name, task_type, task_assignee, task_status, iso_target_date, hero)
    print("The asset you want to modify is: {}, the task is {}, the target date is {} and the assignee is {}.".format(asset_name, task_type, iso_target_date, task_assignee, task_status))
    return redirect(redirect_url())


@app.route('/modify-show/<show_name>', methods=['POST'])
def modify_show(show_name):
    show_is_active = request.form['show-active']
    if show_is_active == "Active":
        mongo.db.shows.update({"name": show_name}, {"$set": {"active": True}})
    else:
        mongo.db.shows.update({"name": show_name}, {"$set": {"active": False}})
        print(show_name, "False")
    # print(show_is_active, show_name)
    return redirect(redirect_url())


@app.route('/modify-user/<user_name>', methods=['POST'])
def modify_user(user_name):
    show_name = request.form['show-name']
    print(show_name)
    utils.join_show(user_name, show_name, mongo.db)
    return "yup"


def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)


@app.route("/get-users/<task>")
def get_user_by_task(task):
    assignee = []
    dict_users = {}
    dict_users['users'] = assignee
    users = [x for x in mongo.db.users.find()]
    for user in users:
        if user.get('tasks') is not None:
            for task_user in user.get('tasks'):
                if task_user == task:
                    assignee.append(user.get('name'))

    return Response(json.dumps(dict_users), mimetype='application/json')


@app.route('/delete-shot/<shot_name>', methods=['POST'])
def delete_shot(shot_name):
    shot_to_delete = request.form['shotName']
    mongo.db.shots.delete_one({"name": shot_to_delete})
    print("Shot {} has been deleted!".format(shot_to_delete))
    return redirect(redirect_url())


@app.route('/delete-asset/<asset_name>', methods=['POST'])
def delete_asset(asset_name):
    asset_to_delete = request.form['assetName']
    mongo.db.assets.delete_one({"name": asset_to_delete})
    print("asset {} has been deleted!".format(asset_to_delete))
    return redirect(redirect_url())


@app.route('/remove-show/<show_name>', methods=['POST'])
def remove_show(show_name):
    show_to_delete = request.form['showName']
    mongo.db.shows.delete_one({"name": show_to_delete})
    mongo.db.seqs.delete_many({"show": show_to_delete})
    mongo.db.shots.delete_many({"show": show_to_delete})
    mongo.db.submissions.delete_many({"Show": show_to_delete})
    mongo.db.assets.delete_many({"show": show_to_delete})
    return redirect(redirect_url())


@app.route('/remove-seq/<seq_name>', methods=['POST'])
def remove_seq(seq_name):
    seq_to_delete = request.form['seqName']
    show = request.form['showName']
    mongo.db.shows.update({"name": show}, {"$pull": {"sequences": {"name": seq_name}}})
    mongo.db.seqs.delete_one({"name": seq_to_delete})
    mongo.db.shots.delete_many({"seq": seq_name})
    print("Seq {} has been deleted!".format(seq_to_delete))
    return redirect(redirect_url())


@app.route('/remove-user/<user_name>', methods=['POST'])
def remove_user(user_name):
    user_to_delete = request.form['userName']
    mongo.db.users.delete_one({"name": user_to_delete})
    shots = [x for x in mongo.db.shots.find()]
    for shot in shots:
        mongo.db.shots.update({"name": shot.get("name")}, {"$pull": {"tasks": {"assignee": user_name}}})

    return redirect(redirect_url())


@app.route('/remove-sub/<ptuid>', methods=['POST'])
def remove_sub(ptuid):
    sub_to_delete = request.form['ptuid']
    mongo.db.submissions.delete_one({"ptuid": sub_to_delete})
    return redirect(redirect_url())


@app.route('/create-show', methods=['POST'])
def create_show():
    show_name = request.form['show-name']
    show_longname = request.form['show-longname']
    dba.create_show(show_longname, show_name)
    print("show_name: {}, show_long_name: {}".format(show_name, show_longname))
    return redirect(redirect_url())


@app.route('/create-seq', methods=['POST'])
def create_seq():
    show_name = request.form['show']
    seq_name = request.form['seq-name']
    print(show_name, seq_name)
    dba.create_seq(show_name, seq_name)
    return redirect(redirect_url())


@app.route('/create-shot', methods=['POST'])
def create_shot():
    show_name = request.form['show']
    seq_name = request.form['seq']
    shot_name = request.form['shot-name']
    frame_in = request.form['frame-in']
    frame_out = request.form['frame-out']
    target_date = request.form['date']
    iso_target_date = utils.convert_datepicker_to_isotime(target_date)
    dba.create_shot(show_name, seq_name, shot_name, frame_in=frame_in, frame_out=frame_out, target_date=iso_target_date)
    return redirect(redirect_url())


@app.route('/create-asset', methods=['POST'])
def create_asset():
    show_name = request.form['show']
    asset_name = request.form['asset-name']
    hero_type = request.form['asset-hero-type']
    if hero_type == "Hero":
        hero = True
    else:
        hero = False
    asset_type = request.form['asset-type']
    target_date = request.form['date-create-asset']
    iso_target_date = utils.convert_datepicker_to_isotime(target_date)
    dba.create_asset(show_name, asset_name, asset_type, hero, iso_target_date)
    print(show_name, asset_name, hero, asset_type, iso_target_date)
    return redirect(redirect_url())


@app.route('/create-xls', methods=['GET', 'POST'])
def create_xls():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            print("sorry sorry lah")
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            print("no file at filename")
            return redirect(request.url)
        if file and allowed_xls_file(file.filename):
            filename = secure_filename(file.filename)
            file_full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_full_path)
            print(file_full_path)
            Xls = utils.Xls_to_mongodb(file_full_path, mongo.db)
            Xls.populate_all()
            os.remove(file_full_path)
            return redirect(redirect_url())
    return redirect(redirect_url())


@app.route("/process/<current_route>/<username>")
def process(current_route, username):
    reset_notification.delay(username)
    return redirect(url_for(current_route))


@app.route("/api/unity/<show>/assets")
def fetch_asset_api(show):
    assets_db = [x for x in mongo.db.assets.find() if x.get('show') == show]
    publish_db = [x for x in mongo.db.publish.find() if x.get('entity') == "asset"]
    name = request.args.get('name')
    published = request.args.get('published')
    tag = request.args.get('tag')
    task = request.args.get('task')
    version = request.args.get('version')
    latest_pub_list = []


    # published all
    if published == "all" and task is None and tag is None and name is None and version is None:
        for pub in publish_db:
            searchObj = re.search(r"%s" % show, pub.get('UUID'), re.M | re.I)
            if searchObj:
                latest_pub_list.append(pub)

    # published all, name
    if published == "all" and task is None and tag is None and name is not None and version is None:
        for pub in publish_db:
            searchObj = re.search(r"%s" % name, pub.get('UUID'), re.M | re.I)
            if searchObj:
                latest_pub_list.append(pub)

    # published all, version
    if published == "all" and task is None and tag is None and name is None and version is not None:
        for pub in publish_db:
            if pub.get('version') == float(version):
                latest_pub_list.append(pub)

    # published all, task
    if published == "all" and task is not None and tag is None and name is None and version is None:
        for pub in publish_db:
            uuid_obj = utils.UUID(pub.get('UUID'), "asset")
            if uuid_obj.task() == task:
                latest_pub_list.append(pub)

    # published latest, tag
    if published == "latest" and tag is not None and name is None and version is None and task is None:
        uuids = utils.get_uuids("latest", assets_db)
        for pub in publish_db:
            for uuid in uuids:
                if pub.get("UUID") == uuid:
                    for t in pub.get("tag"):
                        if t == tag:
                            latest_pub_list.append(pub)

    # published not_latest, tag
    if published == "not_latest" and tag is not None and name is None and version is None and task is None:
        uuids = utils.get_uuids("previous", assets_db)
        for pub in publish_db:
            for uuid in uuids:
                if pub.get("UUID") == uuid:
                    for t in pub.get("tag"):
                        if t == tag:
                            latest_pub_list.append(pub)

    # published latest, task
    if published == "latest" and task is not None and tag is None and name is None and version is None:
        task_list = []
        uuids = utils.get_uuids("latest", assets_db)
        for uuid in uuids:
            uuid_obj = utils.UUID(uuid, "asset")
            if uuid_obj.task() == task:
                task_list.append(uuid)
        for pub in publish_db:
            for uuid in task_list:
                if pub.get('UUID') == uuid:
                    latest_pub_list.append(pub)

    # published not_latest, task
    if published == "not_latest" and task is not None and tag is None and name is None and version is None:
        task_list = []
        uuids = utils.get_uuids("previous", assets_db)
        for uuid in uuids:
            uuid_obj = utils.UUID(uuid, "asset")
            if uuid_obj.task() == task:
                task_list.append(uuid)
        for pub in publish_db:
            for uuid in task_list:
                if pub.get('UUID') == uuid:
                    latest_pub_list.append(pub)

    pub_uuid_list_not_latest_all = []
    pub_uuid_list_not_latest_name = []
    pub_uuid_list_not_latest_version = []
    pub_uuid_list_not_latest_name_version = []

    for asset in assets_db:

        # published latest
        if published == "latest" and task is None and tag is None and name is None and version is None:
            for x in utils.find("latest", asset):
                for pub in publish_db:
                    if pub.get('UUID') == x:
                        latest_pub_list.append(pub)

        # published latest, name
        if published == "latest" and task is None and tag is None and name is not None and version is None:
            if asset.get('name') == name:
                for x in utils.find("latest", asset):
                    for pub in publish_db:
                        if pub.get('UUID') == x:
                            latest_pub_list.append(pub)

        # published not_latest
        if published == "not_latest" and task is None and tag is None and name is None and version is None:
            for x in utils.find("previous", asset):
                if not isinstance(x, list):
                    pub_uuid_list_not_latest_all.append(x)
                else:
                    for y in x:
                        pub_uuid_list_not_latest_all.append(y)

        # published not_latest, name
        if published == "not_latest" and task is None and tag is None and name is not None and version is None:
            if asset.get('name') == name:
                for x in utils.find("previous", asset):
                    if not isinstance(x, list):
                        pub_uuid_list_not_latest_name.append(x)
                    else:
                        for y in x:
                            pub_uuid_list_not_latest_name.append(y)

        # published not_latest, version
        if published == "not_latest" and task is None and tag is None and name is None and version is not None:
            for x in utils.find("previous", asset):
                if not isinstance(x, list):
                    pub_uuid_list_not_latest_version.append(x)
                else:
                    for y in x:
                        pub_uuid_list_not_latest_version.append(y)

        # published not_latest, name, version
        if published == "not_latest" and task is None and tag is None and name is not None and version is not None:
            if asset.get('name') == name:
                for x in utils.find("previous", asset):
                    if not isinstance(x, list):
                        pub_uuid_list_not_latest_name_version.append(x)
                    else:
                        for y in x:
                            pub_uuid_list_not_latest_name_version.append(y)

    if pub_uuid_list_not_latest_all != []:
        for pub in publish_db:
            for uuid in pub_uuid_list_not_latest_all:
                if pub.get('UUID') == uuid:
                    latest_pub_list.append(pub)

    if pub_uuid_list_not_latest_name != []:
        for pub in publish_db:
            for uuid in pub_uuid_list_not_latest_name:
                if pub.get('UUID') == uuid:
                    latest_pub_list.append(pub)

    if pub_uuid_list_not_latest_version != []:
        for pub in publish_db:
            for uuid in pub_uuid_list_not_latest_version:
                if pub.get('UUID') == uuid:
                    if pub.get('version') == float(version):
                        latest_pub_list.append(pub)

    if pub_uuid_list_not_latest_name_version != []:
        for pub in publish_db:
            for uuid in pub_uuid_list_not_latest_name_version:
                if pub.get('UUID') == uuid:
                    if pub.get('version') == float(version):
                        latest_pub_list.append(pub)

    if latest_pub_list != []:
        return Response(json_util.dumps(latest_pub_list, indent=4), mimetype='application/json')
    else:
        return Response(json_util.dumps("Not matching... Sorry.", indent=4), mimetype='application/json')


@app.route("/api/unity/<show_name>/<shot_name>")
def fetch_shot_api(show_name, shot_name):
    published = request.args.get('published')
    tag = request.args.get('tag')
    task = request.args.get('task')
    version = request.args.get('version')
    name = request.args.get('name')

    shot_entity = mongo.db.shots.find_one({"name": shot_name})
    published_db = [x for x in mongo.db.publish.find()if x.get('entity') == "shot"]
    latest_uuids = utils.get_uuids("latest", shot_entity)
    not_latest_uuids = utils.get_uuids("previous", shot_entity)
    all_uuids = latest_uuids + not_latest_uuids
    pub_list = []

    # latest
    if published == "latest" and tag is None and task is None and version is None and name is None:
        for pub in published_db:
            for uuid in latest_uuids:
                if pub.get('UUID') == uuid:
                    pub_list.append(pub)

    # all
    if published == "all" and tag is None and task is None and version is None and name is None:
        for pub in published_db:
            for uuid in all_uuids:
                if pub.get("UUID") == uuid:
                    pub_list.append(pub)

    # not latest
    if published == "not_latest" and tag is None and task is None and version is None and name is None:
        for pub in published_db:
            for uuid in not_latest_uuids:
                if pub.get('UUID') == uuid:
                    pub_list.append(pub)

    # latest, name
    if published == "latest" and tag is None and task is None and version is None and name is not None:
        for uuid in latest_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.name() == name:
                        pub_list.append(pub)

    # latest, version
    if published == "latest" and tag is None and task is None and version is not None and name is None:
        for uuid in latest_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.version() == version:
                        pub_list.append(pub)

    # latest, task
    if published == "latest" and tag is None and task is not None and version is None and name is None:
        for uuid in latest_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.task() == task:
                        pub_list.append(pub)

    # not latest, version, name
    if published == "not_latest" and tag is None and task is None and version is not None and name is not None:
        for uuid in not_latest_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.version() == version:
                        if uuid_obj.name() == name:
                            pub_list.append(pub)

    # latest, version, name
    if published == "latest" and tag is None and task is None and version is not None and name is not None:
        for uuid in latest_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.version() == version:
                        if uuid_obj.name() == name:
                            pub_list.append(pub)

    # not latest, name
    if published == "not_latest" and tag is None and task is None and version is None and name is not None:
        for uuid in not_latest_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.name() == name:
                        pub_list.append(pub)

    # not latest, task
    if published == "not_latest" and tag is None and task is not None and version is None and name is None:
        for uuid in not_latest_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.task() == task:
                        pub_list.append(pub)


    # not latest, version
    if published == "not_latest" and tag is None and task is None and version is not None and name is None:
        for uuid in not_latest_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.version() == version:
                        pub_list.append(pub)

    # latest, task, version, name
    if published == "latest" and tag is None and task is not None and version is not None and name is not None:
        for uuid in latest_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.version() == version:
                        if uuid_obj.name() == name:
                            if uuid_obj.task() == task:
                                pub_list.append(pub)

    # not latest, task, version, name
    if published == "not_latest" and tag is None and task is not None and version is not None and name is not None:
        for uuid in not_latest_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.version() == version:
                        if uuid_obj.name() == name:
                            if uuid_obj.task() == task:
                                pub_list.append(pub)

    # all, name
    if published == "all" and tag is None and task is None and version is None and name is not None:
        for uuid in all_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.name() == name:
                        pub_list.append(pub)

    # all, version
    if published == "all" and tag is None and task is None and version is not None and name is None:
        for uuid in all_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.version() == version:
                        pub_list.append(pub)

    # all, task
    if published == "all" and tag is None and task is not None and version is None and name is None:
        for uuid in all_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.task() == task:
                        pub_list.append(pub)

    # all, tag
    if published == "all" and tag is not None and task is None and version is None and name is None:
        for uuid in all_uuids:
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    for t in pub.get('tag'):
                        if tag == t:
                            pub_list.append(pub)

    # all, tag, version
    if published == "all" and tag is not None and task is None and version is not None and name is None:
        for uuid in all_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    for t in pub.get('tag'):
                        if tag == t:
                            if uuid_obj.version() == version:
                                pub_list.append(pub)

    # all, tag, version
    if published == "all" and tag is not None and task is None and version is not None and name is None:
        for uuid in all_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    for t in pub.get('tag'):
                        if tag == t:
                            if uuid_obj.version() == version:
                                pub_list.append(pub)

    # all, tag, task
    if published == "all" and tag is not None and task is not None and version is None and name is None:
        for uuid in all_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    for t in pub.get('tag'):
                        if tag == t:
                            if uuid_obj.task() == task:
                                pub_list.append(pub)

    # all, task, version
    if published == "all" and tag is None and task is not None and version is not None and name is None:
        for uuid in all_uuids:
            uuid_obj = utils.UUID(uuid, "shot")
            for pub in published_db:
                if pub.get('UUID') == uuid:
                    if uuid_obj.task() == task:
                        if uuid_obj.version() == version:
                            pub_list.append(pub)


    if pub_list != []:
        return Response(json_util.dumps(pub_list, indent=4), mimetype='application/json')
    else:
        return Response(json_util.dumps("Couldn't get your request. Sorry.", indent=4), mimetype='application/json')


if __name__ == "__main__":
    app.secret_key = cfg.FLASK_APP_SECRET_KEY
    app.run(debug=True, host="0.0.0.0", extra_files=dirs_to_watch("templates"))
