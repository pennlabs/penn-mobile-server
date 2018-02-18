import datetime

from flask import jsonify, request
from dateutil.parser import parse

from server import app, sqldb
from .models import StudySpacesBooking
from .penndata import studyspaces
from .base import cached_route


@app.route('/studyspaces/availability/<int:building>', methods=['GET'])
def parse_times(building):
    """
    Returns JSON containing all rooms for a given building.

    Usage:
        /studyspaces/availability/<building> gives all rooms for the next 24 hours
        /studyspaces/availability/<building>?start=2018-25-01 gives all rooms in the start date
        /studyspaces/availability/<building>?start=...&end=... gives all rooms between the two days
    """
    start = request.args.get('start')
    end = request.args.get('end')

    rooms = studyspaces.get_rooms(building, start, end)

    return jsonify(rooms)


@app.route('/studyspaces/locations', methods=['GET'])
def display_id_pairs():
    """
    Returns JSON containing a list of buildings with their ids.
    """
    def get_data():
        return {"locations": studyspaces.get_buildings()}

    return cached_route('studyspaces:locations', datetime.timedelta(days=1), get_data)


@app.route('/studyspaces/book', methods=['POST'])
def book_room():
    """
    Books a room.
    """

    try:
        room = int(request.form["room"])
    except (KeyError, ValueError):
        return jsonify({"results": False, "error": "Please specify a correct room id!"})

    try:
        start = request.form["start"]
        end = request.form["end"]
    except KeyError:
        return jsonify({"results": False, "error": "No start and end parameters passed to server!"})

    contact = {}
    for arg, field in [("fname", "firstname"), ("lname", "lastname"), ("email", "email"), ("nickname", "groupname")]:
        try:
            contact[arg] = request.form[field]
        except KeyError:
            return jsonify({"results": False, "error": "'{}' is a required parameter!".format(field)})

    contact["custom"] = {}
    for arg, field in [("q2533", "phone"), ("q2555", "size")]:
        try:
            contact["custom"][arg] = request.form[field]
        except KeyError:
            pass

    resp = studyspaces.book_room(room, start, end, **contact)
    if "error" not in resp:
        save_booking(
            rid=room,
            email=contact["email"],
            start=parse(start).replace(tzinfo=None),
            end=parse(end).replace(tzinfo=None)
        )
    return jsonify(resp)


def save_booking(**info):
    item = StudySpacesBooking(**info)

    sqldb.session.add(item)
    sqldb.session.commit()
