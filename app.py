from flask import Flask, render_template, request, flash, redirect, url_for, session ,send_file
from functools import wraps
from flask_session import Session
from wtforms import Form, StringField, PasswordField, validators
from flask_mail import Mail, Message
from random import randint
import time
import datetime
import pyrebase
import hashlib
import os
from PIL import Image
from pytube import YouTube
import logging
import sys
from io import BytesIO
from tempfile import TemporaryDirectory

with TemporaryDirectory() as tmp:
    print(tmp)
 
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


config = {
  "apiKey": "AIzaSyD8-9NlQnBJoFeLFFlJlXBZYgcn8gKfJ5Q",
  "authDomain": "metaducator-e851a.firebaseapp.com",
  "databaseURL": "https://metaducator-e851a-default-rtdb.firebaseio.com",
  "projectId": "metaducator-e851a",
  "storageBucket": "metaducator-e851a.appspot.com",
  "messagingSenderId": "354577879194",
  "appId": "1:354577879194:web:d99f5148d42ee5e6008f23",
  "measurementId": "G-9ML9940P03"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

app = Flask(__name__)
sess = Session()

app.secret_key = 'ug86ooriuygiy'
app.config['SESSION_TYPE'] = 'filesystem'

sess.init_app(app)

class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirmed', message='Passwords do not match')
    ])
    confirmed = PasswordField('Confirm Password')


class LoginForm(Form):
    email = StringField('Email', [
        validators.DataRequired(),
        validators.Length(min=6, max=50)
    ])
    password = PasswordField('Password', [
        validators.DataRequired()
    ])

###################################################################################################
# General function to check whether someone is logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))

    return wrap


@app.route('/')
def index():
    form = LoginForm(request.form)
    return render_template('login.html', form=form , user=session)


#################################################  login 

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():

        email = form.email.data
        password = hashlib.sha256(str(form.password.data).encode())
        password = password.hexdigest()

        users = db.child("users").get().val()
        user = None
        user_id = None
        for x in users:
            if users[x]['email'].upper() == email.upper() and users[x]['password'] == password:
                user = users[x]
                user_id = x
                print(user)
                break

        if user is None:
            flash('Please check your credentials', 'danger')
            return redirect(url_for('index'))
        else:
            app.logger.info("Welcome")
            session['logged_in'] = True
            session['username'] = user['name']
            session['email'] = user['email']
            session['id'] = user_id
        return redirect(url_for('youtube_downloader'))

    return redirect(url_for('index'))


################################################## signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        email = form.email.data
        name = form.name.data
        password = hashlib.sha256(str(form.password.data).encode())
        password = password.hexdigest()


        data = {
            "name": name,
            "email": email,
            "password": password,
            "my_downloads":""
        }

        db.child("users/").push(data)

        flash('Your Account has been Created Sucessfully', 'success')

        return redirect(url_for('index'))

    return render_template('signup.html', form=form ,user=session)



################################################################ 

@app.route("/home", methods=["GET", "POST"])
@is_logged_in
def youtube_downloader():
    if request.method == "GET":
        return render_template("home.html",user=session)
    else:
        
        if not request.form["URL"]:
            return redirect("/home")
        else:
            URL = request.form["URL"]
            try:
                video = YouTube(URL)
                video.check_availability()
            except:
                flash('Download Fail', 'danger')
                return redirect("/home")

            resolutions = {}
            for stream in video.streams.filter(progressive=True):
                resolutions[stream.resolution] = stream.resolution
                
            return render_template("download.html", resolutions = resolutions, URL = URL ,user=session)

##########################################################################

@app.route("/download_video", methods=["POST"])
@is_logged_in
def download_video():
    if request.method == "POST":
        if not request.form["URL"] or not request.form["resolution"]:
            return redirect("/home")
        try:
            youtube_url = request.form["URL"]
            note = request.form["note"]
            video_type = request.form["type"]
            resolution = request.form["resolution"]
            video_size = (YouTube(youtube_url).streams.get_highest_resolution().filesize)/1000000
            
            data = {
                "youtube_url":youtube_url,
                "resolution":resolution,
                "note":note,
                "video_size":video_size,
                "video_type":video_type
            }

            db.child("users/"+str(session['id'])+"/my_downloads").push(data)

            with TemporaryDirectory() as tmp_dir:
                ##print(tmp_dir)
                download_path = YouTube(youtube_url).streams.filter(res=resolution, progressive=True).first().download(tmp_dir)
                vid_name = download_path.split("\\")[-1]
                file_bytes = b""
                with open(download_path, "rb") as f:
                    file_bytes = f.read()

                return send_file(BytesIO(file_bytes), attachment_filename=vid_name, as_attachment=True)
        except:
            logging.exception("Failed download")
            flash('Download Fail', 'danger')
            return redirect("/home")

################################################################# my download

@app.route("/my_download")
@is_logged_in
def my_download():

    my_downloads = db.child("users/"+str(session['id'])+"/my_downloads").get().val()

    return render_template("my_downloads.html",my_downloads = my_downloads ,user = session)


###################################################################
# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Successfully logged out', 'success')
    return redirect(url_for("login"))






if __name__ == '__main__':
    app.run(debug=True)
