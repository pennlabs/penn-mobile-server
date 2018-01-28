import unittest
import mock
import server
import json
import datetime

from server.models import sqldb, LaundrySnapshot

# Fake
authHeaders = [(
    'cookie',
    '_shibsession_64656661756c7468747470733a2f2f706f6f7272696368617264736c69737448c36f6d2f73686962695c6c657468=_ddb1128649n08aa8e7a462de9970df3e'
)]
AUTH_TOKEN = b'5e625cf41e3b7838c79b49d890a203c568a44c3b27362b0a06ab6f08bec8f677'


class MobileAppApiTests(unittest.TestCase):
    def setUp(self):
        server.app.config['TESTING'] = True

    @classmethod
    def setUpClass(self):
        with server.app.test_request_context():
            for x in range(0, 24 * 60, 60):
                item = LaundrySnapshot(
                    date=datetime.date(2017, 1, 1),
                    time=x,
                    room=1,
                    washers=3,
                    dryers=3,
                    total_washers=3,
                    total_dryers=3
                )
                sqldb.session.add(item)
            for x in range(0, 24 * 60, 60):
                item = LaundrySnapshot(
                    date=datetime.date(2017, 1, 1) - datetime.timedelta(days=7),
                    time=x,
                    room=1,
                    washers=0,
                    dryers=0,
                    total_washers=3,
                    total_dryers=3
                )
                sqldb.session.add(item)
            sqldb.session.commit()

    def testDiningVenues(self):
        with server.app.test_request_context():
            # Simple test. Did the request go through?
            venue_data = server.dining.retrieve_venues()
            venue_dict = json.loads(venue_data.data.decode('utf8'))
            venues = venue_dict['document']['venue']
            self.assertTrue(len(venues[0]['venueType']) > 0)

    def testDiningV2Venues(self):
        with server.app.test_request_context():
            venue_res = server.dining.retrieve_venues_v2()
            venue_dict = json.loads(venue_res.data.decode('utf8'))
            self.assertEquals("1920 Commons",
                              venue_dict["document"]["venue"][0]["name"])

    def testDiningV2Menu(self):
        with server.app.test_request_context():
            menu_res = server.dining.retrieve_menu_v2('593', '2016-02-08')
            menu_dict = json.loads(menu_res.data.decode('utf8'))
            self.assertTrue(
                len(menu_dict["days"][0]["cafes"]["593"]["dayparts"]) > 0)

    def testDiningV2Hours(self):
        with server.app.test_request_context():
            hours_res = server.dining.retrieve_hours_v2('593')
            hours_dict = json.loads(hours_res.data.decode('utf8'))
            self.assertEquals("1920 Commons",
                              hours_dict["cafes"]["593"]["name"])

    def testDiningV2Item(self):
        with server.app.test_request_context():
            item_res = server.dining.retrieve_item_v2('3899220')
            item_dict = json.loads(item_res.data.decode('utf8'))
            self.assertEquals("tomato tzatziki sauce and pita",
                              item_dict["items"]["3899220"]["label"])

    def testDiningWeeklyMenu(self):
        with server.app.test_request_context():
            menu_res = server.dining.retrieve_weekly_menu('593')
            menu_dict = json.loads(menu_res.data.decode('utf8'))
            self.assertTrue(
                "1920 Commons" in menu_dict["Document"]["location"])

    def testDiningDailyMenu(self):
        with server.app.test_request_context():
            menu_res = server.dining.retrieve_daily_menu('593')
            menu_dict = json.loads(menu_res.data.decode('utf8'))
            self.assertEquals("1920 Commons",
                              menu_dict["Document"]["location"])

    def testDirectorySearch(self):
        with server.app.test_request_context('/?name=Zdancewic'):
            res = server.directory.detail_search()
            steve = json.loads(res.data.decode('utf8'))
            self.assertEquals("stevez@cis.upenn.edu",
                              steve["result_data"][0]["list_email"])

    def testDirectoryPersonDetails(self):
        with server.app.test_request_context():
            res = server.directory.person_details(
                "aed1617a1508f282dee235fda2b8c170")
            person_data = json.loads(res.data.decode('utf8'))
            self.assertEquals("STEPHAN A ZDANCEWIC",
                              person_data["detail_name"])

    def testRegistarCourseSearch(self):
        with server.app.test_request_context("/?q=cis 110"):
            res = server.registrar.search()
            course_data = json.loads(res.data.decode('utf8'))
            for val in course_data["courses"]:
                self.assertEquals("110", val["course_number"])

    def testRegistrarCourseSearchNoNumber(self):
        with server.app.test_request_context("/?q=cis"):
            res = server.registrar.search()
            course_data = json.loads(res.data.decode('utf8'))
            for val in course_data["courses"]:
                self.assertEquals("CIS", val["course_department"])

    def testBuildingSearch(self):
        with server.app.test_request_context("/?q=Towne"):
            res = server.buildings.building_search()
            building_data = json.loads(res.data.decode('utf8'))
            self.assertEquals(building_data["result_data"][0]["title"],
                              "Towne")

    def testTransitStopInventory(self):
        with server.app.test_request_context():
            res = json.loads(server.transit.transit_stops().data.decode(
                'utf8'))
            self.assertTrue(len(res["result_data"]) > 0)

# def testTransitBasicRouting(self):
#   with server.app.test_request_context("/?latFrom=39.9529075495845&lonFrom=-75.1925700902939&latTo=39.9447689912513&lonTo=-75.1751947402954"):
#     res = json.loads(server.transit.fastest_route().data.decode('utf8'))['result_data']
#     self.assertEquals("Food Court, 3409 Walnut St.", res['path'][0]['BusStopName'])
#     self.assertEquals("20th & South", res['path'][-1]['BusStopName'])
#     self.assertEquals("PennBUS East", res['route_name'])

    def fakeLaundryGet(url, *args, **kwargs):
        if "suds.kite.upenn.edu" in url:
            with open("tests/laundry_snapshot.html", "rb") as f:
                m = mock.MagicMock(content=f.read())
            return m
        else:
            raise NotImplementedError

    @mock.patch("penn.laundry.requests.get", fakeLaundryGet)
    def testLaundryAllHalls(self):
        with server.app.test_request_context():
            res = json.loads(server.laundry.all_halls().data.decode('utf8'))[
                'halls']
            self.assertTrue(len(res) > 45)
            self.assertTrue('English House' in res)
            for info in res.values():
                for t in ['washers', 'dryers']:
                    self.assertTrue(info[t]['running'] >= 0)
                    self.assertTrue(info[t]['offline'] >= 0)
                    self.assertTrue(info[t]['out_of_order'] >= 0)
                    self.assertTrue(info[t]['open'] >= 0)

    @mock.patch("requests.get", fakeLaundryGet)
    def testLaundryOneHall(self):
        with server.app.test_request_context():
            res = json.loads(server.laundry.hall(26).data.decode('utf8'))
            self.assertEquals(res['hall_name'], 'Harrison Floor 20')

    def testLaundryUsage(self):
        with server.app.test_request_context():
            request = server.laundry.usage(20, 2017, 1, 1)
            res = json.loads(request.data.decode('utf8'))
            self.assertEquals(res['hall_name'], 'Harrison Floor 08')
            self.assertEquals(res['location'], 'Harrison')
            self.assertEquals(res['day_of_week'], 'Sunday')
            self.assertEquals(res['end_date'], '2017-01-01')
            self.assertEquals(len(res['washer_data']), 27)
            self.assertEquals(len(res['dryer_data']), 27)

    def testLaundryDatabase(self):
        with server.app.test_request_context():
            request = server.laundry.usage(1, 2017, 1, 1)
            res = json.loads(request.data.decode('utf8'))
            self.assertEquals(res['total_number_of_washers'], 3)
            self.assertEquals(res['total_number_of_dryers'], 3)
            for x in range(0, 23):
                self.assertEquals(res['washer_data'][str(x)], 1.5)
                self.assertEquals(res['dryer_data'][str(x)], 1.5)

    def testStudyspacesIDs(self):
        with server.app.test_request_context():
            res = json.loads(server.studyspaces.display_id_pairs().data.decode(
                'utf8'))
            self.assertTrue(len(res) > 0)
            for i in res['locations']:
                self.assertTrue(i['id'] > 0)
                self.assertTrue(i['name'])
                self.assertTrue(i['service'])

    def testStudyspaceExtraction(self):
        with server.app.test_request_context():
            res = json.loads(
                server.studyspaces.parse_times(2683).data.decode('utf8'))
            self.assertTrue(len(res) > 0)
            self.assertTrue("date" in res)
            self.assertTrue("location_id" in res)
            self.assertTrue("rooms" in res)

    def testWeather(self):
        with server.app.test_request_context():
            res = json.loads(server.weather.retrieve_weather_data()
                             .data.decode('utf8'))
            self.assertTrue(len(res) > 0)
            s = res['weather_data']
            self.assertTrue("clouds" in s)
            self.assertTrue("name" in s)
            self.assertTrue("coord" in s)
            self.assertTrue("sys" in s)
            self.assertTrue("base" in s)
            self.assertTrue("visibility" in s)
            self.assertTrue("cod" in s)
            self.assertTrue("weather" in s)
            self.assertTrue("dt" in s)
            self.assertTrue("main" in s)
            self.assertTrue("id" in s)
            self.assertTrue("wind" in s)

    def testCalendarToday(self):
        with server.app.test_request_context():
            res = json.loads(server.calendar3year.pull_today().data.decode(
                'utf8'))
            s = res['calendar']
            today = datetime.datetime.now().date()
            for event in s:
                self.assertTrue("end" in event)
                self.assertTrue("name" in event)
                self.assertTrue("start" in event)
                d = datetime.datetime.strptime(event['start'],
                                               "%Y-%m-%d").date()
                self.assertTrue((d - today).total_seconds() <= 1209600)

    def testCalendarDate(self):
        with server.app.test_request_context():
            ind = "2017-01-01"
            chosen_date = datetime.date(2017, 1, 1)
            res = json.loads(
                server.calendar3year.pull_date(ind).data.decode('utf8'))
            s = res['calendar']
            for event in s:
                self.assertTrue("end" in event)
                self.assertTrue("name" in event)
                self.assertTrue("start" in event)
                d = datetime.datetime.strptime(event['start'],
                                               "%Y-%m-%d").date()
                self.assertTrue((d - chosen_date).total_seconds() <= 1209600)

    def testAuth(self):
        with server.app.test_request_context(headers=authHeaders):
            authToken = server.auth.auth()
            self.assertEquals(AUTH_TOKEN, authToken)

    def testTokenValidation(self):
        with server.app.test_request_context(headers=authHeaders):
            server.auth.auth()
            res = json.loads(
                server.auth.validate(AUTH_TOKEN).data.decode('utf8'))
            self.assertEquals(res['status'], 'valid')

    def testInvalidTokenValidation(self):
        with server.app.test_request_context(headers=authHeaders):
            server.auth.auth()
            res = json.loads(
                server.auth.validate("badtoken").data.decode('utf8'))
            self.assertEquals(res['status'], 'invalid')

    def testTokenValidationNoHttps(self):
        with server.app.test_request_context(headers=authHeaders):
            server.app.config['TESTING'] = False
            server.auth.auth()
            res = json.loads(
                server.auth.validate(AUTH_TOKEN).data.decode('utf8'))
            self.assertEquals(res['status'], 'insecure access over http')


if __name__ == '__main__':
    unittest.main()
