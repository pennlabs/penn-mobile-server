import math
from datetime import datetime

from bs4 import BeautifulSoup
from flask import g, jsonify, request
from sqlalchemy.exc import IntegrityError

from server import app, sqldb
from server.auth import auth


class Housing(sqldb.Model):
    account = sqldb.Column(sqldb.VARCHAR(255), sqldb.ForeignKey("account.id"), primary_key=True)
    house = sqldb.Column(sqldb.Text, nullable=True)
    location = sqldb.Column(sqldb.Text, nullable=True)
    address = sqldb.Column(sqldb.Text, nullable=True)
    off_campus = sqldb.Column(sqldb.Boolean, nullable=True)
    start = sqldb.Column(sqldb.Integer, primary_key=True, default=-1)
    end = sqldb.Column(sqldb.Integer, default=-1)
    created_at = sqldb.Column(sqldb.DateTime, server_default=sqldb.func.now())


@app.route("/housing", methods=["POST"])
@auth()
def save_housing_info():
    html = request.form.get("html")

    soup = BeautifulSoup(html, "html.parser")
    html = soup.prettify().strip().strip("\t\r\n")

    house, location, address = None, None, None
    main = soup.findAll("div", {"class": "interior-main-content col-md-6 col-md-push-3 md:mb-150"})[
        0
    ]

    off_campus = "You don't have any assignments at this time" in html
    if off_campus:
        # Off campus for 2020 - 2021 school year if today is after January and user has no assignments
        today = datetime.today()
        start = today.year if today.month > 1 else today.year - 1
        end = start + 1
    else:
        year_text, house_text = None, None
        headers = main.findAll("h3")
        for h3 in headers:
            if "Academic Year" in h3.text:
                year_text = h3.text
            elif "House Information" in h3.text:
                house_text = h3.text

        info = main.findAll("div", {"class": "col-md-8"})[0]
        paragraphs = info.findAll("p")
        room = paragraphs[0]
        address = paragraphs[1]

        split = year_text.strip().split(" ")
        start, end = split[len(split) - 3], split[len(split) - 1]

        split = house_text.split("-")
        house = split[1].strip()

        split = room.text.split("  ")
        location = split[0].strip()

        split = address.text.split("  ")
        address = split[0].strip()

    housing = Housing(
        account=g.account.id,
        house=house,
        location=location,
        address=address,
        off_campus=off_campus,
        start=start,
        end=end,
    )

    try:
        sqldb.session.add(housing)
        sqldb.session.commit()
    except IntegrityError:
        sqldb.session.rollback()
        current_result = Housing.query.filter_by(account=g.account.id, start=housing.start).first()
        if current_result:
            if housing.off_campus or (housing.house and housing.location and housing.address):
                current_result.house = house
                current_result.location = location
                current_result.address = address
                current_result.off_campus = off_campus
            sqldb.session.commit()

    if housing.start:
        return jsonify(
            {
                "house": housing.house,
                "room": housing.location,
                "address": housing.address,
                "start": int(housing.start),
                "end": int(housing.end),
                "off_campus": housing.off_campus,
            }
        )
    else:
        return jsonify({"error": "Unable to parse HTML."}), 400


@app.route("/housing", methods=["GET"])
@auth()
def get_housing_info():
    today = datetime.today()
    year = today.year if today.month > 5 else today.year - 1
    housing = Housing.query.filter_by(account=g.account.id, start=year).first()
    if housing:
        return jsonify(
            {
                "result": {
                    "house": housing.house,
                    "room": housing.location,
                    "address": housing.address,
                    "start": housing.start,
                    "end": housing.end,
                    "off_campus": housing.off_campus,
                }
            }
        )
    else:
        return jsonify({"result": None})


@app.route("/housing/delete", methods=["POST"])
@auth()
def delete_housing_info():
    Housing.query.filter_by(account=g.account.id).delete()
    sqldb.session.commit()
    return jsonify({"success": True})


@app.route("/housing/all", methods=["POST"])
@auth()
def add_all_housing_info():
    json_arr = request.get_json()
    for json in json_arr:
        house = json.get("house")
        room = json.get("room")
        address = json.get("address")
        start = json.get("start")
        end = json.get("end")
        off_campus = json.get("off_campus")
        try:
            housing = Housing(
                account=g.account.id,
                house=house,
                location=room,
                address=address,
                off_campus=off_campus,
                start=start,
                end=end,
            )
            sqldb.session.add(housing)
            sqldb.session.commit()
        except IntegrityError:
            sqldb.session.rollback()
            current_result = Housing.query.filter_by(account=g.account.id, start=start).first()
            if current_result:
                current_result.house = house
                current_result.location = room
                current_result.address = address
                current_result.off_campus = off_campus
                sqldb.session.commit()

    return jsonify({"success": True})


def get_details_for_location(location):
    """
    Ex: 403 Butcher (Bed space: a)
    Returns 403, 4, Butcher
    """
    split = location.split(" ")
    room = int(split[0].strip())
    floor = math.floor(room / 100)
    section = split[1].strip()

    return room, floor, section
