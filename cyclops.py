import os
from flask import Flask, render_template, url_for, request, session, redirect, Response
from flask_pymongo import PyMongo
from flask_gravatar import Gravatar
from datetime import datetime
from scripts import utils
from scripts.flask_celery import make_celery
from scripts import aws_s3
from scripts import generate_images
from scripts import admin as ad
from scripts import check_img as ci
from scripts.forms import ShotForm
import bcrypt, json, uuid, re
from bson.objectid import ObjectId

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
        side_lib = mongo.db.libraries.find()
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

        return render_template("polyphemus.html", side_lib=side_lib, subs=subs, user_session=user_session, shows=shows, show_infos=show_infos, shots=username_shotList, target_shots=target_shots, todolist=todolist, iso_time=iso_time, notifications=notifications, current_route=current_route)
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
            #lets go!
            name = mongo.db.users.find_one({"name": session['username']})

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
        return render_template("user.html", user_name=user_name, subs=subs, user_session=user_session, notifications=notifications, shows=shows, shots=shots)
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
            iso_time = datetime.utcnow()
            side_lib = mongo.db.libraries.find()
            return render_template("admin.html", user_session=user_session, shows=shows, subs=subs, side_lib=side_lib,
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
    mongo.db.shots.delete_one({"name": shot_to_delete})
    print("Shot {} has been deleted!".format(shot_to_delete))
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


@app.route("/process/<current_route>/<username>")
def process(current_route, username):
    reset_notification.delay(username)
    return redirect(url_for(current_route))

@app.route('/asset/<asset_id>')
def asset_view(asset_id):
    if 'username' in session:
        user_session = mongo.db.users.find_one({"name": session['username']})
        asset_details = mongo.db.assets.find_one({'_id': ObjectId(asset_id)})
        asigns = [x for x in  asset_details]
        colabs = asset_details.get('tasks')
        cols = colabs
        side_lib = mongo.db.libraries.find()
        libs = asset_details.get('in_library')
        tages = asset_details.get('tagz')
        tagz = re.split("[, \-!?._:/*#$%&]+", str(tages))
        filevers = [x for x in asset_details.get('version')]
        current_filever  = asset_details.get('current_version')
        pathtofile = asset_details.get('path')
        asset_bundle = "AB_asetbudle_name_created_by_function.zip"
        #progress WIP asset_details.tasks.0.status
        progstat = "Being worked on"
        overall_progress = progstat

    return render_template("asset.html", side_lib=side_lib, asset_bundle=asset_bundle, libs=libs, current_filever=current_filever, cols=cols, colabs=colabs,tagz=tagz, pathtofile=pathtofile, filevers=filevers, overall_progress=overall_progress, user_session=user_session, asset_details=asset_details, asset_view=asset_view)

@app.route('/preview/<asset_id>')
def preview(asset_id):
    if 'username' in session:
        user_session = mongo.db.users.find_one({"name": session['username']})
        asset_details = mongo.db.assets.find_one({'_id': ObjectId(asset_id)})
        side_lib = mongo.db.libraries.find()
        tages = "model_house/3d-walls*details#wall$piece mounted whitespace"
        tagz = re.split("[, \-!?._:/*#$%&]+", tages)

    return render_template("preview.html", user_session=user_session, asset_details=asset_details, side_lib=side_lib, tagz=tagz)

@app.route('/assets/')
def assets_view():
    if 'username' in session:
        user_session = mongo.db.users.find_one({"name": session['username']})
        assets = [x for x in mongo.db.assets.find()]
        side_lib = mongo.db.libraries.find()
        tages = "RGBA-model_house/3d-walls*details#wall$piece mounted whitespace"
        tagz = re.split("[, \-!?_:/.*#$%&]+", tages)

    return render_template("assets.html", side_lib=side_lib, tagz=tagz, assets=assets, user_session=user_session)

@app.route('/libraries/')
def libraries():
    if 'username' in session:
        user_session = mongo.db.users.find_one({"name": session['username']})
        system_libs = mongo.db.libraries.find()
        user_lib =  mongo.db.libraries.find()
        lib_list = [x for x in mongo.db.libraries.find()]
        
    return render_template("library.html", lib_list=lib_list, user_lib=user_lib, system_libs=system_libs, user_session=user_session)

@app.route('/libraries/<lib_name>')
def libraries_view(lib_name):
    if 'username' in session:
        user_session = mongo.db.users.find_one({"name": session['username']})
        get_lib = mongo.db.libraries.find_one({"lib_name": lib_name})
        side_lib = mongo.db.libraries.find()
        filtered_assets = [x for x in mongo.db.assets.find({ "in_library":  lib_name })]

    return render_template("libraries.html", get_lib=get_lib, lib_name=lib_name, filtered_assets=filtered_assets, side_lib=side_lib, user_session=user_session)

def library_edit(lib_name):
    return

def library_add_asset(lib_name, asset):
    return

@app.route('/libraries/create/', methods=['GET', 'POST'])
def library_create():
    """ Creation of a lib entity.
        We have many inputs to get to fill the library mongo entry.
        creator can be system if its autogenerated.
        coments and tags are optional.
    """
    lib_creator = session['username']
    lib_name = request.form['library-name']
    lib_comment = 'No entered comments.'
    lib_date = datetime.utcnow()
    lib_timestamp = datetime.utcnow()
    lib_created = datetime.utcnow()
    lib_changed = datetime.utcnow()
    lib_uid = uuid.uuid4().hex
    lib_tags = 'Empty library'
    mongo.db.libraries.insert(
        {
            "lib_name" : lib_name,
            "lib_created_by" : lib_creator,
            "lib_created" : lib_created,
            "lib_changed" : lib_changed,
            "timestamp" : lib_timestamp,
            "comment" : lib_comment,
            "thumbnail_s3" : "https://s3.amazonaws.com/cyclopsvfx/.MANOR_010_v001_comp.thumbnail.jpg",
            "lib_uid" : lib_uid,
            "tags" : [ 
            lib_tags
            ],
            "lib_favs" : 0
        }
    )
    return json.dumps({'status':'OK','Library created:':lib_name});



@app.route('/lib_add_fav/<lib_name>', methods=['GET', 'POST']) 
def lib_add_fav(lib_name):
    get_lib = mongo.db.libraries.find_one({"lib_name": lib_name})
    favs_num = get_lib.get('lib_favs')
    favs_num = favs_num+1
    print(favs_num, get_lib)
    mongo.db.libraries.update({"lib_name": lib_name},
                                  {"$set": {"lib_favs": favs_num}})
    # do db stuff jsonify

    return json.dumps({'status':'OK','library':lib_name,'favs':favs_num});

@app.route('/asset_add_fav/<asset_id>') 
def asset_add_fav(asset_id):
    get_asset = mongo.db.assets.find_one({'_id': ObjectId(asset_id)})
    favs_num = get_asset.get('favs')
    favs_num = favs_num+1
    print(favs_num, get_asset)
    mongo.db.assets.update({'_id': ObjectId(asset_id)},
                                  {"$set": {"favs": favs_num}})
    # do db stuff
    return json.dumps({'status':'OK','asset':asset_id,'favs':favs_num});

@app.route('/3D/<model_id>')
def model(model_id):
    texture_name = "/static/polyphemus/assets/img/cyc_placeholder.png"
    base_file_path = "/static/polyphemus/data/3D/poly/"
    model_file = "poly.obj"
    material_file = "poly.mtl"
    return render_template('type-model.html', base_file_path=base_file_path, texture_name=texture_name, model_id=model_id, model_file=model_file, material_file=material_file)

@app.route('/2D/<model_id>')
def texture(model_id):
    tex_name = "Random Tex name"
    texture_name = "/static/polyphemus/assets/img/rubishboy.jpg"
    base_file_path = "/static/polyphemus/data/3D/poly/"
    details = ["RGBA", "roto", "mask with alpha"]
    tages = "RGBA-model_house/3d-walls*details#wall$piece mounted whitespace"
    tagz = re.split("[, \-!?_:/.*#$%&]+", tages)
    return render_template('type-texture.html', details=details, tagz=tagz, tex_name=tex_name, texture_name=texture_name, base_file_path=base_file_path)

@app.route('/video/<video_id>')
def video(video_id):
    video_file = "/static/polyphemus/data/video/video.mp4"
    video_poster_frame = "/static/polyphemus/data/video/poster.jpg"
    video_name = "test_video_name"
    return render_template('type-video.html', video_file=video_file, video_poster_frame=video_poster_frame, video_name=video_name, video_id=video_id)

@app.route('/sound/<sound_id>')
def sound(sound_id):
    sound_file = "/static/polyphemus/data/sounds/sound.mp3"
    sound_name = "test sound name"
    return render_template('type-sound.html', sound_file=sound_file, sound_name=sound_name, sound_id=sound_id)


@app.route('/camera/<model_id>')
def camera(model_id):
    model_file = "sphere.obj"
    texture_name = "/TMP/Folder.jpg"
    return render_template('type-camera.html', texture_name=texture_name, model_id=model_id)

@app.route('/texture/<texture_id>')
def textures(texture_id):
    texture_file = "/static/polyphemus/data/video/poster.jpg"
    texture_name = "Folder"
    return render_template('type-texture.html', texture_name=texture_name, texture_id=texture_id, texture_file=texture_file)


@app.route('/documments/<document_id>')
def documents(document_id):
    document_file = "word.docx"
    document_name = "Big Word File"
    return render_template('type-document.html', document_name=document_name, document_id=document_id, document_file=document_file)



if __name__ == "__main__":
    app.secret_key = cfg.FLASK_APP_SECRET_KEY
    app.run(debug=True, host="0.0.0.0")
