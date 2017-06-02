from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Category, Item, User
engine = create_engine('sqlite:///tradeitems.db')

Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

#  Create categories
category1 = Category(name="Technology")
session.add(category1)
session.commit()

category2 = Category(name="Games & Fun")
session.add(category2)
session.commit()

category3 = Category(name="Sports")
session.add(category3)
session.commit()

category4 = Category(name="Tools")
session.add(category4)
session.commit()

category5 = Category(name="Motor Vehicles")
session.add(category5)
session.commit()
