from flask.ext.script import Manager, Shell
from application import app, db, models, admin


manager = Manager(app)


# for shell command
def _make_context():
    return dict(app=app, db=db, models=models)


@manager.command
def run():
    app.run()


@manager.command
def test():
    app.config['TESTING'] = True
    app.run(debug=True)


@manager.command
def initdb():
    """Init/reset database."""
    from application.models import WHMCSclients, Badges, WHMCSproducts, WHMCSaddons
    from datetime import date, timedelta

    db.drop_all()
    db.create_all()

    client = WHMCSclients('Benjamin', 'Groves', 'ben.groves.tx@gmail.com')

    db.session.add(client)
    db.session.commit()

    badge = Badges(client.id, 123456, 'Deactivated')

    db.session.add(badge)
    db.session.commit()

    next_week = date.today() + timedelta(days=7)
    product = WHMCSproducts(client.id, next_week, u'Active')

    db.session.add(product)
    db.session.commit()

    addon = WHMCSaddons(client.id, u'Active', next_week)

    db.session.add(addon)
    db.session.commit()


manager.add_command("shell", Shell(make_context=_make_context))

if __name__ == "__main__":
    manager.run()
