import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from flaskblog import app, db, bcrypt
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, CommentForm, MessageForm
from flaskblog.models import User, Post, Comment, Message
from flask_login import login_user, current_user, logout_user, login_required


@app.route("/")
def cover():
    cover_img = url_for('static', filename='profile_pics/cover.jpg')
    return render_template('cover.html',cover_img=cover_img)

@app.route("/home")
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('home.html', posts=posts)

@app.route("/material")
@login_required
def material():
    return render_template('material.html', title='Material')

@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
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
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    posts_count = len(Post.query.filter_by(user_id=current_user.id).all())
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
    connections = current_user.connections
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form, posts_count=posts_count, connections = connections)


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)

@app.route("/likes/<int:post_id>", methods=['POST', 'GET'])
@login_required
def likes(post_id):
    post = Post.query.get_or_404(post_id) 
    lst = list(map(int,post.liked_users.split()))
    if current_user.id in lst:
        post.likes -= 1
        lst.remove(current_user.id)
        flash('UnLiked!', 'danger')
    else:         
        lst.append(current_user.id)
        post.likes += 1
        flash('Like Done!', 'success')
    lst = list(map(str,lst))
    post.liked_users = " ".join(lst)
    db.session.commit()
    return redirect(url_for('home', post_id=post.id))

@app.route("/comments/<int:post_id>", methods=['POST', 'GET'])
@login_required
def comments(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, user_id=current_user.id, post_id=post_id)
        db.session.add(comment)
        db.session.commit()
        flash('Commented!', 'success')
        return redirect(url_for('comments',post_id=post_id))
    comments = Comment.query.filter_by(post_id=post_id).all()
    return render_template('comments.html', comments=comments,legend='Comments',form=form)

@app.route("/clubs")
def clubs():
    return render_template('clubs.html', title='Clubs')

@app.route("/help_desk")
def help_desk():
    return render_template('help_desk.html', title='Help-Desk')

@app.route("/profile/<string:username>")
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first()
    posts_count = len(Post.query.filter_by(user_id=user.id).all())
    connections = user.connections
    connected_users = user.connected_users
    image_file = url_for('static', filename='profile_pics/' + user.image_file)
    current_lst = list(map(int,current_user.connected_users.split()))
    if user.id in current_lst:
        is_connected = True
    else:
        is_connected = False
    return render_template('profile.html', user=user, image_file=image_file, posts_count=posts_count, connections = connections, connected_users= connected_users, is_connected=is_connected)

@app.route("/connections/<int:user_id>")
@login_required
def connections(user_id):
    user = User.query.get_or_404(user_id)
    lst = list(map(int,user.connected_users.split()))
    current_lst = list(map(int,current_user.connected_users.split()))
    if current_user.id in lst:
        user.connections -=1
        current_user.connections -=1
        lst.remove(current_user.id)
        current_lst.remove(user.id)
    else:
        user.connections +=1
        current_user.connections +=1
        lst.append(current_user.id)
        current_lst.append(user.id)
    lst = list(map(str,lst))
    current_lst=list(map(str,current_lst))
    user.connected_users = " ".join(lst)
    current_user.connected_users = " ".join(current_lst)
    db.session.commit()
    return redirect(url_for('profile', username = user.username))

@app.route("/user_list/<string:content>/<int:id>", methods=['POST', 'GET'])
@login_required
def user_list(content, id):
    if content=='like':
        post = Post.query.filter_by(id=id).first()
        liked_users = post.liked_users
        lst = list(map(int,liked_users.split()))
        legend="User Likes"
    elif content=='connections':
        user = User.query.filter_by(id=id).first()
        connected_users = user.connected_users
        lst = list(map(int,connected_users.split()))
        legend="Connections"
    users=[]
    for i in lst:
        user_1 = User.query.filter_by(id=i).first()
        users.append(user_1)        
    for user in users:
        current_lst = list(map(int,current_user.connected_users.split()))
        if user.id in current_lst:
            user.email =1
        elif user.id == current_user.id:
            user.email =2
        else:  
            user.email =3 
    return render_template('user_list.html', users=users, legend=legend)    
        

@app.route("/search",methods=['POST','GET'])
@login_required
def search():
    if request.method =="POST":
        search_request=request.form['name']
        searched_user=search_request.lower()
        Users=User.query.all()
        username_list=[]
        for user in Users:
            if searched_user == user.username.lower()[:len(searched_user)]:
                username_list.append(user)
            elif user.email==searched_user:
                return redirect(url_for('profile',username=user.username))
        return render_template('search_user.html',username_list=username_list, legend="Search User")        
    else :
        flash('Invalid request', 'danger')


@app.route("/messages/<int:user_id>/<int:current_user_id>", methods=['POST', 'GET'])
@login_required
def messages(user_id,current_user_id):
    if current_user.id == current_user_id:
        form = MessageForm()
        if form.validate_on_submit():
            message = Message(message=form.content.data, receiver_id=user_id, sender_id=current_user_id)
            db.session.add(message)
            db.session.commit()
            flash('Message sent successfully!', 'success')
            return redirect(url_for('messages',user_id=user_id,current_user_id=current_user_id))
        messages_id=[]    
        messages1=Message.query.filter_by(receiver_id=user_id,sender_id=current_user_id).all()
        for message in messages1:
            messages_id.append(message.id)
        messages2=Message.query.filter_by(receiver_id=current_user_id,sender_id=user_id).all()
        for message in messages2:
            messages_id.append(message.id)    
        messages=[]    
        for id in messages_id:
            messages.append(Message.query.filter_by(id=id).first())
        current_receiver = User.query.filter_by(id=user_id).first()        
        return render_template('messages.html', messages = messages, current_receiver=current_receiver, legend = 'Messages', form = form)
    else:
        flash('Dont try to be Oversmart!', 'danger')
        return redirect(url_for('home'))