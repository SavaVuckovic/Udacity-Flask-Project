from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

#  Categories table


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

#  Users table


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))
    phone = Column(Integer, nullable=False)
    location = Column(String(250), nullable=False)

#  Items(for trade) table


class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'))
    category_id = Column(Integer, ForeignKey('categories.id'))
    name = Column(String(250), nullable=False)
    condition = Column(String(250), nullable=False)
    description = Column(Text, nullable=False)
    image = Column(String(250))


#  Create the 'tradeitems.db' database file
engine = create_engine('sqlite:///tradeitems.db')
Base.metadata.create_all(engine)
