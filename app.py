from hashlib import sha256
import hmac
import json
import os
import threading
import urlparse
import httplib, urllib

from dropbox.client import DropboxClient, DropboxOAuth2Flow
from flask import abort, Flask, redirect, render_template, request, session, url_for
from markdown import markdown
import redis
 
redis_url = os.environ['REDISTOGO_URL']
redis_client = redis.from_url(redis_url)
 
# App key and secret from the App console (dropbox.com/developers/apps)
APP_KEY = os.environ['APP_KEY']
APP_SECRET = os.environ['APP_SECRET']
 
app = Flask(__name__)
app.debug = True
 
# A random secret used by Flask to encrypt session data cookies
app.secret_key = os.environ['FLASK_SECRET_KEY']

def get_url(route):
    '''Generate a proper URL, forcing HTTPS if not running locally'''
    host = urlparse.urlparse(request.url).hostname
    url = url_for(
        route,
        _external=True,
        _scheme='http' if host in ('127.0.0.1', 'localhost') else 'https'
    )

    return url

def get_flow():
    return DropboxOAuth2Flow(
        APP_KEY,
        APP_SECRET,
        get_url('oauth_callback'),
        session,
        'dropbox-csrf-token')

@app.route('/welcome')
def welcome():
    return render_template('welcome.html', redirect_url=get_url('oauth_callback'),
        webhook_url=get_url('webhook'), home_url=get_url('index'), app_key=APP_KEY)

@app.route('/oauth_callback')
def oauth_callback():
    '''Callback function for when the user returns from OAuth.'''

    access_token, uid, extras = get_flow().finish(request.args)
 
    # Extract and store the access token for this user
    redis_client.hset('tokens', uid, access_token)

    process_user(uid)

    return redirect(url_for('done'))

def process_user(uid):
    '''Call /delta for the given user ID and process any changes.'''
    print 'Here I am'
    # OAuth token for the user
    token = redis_client.hget('tokens', uid)

    # /delta cursor for the user (None the first time)
    cursor = redis_client.hget('cursors', uid)

    client = DropboxClient(token)
    has_more = True

    while has_more:
        result = client.delta(cursor)
        print '\n'
        print result
        print '\n'

        for path, metadata in result['entries']:

            # Ignore deleted files, folders, and non-markdown files
            if (metadata is None or
                    metadata['is_dir'] or
                    path.endswith('.md')):
                continue

            # Convert to Markdown and store as <basename>.html
            '''html = markdown(client.get_file(path).read())
            client.put_file(path[:-3] + '.html', html, overwrite=True)'''

            url_test = client.media(path)
            url_test2 = json.dumps(url_test)
            url_test3 = json.loads(url_test2)
            public_url = url_test3['url']
            print public_url

            # Publish task
            print 'My URL:'
            print urlparse.urlparse(request.url).hostname

            params = {
                "description": "We have detected a potential terrorist attack. We will ask you to locate some pictures and describe what is happening on them. If you don't know the answer, please answer 'I don't know'. ",
                "webhook_url": {
                    "host": urlparse.urlparse(request.url).hostname,
                    "path": "/answer"
                },
                "items": [{"item_answer_type": "text",
                           "item_question": "Can you indicate, as exactly as possible, the location of the following picture?",
                           "item_picture_url": public_url,
                           "item_answer_type": "text",
                           "item_question": "Describe what is happening on the picture."}
                           ],
                 "number_of_answers": 3,
                 "reward": 5,
                 "title": "Locate and describe picture"
                 }
            
            print params
            headers = {"Content-type": "application/json"}
            conn = httplib.HTTPConnection(os.environ['API_ENDPOINT'])
            conn.request("POST", "/api/tasks", json.dumps(params), headers)
            response = conn.getresponse()
            print response.read().decode()
            data = response.read()
            conn.close()

        # Update cursor
        cursor = result['cursor']
        redis_client.hset('cursors', uid, cursor)

        # Repeat only if there's more to do
        has_more = result['has_more']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return redirect(get_flow().start())

@app.route('/done')
def done(): 
    return render_template('done.html')

def validate_request():
    '''Validate that the request is properly signed by Dropbox.
       (If not, this is a spoofed webhook.)'''

    signature = request.headers.get('X-Dropbox-Signature')
    return signature == hmac.new(APP_SECRET, request.data, sha256).hexdigest()

@app.route('/webhook', methods=['GET'])
def challenge():
    '''Respond to the webhook challenge (GET request) by echoing back the challenge parameter.'''

    return request.args.get('challenge')

@app.route('/webhook', methods=['POST'])
def webhook():
    '''Receive a list of changed user IDs from Dropbox and process each.'''

    # Make sure this is a valid request from Dropbox
    if not validate_request(): abort(403)

    for uid in json.loads(request.data)['delta']['users']:
        # We need to respond quickly to the webhook request, so we do the
        # actual work in a separate thread. For more robustness, it's a
        # good idea to add the work to a reliable queue and process the queue
        # in a worker process.
        threading.Thread(target=process_user, args=(uid,)).start()
    return ''

@app.route('/answer', methods=['POST'])
def answer():

    redis_client.hset('answers', json.loads(request.data)['answers']['_id'], request.data)
    
    return ''

if __name__=='__main__':
    app.run(debug=True)
