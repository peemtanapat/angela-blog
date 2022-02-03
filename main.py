from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar


def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id = current_user.id
        if user_id != 1:
            print('You are not admin!!!')
            return render_template('forbidden.html')
        return func(*args, **kwargs)
    return wrapper


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

##AUTHENTICATION
login_manager = LoginManager()
login_manager.init_app(app)

##Gravatar
gravatar = Gravatar(
    app,
    size=100,
    rating='g',
    default='retro',
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None
)

##CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    # author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    def to_dict(self):
        dictionary: dict = {}
        for col in self.__table__.columns:
            dictionary[col.name] = getattr(self, col.name)
        return dictionary


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000), unique=True)

    def to_dict(self):
        dictionary: dict = {}
        for col in self.__table__.columns:
            dictionary[col.name] = getattr(self, col.name)
        return dictionary


class Comment(UserMixin, db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def to_dict(self):
        dictionary: dict = {}
        for col in self.__table__.columns:
            dictionary[col.name] = getattr(self, col.name)
        return dictionary


db.create_all()


posts: list = []
current_username: str = None


def fetch_posts():
    posts.clear()
    # all_posts = db.session.query(BlogPost, Comment, User)\
    all_posts = db.session.query(BlogPost, User)\
            .filter(User.id == BlogPost.author_id)\
            .all()
            # .filter(BlogPost.id == Comment.post_id)\
            # .join(User)\
            # .add_columns(BlogPost.id, User.name)\
            # .filter(BlogPost)
    # print(len(all_posts), all_posts)
    # print(all_posts)
    # for post, comment, user in all_posts:
    for post, user in all_posts:
        post = post.to_dict()
        # comment = comment.to_dict()
        user = user.to_dict()
        # print(post, '\n', comment, '\n', user, '\n')
        post['author'] = user['name']
        posts.append(post)
    print(len(posts), posts)


@app.route('/')
def get_all_posts():
    fetch_posts()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if request.method == 'GET':
        return render_template("register.html", form=form)
    else:
        email_inp = form.email.data
        name_inp = form.name.data
        found_user = User.query.filter(User.email == email_inp).first()
        if bool(found_user):
            flash('Duplicated email')
            return redirect(url_for('register'))
        new_user = User(
            email=email_inp,
            password=form.password.data,
            name=name_inp
        )
        print('new_user', new_user)
        try:
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            print('e', e)
            flash(str(e))
            return redirect(url_for('register'))
        login_user(new_user)
        return redirect(url_for('get_all_posts'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email_inp = form.email.data
        password_inp = form.password.data
        found_user = User.query.filter(User.email == email_inp).first()
        print('found_user', found_user)
        if found_user is None:
            flash('Not found email')
            return redirect(url_for('login'))
        found_user_dict = found_user.to_dict()
        if password_inp != found_user_dict['password']:
            flash('Password invalid')
            return redirect(url_for('login'))
        login_user(found_user)
        return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


def get_post(post_id: int, for_db: bool):
    requested_post = BlogPost.query.get(post_id)
    if requested_post is None:
        return render_template('not_found.html')
    user = User.query.get(requested_post.to_dict()['author_id'])
    if for_db:
        return requested_post
    requested_post = requested_post.to_dict()
    requested_post['author'] = user.to_dict()['name']
    return requested_post


def get_comments_by_post_id(post_id: int):
    comment_show: list = []
    comments = db.session.query(Comment, User)\
                .filter(Comment.post_id == post_id)\
                .filter(Comment.user_id == User.id)\
                .all()
    for comment, user in comments:
        print('Here...\n', comment.to_dict(), '\n', user.to_dict(), '\n.........')
        comment = comment.to_dict()
        user = user.to_dict()
        comment['author'] = user['name']
        comment['email'] = user['email']
        comment_show.append(comment)
    # comments = Comment.query.filter(Comment.post_id == post_id).all()
    # print(comments)
    return comment_show


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    print('post_id', post_id)
    comment_form = CommentForm()
    requested_post = get_post(post_id, for_db=False)
    comments_of_post = get_comments_by_post_id(post_id)
    return render_template("post.html",
                           post=requested_post,
                           comment_form=comment_form,
                           comments=comments_of_post,
                           user=current_user,
                           gravatar=gravatar,
                           logged_in=current_user.is_authenticated)


@app.route("/comment/<int:post_id>", methods=['POST'])
@login_required
def comment(post_id):
    print('comment!!!')
    form = CommentForm()
    new_comment = Comment(
        text=form.text.data,
        post_id=post_id,
        user_id=current_user.id
    )
    db.session.add(new_comment)
    db.session.commit()
    return redirect(url_for('show_post', post_id=get_post(post_id, for_db=False)['id']))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=['GET', 'POST'])
@login_required
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)


@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@login_required
@admin_only
def edit_post(post_id):
    edit_form = CreatePostForm()
    if edit_form.validate_on_submit():
        post = get_post(post_id, for_db=True)
        print(edit_form.title.data)
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author_id = current_user.id
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    post = get_post(post_id, for_db=False)
    edit_form = CreatePostForm(
        title=post['title'],
        subtitle=post['subtitle'],
        img_url=post['img_url'],
        author=post['author'],
        body=post['body']
    )
    return render_template("make-post.html", form=edit_form, post=post, logged_in=current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
@login_required
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


if __name__ == "__main__":
    app.run(port=5555, debug=True)
