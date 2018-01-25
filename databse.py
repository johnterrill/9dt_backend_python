from app import flask_app
from sql_data_provider import db

if __name__ == '__main__':
    with flask_app.app_context():
        db.drop_all()
        db.create_all()
