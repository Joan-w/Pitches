import os
import secrets
# from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from pitches import app, db, bcrypt, mail
from pitches.forms import (SignupForm, LoginForm, UpdateAccountForm,
                            PitchForm, RequestResetForm, ResetPasswordForm)
from pitches.models import User, Pitch
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message


@app.route('/')
@app.route('/home')
def home():
    page = request.args.get('page', 1, type=int)
    pitches = Pitch.query.order_by(Pitch.date_posted.desc()).paginate(page=page, per_page=3)
    return render_template('home.html', pitches=pitches)

@app.route('/about')
def about():
    return render_template('about.html', title = 'About Page')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = SignupForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been successfully created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html', title='Sign Up', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        flash('Login Unsuccessful. Please check your email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', 'picture_fn')
    form_picture.save(picture_path)

    return picture_fn

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                          image_file=image_file, form=form)

            
# @app.route('/pitch/new', methods=['GET', 'POST'])
# @login_required
# def new_pitch():
#     form = PitchForm()
#     if form.validate_on_submit:
#         flash('Your post has been created!', 'success')
#         return redirect(url_for('home'))
#     return render_template('create_pitch.html', title='New Pitch', form=form)

# @app.route('/pitch/new', methods=['GET', 'POST'])
# @login_required
# def new_pitch():
#     form = PitchForm()
#     # if form.validate_on_submit:
#     #     flash('Your post has been created!', 'success')
#     #     return redirect(url_for('home'))
#     return render_template('create_pitch.html', title='New Pitch', form=form)


@app.route("/pitch/new", methods=['GET', 'POST'])
@login_required
def new_pitch():
    form = PitchForm()
    if form.validate_on_submit():
        pitch = Pitch(category=form.category.data, content=form.content.data, author=current_user)
        db.session.add(pitch)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_pitch.html', title='New Pitch',
                            form=form, legend='Update Pitch')

@app.route("/pitch/<int:pitch_id>")
def pitch(pitch_id):
    pitch = Pitch.query.get_or_404(pitch_id)
    return render_template('pitch.html', title =pitch.category, pitch=pitch)

@app.route("/pitch/<int:pitch_id>/update", methods=['GET', 'POST'])
@login_required
def update_pitch(pitch_id):
    pitch = Pitch.query.get_or_404(pitch_id)
    if pitch.author != current_user:
        abort(403)
    form = PitchForm()
    if form.validate_on_submit():
        pitch.category = form.category.data
        pitch.content = form.content.data
        db.session.commit()
        flash('Your pitch has been updated!', 'success')
        return redirect(url_for('pitch', pitch_id=pitch.id))
    elif request.method == 'GET':        
        form.category.data = pitch.category
        form.content.data = pitch.content
    return render_template('create_pitch.html', title='New Pitch',
                            form=form, legend='Update Pitch')

@app.route("/pitch/<int:pitch_id>/delete", methods=['POST'])
@login_required
def delete_pitch(pitch_id):
    pitch = Pitch.query.get_or_404(pitch_id)
    if pitch.author != current_user:
        abort(403)
    db.session.delete(pitch)
    db.session.commit()
    flash('Your pitch has been deleted!', 'success')
    return redirect(url_for('home'))

@app.route("/user/<string:username>")
def user_pitches(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    pitches = Pitch.query.filter_by(author=user)\
        .order_by(Pitch.date_posted.desc())\
        .paginate(page=page, per_page=5)
    return render_template('user_pitches.html', pitches=pitches, user=user)

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                    sender='noreply@demo.com',
                    recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}    

If you did not make this request then simply ignore this email and no changes will be made.
'''

@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions on how to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)        