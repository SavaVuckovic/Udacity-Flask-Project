from database_setup import Base, Category, User, Item
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker

#  Connect to Database and create database session
engine = create_engine('sqlite:///tradeitems.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

def createItem(user_id, category_id, item_name, condition, description, img_name):
    item = Item(
        owner_id = user_id,
        category_id = category_id,
        name = item_name,
        condition = condition,
        description = description,
        image = img_name
    )
    session.add(item)
    session.commit()
    return item

def createUser(login_session, phone, location):
    #  create new user object
    user = User(
        name=login_session['username'],
        email=login_session['email'],
        picture=login_session['picture'],
        phone=phone,
        location=location)
    #  Add new user to the database
    session.add(user)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user

def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

def getItemOwner(item_owner_id):
    owner = session.query(User).filter_by(id=item_owner_id).one()
    return owner

def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

def getItem(item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    return item

def getAllItems():
    items = session.query(Item).order_by(desc(Item.id))
    return items

def getItemsByCategory(category_id):
    items = session.query(Item).filter_by(category_id=category_id).order_by(desc(Item.id)).all()
    return items





def getAllCategories():
    categories = session.query(Category)
    return categories

def getCategory(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    return category
