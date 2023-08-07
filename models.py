from mongoengine import *
import configparser
from urllib.parse import quote_plus

config = configparser.ConfigParser()

config.read('config.ini')

mongodb_url = config.get('DATABASE', 'mongodb_url')
mongodb_uri = quote_plus(mongodb_url)  # Екрануємо спеціальні символи у URL

connect(db='hw_8', host=mongodb_uri)

class Author(Document):
    fullname = StringField(required=True)
    born_date = StringField(max_length=50)
    born_location = StringField(max_length=80)
    description = StringField()


class Quote(Document):
    tags = ListField(StringField())
    author = ReferenceField(Author)
    quote = StringField(required=True)