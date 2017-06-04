from flask import session as login_session
from flask import Flask, render_template, flash, redirect, url_for, request, jsonify, make_response
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
import os
import random
import string
import httplib2
import json
import requests
import helper_functions as helper

app = Flask(__name__)
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

#  JSON Endpoint


@app.route('/JSON')
def indexJSON():
    categories = helper.getAllCategories()
    items = helper.getAllItems()
    #  Create the object that will be jsonified, and fill it with required info
    jsonObj = {'Category': []}
    for cat in categories:
        jsonObj['Category'].append({
            'id': cat.id,
            'name': cat.name,
            'trade_items': []
        })
    for i in items:
        jsonObj['Category'][i.category_id-1]['trade_items'].append({
            'id': i.id,
            'owner_id': i.owner_id,
            'category_id': i.category_id,
            'name': i.name,
            'condition': i.condition,
            'description': i.description
        })

    return jsonify(jsonObj)

#  Home page, all items


@app.route('/')
def index():
    categories = helper.getAllCategories()
    items_for_trade = helper.getAllItems()
    item_owner_ids = []
    item_owners = []
    for item in items_for_trade:
        item_owner_ids.append(item.owner_id)
    for id in item_owner_ids:
        item_owners.append(helper.getItemOwner(id))
    #  Convert into set to remove duplicate values
    item_owners = set(item_owners)

    return render_template('items.html', items=items_for_trade,
                           owners=item_owners, categories=categories)

#  Items by category


@app.route('/items/<int:category_id>/')
def items_by_category(category_id):
    categories = helper.getAllCategories()
    items = helper.getItemsByCategory(category_id)
    item_owner_ids = []
    item_owners = []
    for item in items:
        item_owner_ids.append(item.owner_id)
    for id in item_owner_ids:
        item_owners.append(helper.getItemOwner(id))
    #  Convert into set to remove duplicate values
    item_owners = set(item_owners)
    return render_template('items.html', items=items,
                           owners=item_owners, categories=categories)

#  Create new item


@app.route('/create/', methods=['GET', 'POST'])
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
        #  Extract only image name and save it
        imgname = imgpath.split('\\')
        imgname = imgname[::-1][0]
        #  Check if user has uploaded the image, if not, set the default
        if imgname == '':
            imgname = 'noimage.jpg'
        #  Save the image if the user has uploaded it
        destination = os.path.join(target, imgname)
        if imgname != 'noimage.jpg':
            image.save(destination)
        #  Add item to the database
        newItem = helper.createItem(
            login_session['user_id'],
            request.form['category_id'],
            request.form['item_name'],
            request.form['condition'],
            request.form['description'],
            '/static/images/' + imgname)
        #  Display success message and redirect
        flash("{item} is now available for trade.".format(
            item=newItem.name), 'success')
        return redirect('/')
    #  If user simply visits the page
    else:
        categories = helper.getAllCategories()
        return render_template('create.html', categories=categories)

#  View single item


@app.route('/item/<int:item_id>')
def item(item_id):
    categories = helper.getAllCategories()
    item = helper.getItem(item_id)
    item_category = helper.getCategory(item.category_id)
    owner = helper.getItemOwner(item.owner_id)
    allowed_to_edit = False
    if 'username' in login_session:
        if item.owner_id == login_session['user_id']:
            allowed_to_edit = True
    state = 'not logged in'
    if 'state' in login_session:
        state = login_session['state']
    return render_template('item.html', categories=categories, item=item,
                           item_category=item_category, owner=owner,
                           state=state, allowed_to_edit=allowed_to_edit)

#  Update item


@app.route('/update', methods=['POST'])
def update():
    #  CSRF protection
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Something went wrong.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    item_id = request.form['update-item-id']
    #  Dictionary of data to update
    new_data = {}
    for d in request.form:
        new_data[d] = request.form[d]

    #  Upload the item image
    target = os.path.join(APP_ROOT, 'static/images/')
    image = request.files['image']
    imgpath = request.form['file-name']
    #  Extract only image name and save it
    imgname = imgpath.split('\\')
    imgname = imgname[::-1][0]
    #  Check if user has uploaded the image, if not, set the default
    if imgname == '':
        imgname = 'noimage.jpg'
    #  Save the image if the user has uploaded it
    destination = os.path.join(target, imgname)
    if imgname != 'noimage.jpg':
        image.save(destination)
    #  Call the helper to update item
    helper.updateItem(item_id, new_data, imgname)
    flash('Item edited successfully', 'success')
    return item_id


#  Delete item
@app.route('/delete', methods=['POST'])
def delete():
    #  CSRF protection
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Something went wrong.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    item_id = request.form['delete-item-id']
    #  Delete the item
    helper.deleteItem(item_id)
    #  Call the helper to update item
    flash('Item deleted successfully', 'success')
    return 'deleted'


#  Login
@app.route('/login')
def login():
    #  Random code to protect against CSRF
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', state=state)

#  Auth with Google


@app.route('/gconnect', methods=['POST'])
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
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' %
           access_token)
    h = httplib2.Http()
    #  JSON object has to be str, not bytes
    result = json.loads(h.request(url, 'GET')[1].decode('utf-8'))

    #  Check if token is valid
    if result.get('error') is not None:
        print("Error: " + result.get('error'))
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    #  Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps('Token\'s user ID doesn\'t match given user ID.'), 401)
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
            json.dumps('Already connected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    #  Update the session
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    #  Get user info
    userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()
    #  Update the session with user info
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    #  If user doesn't exist in the database, send different response
    try:
        user_id = helper.getUserID(data['email'])
    except Exception as e:
        print(e)
    try:
        user_info = helper.getUserInfo(user_id)
    except Exception as e:
        print(e)
    if not user_id:
        return 'User doesn\'t exist'
    else:
        login_session['user_id'] = user_id
        login_session['username'] = user_info.name
        flash('Successfully logged in as %s' % user_info.name, 'success')
        return 'User exists'

#  Create the User in database table users


@app.route('/register_user', methods=['POST'])
def register_user():
    #  CSRF protection
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Something went wrong.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    #  Update the session
    login_session['username'] = request.form['username']
    #  Create the user in the database
    user = helper.createUser(
        login_session,
        request.form['phone'],
        request.form['location'])
    login_session['user_id'] = user.id
    #  If user created successfully
    if user:
        flash('Successfully logged in as %s' % user.name, 'success')
        return 'success'
    else:
        return 'failed'


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
        return redirect('/')
    else:
        flash("You were not logged in")
        return redirect('/')


if __name__ == '__main__':
    app.secret_key = "this_is_fun_76543"
    #app.run(debug=True)
    app.run()
