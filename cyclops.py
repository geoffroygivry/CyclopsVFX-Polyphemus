from flask import Flask, render_template
from flask_pymongo import PyMongo
import cyc_config as cfg

app = Flask(__name__)
app.config['MONGO_DBNAME'] = 'hydra'
app.config['MONGO_URI'] = cfg.MONGODB

mongo = PyMongo(app)


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/polyphemus')
def polyphemus():
    subs = [x for x in mongo.db.dailies_submissions.find()]
    return render_template("polyphemus.html", subs=subs)


if __name__ == "__main__":
    app.run(debug=True)
