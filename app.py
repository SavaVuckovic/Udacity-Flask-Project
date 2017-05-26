from flask import Flask, render_template, flash, redirect, url_for, request, jsonify, make_response
from flask import session as login_session
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import os, random, string, httplib2, json, requests
import helper_functions as helper

'''
TO DO:
 - fix auth
 - style images
 finish:
 - Update (& authorization)
 - Delete (& authorization)
 - create more helpers and show all required info
 - clean the code (final) (pep8)
 - create the home page
 - create JSON endpoint
 - change Google API project name
 - write a readme

'''


app = Flask(__name__)
CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

#  Home page
@app.route('/')
def index():
    return render_template('home.html')

#  All items
@app.route('/items')
def items():
    categories = helper.getAllCategories()
    items_for_trade = helper.getAllItems()
    return render_template('items.html', items = items_for_trade, categories = categories)

@app.route('/items/<int:category_id>/')
def items_by_category(category_id):
    categories = helper.getAllCategories()
    items = helper.getItemsByCategory(category_id)
    return render_template('items.html', items = items, categories = categories)

#  Create new item
@app.route('/create/', methods=['GET', 'POST'] )
def create_item():
    #  Redirect if user is not logged in
    if 'username' not in login_session:
        flash('You have to log in to be able to create items.', 'info')
        return redirect('/login')
    #  If user posts a form, create new item in the database
    if request.method == 'POST':
        #  Upload the item image
        target = os.path.join(APP_ROOT, 'static/images/')
        image = request.files['image']
        imgpath = request.form['file-name']
        #  Extract only image name
        imgname = imgpath.split('\\')
        imgname = imgname[::-1][0]
        destination = os.path.join(target, imgname)
        image.save(destination)
        #  Add item to the database
        newItem = helper.createItem(
            login_session['user_id'],
            request.form['category_id'],
            request.form['item_name'],
            request.form['condition'],
            request.form['description'],
            '/static/images/'+imgname)
        #  Display success message and redirect
        flash("{item} is now available for trade.".format(item = newItem.name), 'success')
        return redirect('/items')
    #  If user simply visits the page
    else:
        categories = helper.getAllCategories()
        return render_template('create.html', categories = categories)

#  View single item
@app.route('/item/<int:item_id>')  ######11111111111111111111111111111111111111111111111
def item(item_id):
    categories = helper.getAllCategories()
    item = helper.getItem(item_id)
    allowed_to_edit = False
    if 'username' in login_session:
        if item.owner_id == login_session['user_id']:
            allowed_to_edit = True
    return render_template('item.html', item = item, categories = categories, allowed_to_edit = allowed_to_edit)

#  Login
@app.route('/login')
def login():
    #  Random code to protect against CSRF
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', state=state)

#  Auth with Google
@app.route('/gconnect', methods = ['POST'])
def gconnect():
    #  CSRF protection
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Something went wrong.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    #  Gets the one time code
    code = request.data
    try:
        #  Create the credentials obj from auth code
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    #  If it fails
    except FlowExchangeError:
        response = make_response(
                    json.dumps('Failed to create credentials object'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    #  Verify the token
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    #  JSON object has to be str, not bytes
    result = json.loads(h.request(url, 'GET')[1].decode('utf-8'))

    #  Check if token is valid
    if result.get('error') is not None:
        print("Error: " + result.get('error')) #
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    #  Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    #  Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Already connected'),200)
        response.headers['Content-Type'] = 'application/json'
        return response

    #  Update the session
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    #  Get user info
    userinfo_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    #  Update the session with user info
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    #  Create user if he doesn't already exist in the database
    user_id = helper.getUserID(data["email"])
    if not user_id:
        user_id = helper.createUser(login_session)
    login_session['user_id'] = user_id

    #  Success
    flash("Successfully logged in as %s" % login_session['username'], 'success')
    return login_session['username']


#  Disconnect (Log out) the user
@app.route('/disconnect')
def disconnect():
    if 'username' in login_session:
        token = login_session.get('access_token')
        if token is None:
            response = make_response(
                json.dumps('Current user not connected.'), 401)
            response.headers['Content-Type'] = 'application/json'
            return response
        access_token = token
        print('token: ' + access_token)
        url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
        h = httplib2.Http()
        result = h.request(url, 'GET')[0]
        if result['status'] != '200':
            #  For whatever reason, the given token was invalid.
            response = make_response(
                json.dumps('Failed to revoke token for given user.'), 400)
            response.headers['Content-Type'] = 'application/json'
            return response

        flash('Thanks for visiting us', 'info')
        #  Destroy the session
        del login_session['gplus_id']
        del login_session['access_token']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        return redirect('/items')
    else:
        flash("You were not logged in")
        return redirect('/items')


if __name__ == '__main__':
    app.secret_key = "this_is_fun_76543"
    app.run(debug=True)
    #app.run()




















'''


RELEVANT
https://github.com/udacity/OAuth2.0
https://www.google.rs/search?q=flask+and+3rd+party+oauth&ie=utf-8&oe=utf-8&client=firefox-b&gws_rd=cr&ei=cBUgWbKWOcfXwAL3rJOwCw
https://blog.miguelgrinberg.com/post/oauth-authentication-with-flask
http://docs.sqlalchemy.org/en/latest/orm/basic_relationships.html#one-to-many









'''