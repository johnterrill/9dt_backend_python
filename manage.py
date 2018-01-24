from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from app import flask_app
from sql_data_provider import db

manager = Manager(flask_app)
migrate = Migrate(flask_app, db)

manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
