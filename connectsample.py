# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
"""Main program for Microsoft Graph API Connect demo."""
import json
import sys
import uuid

# un-comment these lines to suppress the HTTP status messages sent to the console
#import logging
#logging.getLogger('werkzeug').setLevel(logging.ERROR)

import requests
from flask import Flask, redirect, url_for, session, request, render_template
from flask_oauthlib.client import OAuth

############################
#        MySQL Setup       #
############################

from flask_mysqldb import MySQL

# read private credentials from text file
client_id, client_secret, *_ = open('_PRIVATE.txt').read().split('\n')
if (client_id.startswith('*') and client_id.endswith('*')) or \
    (client_secret.startswith('*') and client_secret.endswith('*')):
    print('MISSING CONFIGURATION: the _PRIVATE.txt file needs to be edited ' + \
        'to add client ID and secret.')
    sys.exit(1)

app = Flask(__name__)
app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'tigerhacks'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_UNIX_SOCKET'] = '//Applications/MAMP/tmp/mysql/mysql.sock'

mysql = MySQL(app)

############################
#     End MySQL Setup      #
############################

# since this sample runs locally without HTTPS, disable InsecureRequestWarning
requests.packages.urllib3.disable_warnings()

msgraphapi = oauth.remote_app( \
    'microsoft',
    consumer_key=client_id,
    consumer_secret=client_secret,
    request_token_params={'scope': 'User.Read Mail.Send'},
    base_url='https://graph.microsoft.com/v1.0/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
    authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
                             )

@app.route('/')
def index():
    """Handler for home page."""
    return render_template('connect.html')

@app.route('/login')
def login():
    """Handler for login route."""
    guid = uuid.uuid4() # guid used to only accept initiated logins
    session['state'] = guid
    return msgraphapi.authorize(callback=url_for('authorized', _external=True), state=guid)

@app.route('/logout')
def logout():
    """Handler for logout route."""
    session.pop('microsoft_token', None)
    session.pop('state', None)
    return redirect(url_for('index'))

@app.route('/login/authorized')
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

@app.route('/dashboard', methods=('GET','POST'))
def dashboard():

    name = session['display_name']

    CHECK_USER_EXISTS = "SELECT id FROM users WHERE graph_id = '%s'"
    INSERT_NEW_USER = ("INSERT INTO users (display_name, graph_id, email) VALUES " +
                       "('%s', '%s', '%s')")

    # Does the user already exist?
    cur = mysql.connection.cursor()
    cur.execute((CHECK_USER_EXISTS % session['graph_id']))
    result = cur.fetchall()

    # If yes, grab their uid
    if result:
        session['uid'] = result[0]

    # If not, insert them into the db, then grab their id
    else:
        new_user = (
            session['display_name'],
            session['graph_id'],
            session['email']
        )

        cur.execute((INSERT_NEW_USER % new_user))
        mysql.connection.commit()

        session['uid'] = cur.lastrowid

    # Populate board with user's articles
    SELECT_ARTICLES = ("SELECT url FROM users u, userBoards b, articles a " +
                            "WHERE u.id = b.uid AND b.aid = a.id AND u.id = '%s'")

    cur.execute((SELECT_ARTICLES % session['uid']))

    all_articles = []
    for article in cur.fetchall():
        all_articles.append(article[0])

    # Populate board with friends' articles
    SELECT_USER_FRIENDS = ("SELECT uid2 FROM users u, friends f WHERE " +
                           "f.uid1 = u.id AND u.id = '%s'")

    cur.execute((SELECT_USER_FRIENDS % session['uid']))

    user_friends = []
    for friend in cur.fetchall():
        user_friends.append(friend[0])

    for friend in user_friends:
        cur.execute((SELECT_ARTICLES % friend))

        for article in cur.fetchall():
            all_articles.append(article[0])

    # Select all existing users for friends input
    SELECT_ALL_USERS = "SELECT id,display_name FROM users"

    cur.execute(SELECT_ALL_USERS)

    all_users = []
    for user in cur.fetchall():
        all_users.append((user[0], user[1]))

    return render_template('dashboard.html', name=name,
                           all_articles=all_articles, all_users=all_users)

@app.route('/add-friend', methods=('GET','POST'))
def addFriend():

    # Add new user to friends list
    new_friend = request.form['user']

    ADD_TO_FRIENDS_LIST = "INSERT INTO friends (uid1, uid2) VALUES ('%s', '%s')"

    cur = mysql.connection.cursor()
    cur.execute((ADD_TO_FRIENDS_LIST % (session['uid'][0], new_friend)))
    cur.execute((ADD_TO_FRIENDS_LIST % (new_friend, session['uid'][0])))
    mysql.connection.commit()

    return redirect(url_for('dashboard'))

#########################
#  END TIGERHACKS API   #
#########################

@app.route('/send_mail')
def send_mail():
    """Handler for send_mail route."""
    email_address = request.args.get('emailAddress') # get email address from the form
    response = call_sendmail_endpoint(session['access_token'], session['alias'], email_address)
    if response == 'SUCCESS':
        show_success = 'true'
        show_error = 'false'
    else:
        print(response)
        show_success = 'false'
        show_error = 'true'

    session['pageRefresh'] = 'false'
    return render_template('main.html', name=session['alias'],
                           emailAddress=email_address, showSuccess=show_success,
                           showError=show_error)

# If library is having trouble with refresh, uncomment below and implement
# refresh handler see https://github.com/lepture/flask-oauthlib/issues/160 for
# instructions on how to do this. Implements refresh token logic.
# @app.route('/refresh', methods=['POST'])
# def refresh():
@msgraphapi.tokengetter
def get_token():
    """Return the Oauth token."""
    return session.get('microsoft_token')

def call_sendmail_endpoint(access_token, name, email_address):
    """Call the resource URL for the sendMail action."""
    send_mail_url = 'https://graph.microsoft.com/v1.0/me/microsoft.graph.sendMail'

	# set request headers
    headers = {'User-Agent' : 'python_tutorial/1.0',
               'Authorization' : 'Bearer {0}'.format(access_token),
               'Accept' : 'application/json',
               'Content-Type' : 'application/json'}

	# Use these headers to instrument calls. Makes it easier to correlate
    # requests and responses in case of problems and is a recommended best
    # practice.
    request_id = str(uuid.uuid4())
    instrumentation = {'client-request-id' : request_id,
                       'return-client-request-id' : 'true'}
    headers.update(instrumentation)

	# Create the email that is to be sent via the Graph API
    email = {'Message': {'Subject': 'Welcome to the Microsoft Graph Connect sample for Python',
                         'Body': {'ContentType': 'HTML',
                                  'Content': render_template('email.html', name=name)},
                         'ToRecipients': [{'EmailAddress': {'Address': email_address}}]
                        },
             'SaveToSentItems': 'true'}

    response = requests.post(url=send_mail_url,
                             headers=headers,
                             data=json.dumps(email),
                             verify=False,
                             params=None)

    if response.ok:
        return 'SUCCESS'
    else:
        return '{0}: {1}'.format(response.status_code, response.text)
