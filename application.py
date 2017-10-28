# CopyrighOKU_POSTGRESQL_COLORjjjjkjkkkkhts reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
"""Main program for Microsoft Graph API Connect demo."""
import os
from urllib import parse
import psycopg2
from flask_sqlalchemy import SQLAlchemy
import json
import sys
import uuid

# un-comment these lines to suppress the HTTP status messages sent to the console
#import logging
#logging.getLogger('werkzeug').setLevel(logging.ERROR)

import requests
from flask import Flask, redirect, url_for, session, request, render_template
from flask_oauthlib.client import OAuth

import datetime
from flask_sslify import SSLify

############################
#        App Setup         #
############################

# read private credentials from text file
client_id, client_secret, *_ = open('_PRIVATE.txt').read().split('\n')
if (client_id.startswith('*') and client_id.endswith('*')) or \
    (client_secret.startswith('*') and client_secret.endswith('*')):
    print('MISSING CONFIGURATION: the _PRIVATE.txt file needs to be edited ' + \
        'to add client ID and secret.')
    sys.exit(1)

application = Flask(__name__)
application.config.from_object(__name__)
application.debug = False
application.secret_key = 'development'
oauth = OAuth(application)

if 'DYNO' in os.environ: # only trigger SSLify if the app is running on Heroku
    sslify = SSLify(application)

############################
#        PostgreSQL        #
############################

parse.uses_netloc.append("postgres")
url = parse.urlparse(os.environ["DATABASE_URL"])

conn = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)

application.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(application)
db.session.expire_all()

class communities(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500))

    def __init__(self, name):
        self.name = name

class commembers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cid = db.Column(db.Integer, db.ForeignKey('communities.id'))
    uid = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __init__(self, cid, uid):
        self.cid = cid
        self.uid = uid

class users(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  display_name = db.Column(db.String(200))
  graph_id = db.Column(db.String(100), unique=True)
  email = db.Column(db.String(200), unique=True)

  def __init__(self, display_name, graph_id, email):
    self.display_name = display_name
    self.graph_id = graph_id
    self.email = email

class friends(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  uid1 = db.Column(db.Integer, db.ForeignKey('users.id'))
  uid2 = db.Column(db.Integer, db.ForeignKey('users.id'))

  def __init__(self, uid1, uid2):
    self.uid1 = uid1
    self.uid2 = uid2

class articles(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  url = db.Column(db.String(500))
  rating = db.Column(db.Integer, nullable=True)
  post_date = db.Column(db.Date)
  cat = db.Column(db.Integer)
  image = db.Column(db.String(500), nullable=True)
  title = db.Column(db.String(200), nullable=True)

  def __init__(self, url, cat, post_date=None, image=None, title=None):
    self.url = url
    self.cat = cat
    self.post_date = post_date
    self.image = image
    self.title = title

class userboards(db.Model):
  uid = db.Column(db.Integer, primary_key=True)
  aid = db.Column(db.Integer, primary_key=True)

  def __init__(self, uid, aid):
    self.uid = uid
    self.aid = aid

class catarticles(db.Model):
  bid = db.Column(db.Integer, primary_key=True)
  aid = db.Column(db.Integer, primary_key=True)

  def __init__(self, bid, aid):
    self.bid = bid
    self.aid = aid

class catboards(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(100))
  uid = db.Column(db.Integer)

  def __init__(self, name, uid):
    self.name = name
    self.uid = uid

class subscriptions(db.Model):
  uid = db.Column(db.Integer, primary_key=True)
  bid = db.Column(db.Integer, primary_key=True)

  def __init__(self, uid, bid):
    self.uid = uid
    self.bid = bid


############################
#     End MySQL Setup      #
############################

# since this sample runs locally without HTTPS, disable InsecureRequestWarning
requests.packages.urllib3.disable_warnings()

msgraphapi = oauth.remote_app( \
    'microsoft',
    consumer_key=client_id,
    consumer_secret=client_secret,
    request_token_params={'scope': 'User.Read Mail.Send User.ReadBasic.All'},
    base_url='https://graph.microsoft.com/v1.0/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
    authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
                             )

@application.route('/')
def index():
    """Handler for home page."""
    return render_template('landing.html')

@application.route('/login')
def login():
    """Handler for login route."""
    guid = uuid.uuid4() # guid used to only accept initiated logins
    session['state'] = guid
    return msgraphapi.authorize(callback=url_for('authorized', _scheme='https', _external=True), state=guid)

@application.route('/logout')
def logout():
    """Handler for logout route."""
    session.pop('microsoft_token', None)
    session.pop('state', None)
    return redirect(url_for('index'))

@application.route('/login/authorized')
def authorized():
    """Handler for login/authorized route."""
    response = msgraphapi.authorized_response()

    if response is None:
        return "Access Denied: Reason={0}\nError={1}".format( \
            request.args['error'], request.args['error_description'])

    # Check response for state
    if str(session['state']) != str(request.args['state']):
        raise Exception('State has been messed with, end authentication')
    session['state'] = '' # reset session state to prevent re-use

    # Okay to store this in a local variable, encrypt if it's going to client
    # machine or database. Treat as a password.
    session['microsoft_token'] = (response['access_token'], '')
    # Store the token in another session variable for easy access
    session['access_token'] = response['access_token']
    me_response = msgraphapi.get('me')
    me_data = json.loads(json.dumps(me_response.data))

    # Grab the email
    email = me_data['mail']
    session['email'] = email

    # Grab the display name
    display_name = me_data['displayName']
    session['display_name'] = display_name

    # Grab the graph_id
    graph_id = me_data['id']
    session['graph_id'] = graph_id

    return redirect('dashboard')

#########################
#     TIGERHACKS API    #
#########################

@application.route('/load-graph-users', methods=('GET','POST'))
def loadGraphUsers():

    # Initialize default communities
    mst = communities("Missouri S&T")
    db.session.add(mst)

    mizzou = communities("Mizzou")
    db.session.add(mizzou)

    umsl = communities("UMSL")
    db.session.add(umsl)

    umkc = communities("UMKC")
    db.session.add(umkc)

    db.session.commit()


    # Get all users on graph
    r = requests.get('https://graph.microsoft.com/v1.0/users', headers={"Authorization":"Bearer "+ session['access_token']})
    r = r.json()

    for user in r['value']:
        new_graph_user = users(user['displayName'], user['id'], user['mail'])
        db.session.add(new_graph_user)
        db.session.commit()

        # Sort into default communities
        sandt_email = "mail.mst.edu"
        mizzou_email = "mail.missouri.edu"
        umsl_email = "mail.umsl.edu"
        umkc_email = "mail.umkc.edu"

        try:
            user_email = str(user['mail']).split("@",1)[1]

            if user_email == sandt_email:
                new_member = commembers(mst.id, new_graph_user.id)

            elif user_email == mizzou_email:
                new_member = commembers(mizzou.id, new_graph_user.id)

            elif user_email == umsl_email:
                new_member = commembers(umsl.id, new_graph_user.id)

            elif user_email == umkc_email:
                new_member = commembers(umkc.id, new_graph_user.id)

            db.session.add(new_member)
            db.session.commit()
        except:
            pass

    return "awesome"

@application.route('/boards', methods=('GET','POST'))
def boards():

    # Render all subscribed-to boards
    subbed_boards_users = userboards.query.filter(users.id == session['uid']).filter(subscriptions.uid == users.id).filter(userboards.uid == subscriptions.bid)
    subbed_boards_cats = catboards.query.filter(users.id == subscriptions.uid).filter(subscriptions.bid == catboards.id)

    all_subbed_boards = []
    for board in subbed_boards_users:
        user = users.query.filter(users.id == board.uid).first()
        all_subbed_boards.append(user.display_name)

    for board in subbed_boards_cats:
        all_subbed_boards.append(board.name)

    # Render default communities
    sandt = communities.query.filter(communities.id == 1)
    mizzou = communities.query.filter(communities.id == 2)
    umsl = communities.query.filter(communities.id == 3)
    umkc = communities.query.filter(communities.id == 4)

    default_com = [sandt, mizzou, umsl, umkc]

    # Render and prioritize all communities
    communities_data = communities.query.filter(users.id == session['uid']).filter(commembers.uid == users.id).filter(commembers.cid == communities.id)

    all_communities = []
    for community_item in communities_data:
        all_communities.append(community_item)

    # Select all existing users for friends input
    all_users_data = users.query.all()

    all_users = []
    for user in all_users_data:
        all_users.append((user.id, user.display_name))

    return render_template('boards.html', all_subbed_boards=all_subbed_boards, all_users=all_users, all_communities=all_communities, default_com=default_com)

@application.route('/dashboard', methods=('GET','POST'))
def dashboard():

    name = session['display_name']

    # Does the user already exist?
    user = users.query.filter_by(graph_id=session['graph_id']).first()

    # If yes, grab their uid
    if user is not None:
        session['uid'] = user.id

    # If not, insert them into the db, then grab their id
    else:
        new_user = (
            session['display_name'],
            session['graph_id'],
            session['email']
        )

        new_user = users(session['display_name'], session['graph_id'], session['email'])
        db.session.add(new_user)
        db.session.commit()

        session['uid'] = new_user.id

    # Populate board with user's articles
    articles_data = articles.query.filter(articles.id==userboards.aid).filter(users.id==userboards.uid).filter(users.id==session['uid'])

    all_articles = []
    for article in articles_data:
        all_articles.append([article.url, article.image, article.title])

    # Populate board with friends' articles
    user_friends_data = friends.query.filter(users.id == friends.uid1).filter(users.id == session['uid'])

    user_friends = []
    for friend in user_friends_data:
        user_friends.append(friend.uid2)

    for friend in user_friends:
        articles_data = articles.query.filter(articles.id==userboards.aid).filter(users.id==userboards.uid).filter(users.id==friend)

        for article in articles_data:
            all_articles.append([article.url, article.image, article.title])

    # Populate template with subbed boards
    subbed_boards_data = catboards.query.filter(catboards.id == subscriptions.bid).filter(subscriptions.uid == users.id).filter(users.id==session['uid'])

    subbed_boards = []
    for board in subbed_boards_data:
        subbed_boards.append((board.id, board.name))

    for index,board in enumerate(subbed_boards):
        subbed_articles = []
        subbed_articles_data = articles.query.filter(articles.id == catarticles.aid).filter(catarticles.bid == str(board[0]))

        for article in subbed_articles_data:
            subbed_articles.append([article.url, article.image, article.title])

        subbed_boards[index] = subbed_boards[index] + (subbed_articles,)

    # Select all existing users for friends input
    all_users_data = users.query.all()

    all_users = []
    for user in all_users_data:
        all_users.append((user.id, user.display_name))

    # Select all created categories
    all_subbed_cats_data = catboards.query.filter(users.id == catboards.uid).filter(users.id == session['uid'])

    subbed_cats = []
    for cat in all_subbed_cats_data:
        subbed_cats.append((cat.id, cat.name))

    return render_template('dashboard.html', name=name,
                           all_articles=all_articles, all_users=all_users,
                           subbed_cats=subbed_cats, subbed_boards=subbed_boards)

@application.route('/add-friend', methods=('GET','POST'))
def addFriend():

    # Add new user to friends list
    new_friend = request.form['user']

    # If they are not already friends
    friend_check = friends.query.filter(new_friend==friends.uid2).filter(session['uid']==friends.uid1)
    friend_check2 = friends.query.filter(session['uid']==friends.uid2).filter(session['uid']==friends.uid1)

    if friend_check.first() is None and friend_check2 is None:
        friend1 = friends(session['uid'], new_friend)
        db.session.add(friend1)
        friend2 = friends(new_friend, session['uid'])
        db.session.add(friend2)

        db.session.commit()

    return redirect(url_for('dashboard'))

@application.route('/add-article', methods=('GET','POST'))
def addArticle():

    new_article = request.form['article']
    post_date = datetime.datetime.now()
    cat_tag = request.form['cat']

    new_article_query = articles(new_article, cat_tag, post_date)
    db.session.add(new_article_query)
    db.session.commit()

    aid = new_article_query.id

    # If an article is tagged, add to catarticles
    if int(cat_tag) != -1:
        add_to_cat_board = catarticles(cat_tag, aid)
        db.session.add(add_to_cat_board)

    # Add article to user board always
    add_to_user_board = userboards(session['uid'], aid)
    db.session.add(add_to_user_board)

    db.session.commit()

    return redirect(url_for('dashboard'))

@application.route('/add-board', methods=('GET','POST'))
def addBoard():

    # Add a new category board
    new_board = request.form['board']

    add_new_board = catboards(new_board, session['uid'])
    db.session.add(add_new_board)
    db.session.commit()

    bid = add_new_board.id

    # Subscribe to new board
    subscribe_to_board = subscriptions(session['uid'], bid)
    db.session.add(subscribe_to_board)
    db.session.commit()

    return redirect(url_for('catBoard', board_name=new_board))

@application.route('/board/<board_name>')
def catBoard(board_name):

    #board_name = (board_name.lower()).replace("_", "")
    board_name = board_name

    # Check if board exists in db
    check_board = catboards.query.filter(catboards.name == board_name)

    if check_board.first() is not None:

        # Render all articles that belong to this catboards
        catarticles_data = articles.query.filter(catboards.id == catarticles.bid).filter(catarticles.aid == articles.id)

        all_catarticles = []
        for article in catarticles_data:
            all_catarticles.append([article.url, article.image, article.title])

        # Select all existing users for friends input
        all_users_data = users.query.all()

        all_users = []
        for user in all_users_data:
            all_users.append((user.id, user.display_name))

        return render_template('dashboard.html', board_name=board_name, all_articles=all_catarticles,
                                all_users=all_users)

    else:
        return redirect('https://www.readthis.cf/oops')

    return "cool"

@application.route('/get-ajax-data', methods=('GET','POST','PUT'))
def getAjaxData():

    art_data = request.get_json()
    art_link = art_data['article_link']
    art_image = art_data['article_image']
    art_title = art_data['article_title']

    date = datetime.datetime.now()
    cat = -1

    new_article = articles(art_link, cat, date, art_image, art_title)
    db.session.add(new_article)
    db.session.commit()

    uid = 1
    inert_to_userboard = userboards(uid, new_article.id)
    db.session.add(inert_to_userboard)
    db.session.commit()

    return "cool"

@application.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

#########################asfadsfasfas
#  END TIGERHACKS API   #
#########################

# If library is having trouble with refresh, uncomment below and implement
# refresh handler see https://github.com/lepture/flask-oauthlib/issues/160 for
# instructions on how to do this. Implements refresh token logic.
# @application.route('/refresh', methods=['POST'])
# def refresh():
@msgraphapi.tokengetter
def get_token():
    """Return the Oauth token."""
    return session.get('microsoft_token')

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    application.run(host='0.0.0.0', port=port)
