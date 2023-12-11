from flask import Flask, render_template, redirect, session, flash, url_for
from flask_debugtoolbar import DebugToolbarExtension
from models import connect_db, db, User, Feedback
from forms import RegisterForm, LoginForm, FeedbackForm, DeleteForm
from flask_migrate import Migrate
from werkzeug.exceptions import Unauthorized


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///auth_exercise"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = "abc123"

connect_db(app)
# db.create_all()
# To make changes to model without having to drop tables
migrate = Migrate(app, db)

toolbar = DebugToolbarExtension(app)
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False


@app.route("/")
def home():
    """Show homepage that redirects register route"""
    return redirect("/register")


@app.route("/register",  methods=['GET', 'POST'])
def register():
    """Register user: produce form & handle form submission."""

    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        email = form.email.data

        new_user = User.register(username=username, pwd=password,
                          first_name=first_name, last_name=last_name, email=email)
        db.session.add(new_user)
        db.session.commit()
        session['username'] = new_user.username
        return redirect(url_for('user_profile', username=new_user.username))
    else:
        return render_template('register.html', form=form)

@app.route("/login",  methods=['GET', 'POST'])
def login():
    """Log in user: produce form & handle form submission."""

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.authenticate(username, password)
        if user:
            flash(f"Welcome Back, {user.username}!", "primary")
            session['username'] = user.username
            return redirect(url_for('user_profile', username=user.username))
        else:
            form.username.errors = ['Invalid username.']
            form.password.errors = ['Invalid password.']

    return render_template('login.html', form=form)

@app.route('/users/<username>')
def user_profile(username):
    # Using both conditions in "or" statement ensures:
    # A user must be logged in to access any profile page.
    # The logged-in user can only access their own profile page and not that of another user.
    if "username" not in session or username != session['username']:
        flash("You must be logged in to view this page.", "warning")
        raise Unauthorized()

    user = User.query.get_or_404(username)
    feedbacks = Feedback.query.filter_by(username=username).all()
    form = DeleteForm()


    return render_template('user_profile.html', user=user, feedbacks=feedbacks, form=form)

@app.route('/users/<username>/delete', methods=['POST'])
def delete_user(username):
    if 'username' not in session or username != session['username']:
        flash("You are not authorized to do this action.", "warning")
        raise Unauthorized()

    user = User.query.get_or_404(username)
    # Feedback.query.filter_by(username=username).delete()
    db.session.delete(user)
    db.session.commit()
    session.pop('username', None)
    flash("User and all feedback deleted.", "info")
    return redirect('/login')    

@app.route('/users/<username>/feedback/add', methods=['GET', 'POST'])
def add_feedback(username):
    if 'username' not in session or username != session['username']:
        flash("You must be logged in to view this page.", "warning")
        raise Unauthorized()

    form = FeedbackForm()

    if form.validate_on_submit():
        feedback = Feedback(title=form.title.data, content=form.content.data, username=username)
        db.session.add(feedback)
        db.session.commit()
        return redirect(f"/users/{feedback.username}")

    else:
        return render_template('feedback/add.html', form=form)


@app.route('/feedback/<int:feedback_id>/update', methods=['GET', 'POST'])
def update_feedback(feedback_id):
    feedback = Feedback.query.get_or_404(feedback_id)
    if 'username' not in session or feedback.username != session['username']:
        flash("You are not authorized to do this action.", "warning")
        return redirect('/login')

    form = FeedbackForm(obj=feedback)
    if form.validate_on_submit():
        feedback.title = form.title.data
        feedback.content = form.content.data
        db.session.commit()
        return redirect(f'/users/{feedback.username}')

    return render_template('feedback/edit.html', form=form, feedback=feedback)

@app.route('/feedback/<int:feedback_id>/delete', methods=['POST'])
def delete_feedback(feedback_id):
    feedback = Feedback.query.get_or_404(feedback_id)
    if 'username' not in session or feedback.username != session['username']:
        flash("You are not authorized to do this action.", "warning")
        return redirect('/login')

    db.session.delete(feedback)
    db.session.commit()
    return redirect(f'/users/{feedback.username}')


@app.route('/logout')
def logout_user():
    session.pop('username')
    flash("Goodbye!", "info")
    return redirect('/login')

