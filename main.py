from pytz import timezone
import numpy
import pandas as pd
import os
import time
import requests
import streamlit as st
import datetime

BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAPg%2BbgEAAAAAMjH78w4rLztU%2F4s%2FksZ37qb99Kg%3D7JzYNSBb9T5vFAeh4YdSKqbXF3fxvJTIcXDjV9xpTRQFt2Qiev"

responded = False
data = {}
tz = timezone('US/Eastern')

os.environ['TZ'] = 'America/New_York'
if hasattr(time, 'tzset') and callable(getattr(time, 'tzset')):
    time.tzset()

def create_headers():
    return {"Authorization": "Bearer " + BEARER_TOKEN}


def create_params(keyword_params, start_datetime_params, end_datetime_params, max_results_params, sort_order_params, is_verified):
    search_url = "https://api.twitter.com/2/tweets/search/recent?"

    query_params = {'query': keyword_params,
                    'start_time': start_datetime_params.isoformat('T'),
                    'end_time': end_datetime_params.isoformat('T'),
                    'max_results': max_results_params,
                    'sort_order': sort_order_params.lower(),
                    'expansions': 'author_id,geo.place_id',
                    'tweet.fields': 'id,text,author_id,in_reply_to_user_id,geo,conversation_id,created_at,lang,public_metrics,referenced_tweets,reply_settings,source',
                    'user.fields': 'id,name,username,created_at,description,public_metrics,verified,location',
                    'place.fields': 'full_name,id,country,country_code,geo,name,place_type',
                    'next_token': {}}

    if is_verified:
        query_params['query'] = query_params['query'] + " is:verified"

    return search_url, query_params


def connect_to_endpoint(url, headers, params):
    response = requests.request("GET", url, headers=headers, params=params)
    # print("Endpoint Response Code: " + str(response.status_code))
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
    return response.json()


def get_data(keyword_params, start_datetime_params, end_datetime_params, max_results_params, sort_order_params, is_verified=False):
    headers = create_headers()
    request = create_params(keyword_params, start_datetime_params, end_datetime_params, max_results_params,
                            sort_order_params, is_verified)
    response = connect_to_endpoint(request[0], headers, request[1])

    global responded
    global data
    data = response


def get_local(address):
    url = 'https://nominatim.openstreetmap.org/search/' + address + '?format=json'
    response = requests.get(url)
    res_js = response.json()
    if response.status_code != 200 or len(res_js) == 0:
        # raise Exception(response.status_code, response.text)
        return ''
    return [float(res_js[0]["lat"]), float(res_js[0]["lon"])]


st.set_page_config(page_title="Twitter Filter", page_icon="🦾", layout="centered")

st.title("🦾 Twitter Filter")

st.markdown("This web app gets the most recent twitter posts, filtering by the fields you enter, and displays different" +
        " demographic data about them.")

form = st.form(key="annotation")

with form:
    cols = st.columns(1)
    keyword = cols[0].text_input("Keyword: ")

    cols = st.columns(1)
    tweet_amount = cols[0].select_slider(
        "Amount of Tweets", numpy.arange(10, 101), value=55
    )

    cols = st.columns(1)
    cols[0].text("Please enter the earliest date/time you want results for.")

    cols = st.columns((1, 1))
    start_date = cols[0].date_input("Start date: ", value=tz.localize(datetime.datetime.now() - datetime.timedelta(days=6)))
    start_time = cols[1].time_input("Start time: ", value=datetime.time(hour=0, minute=0))

    cols = st.columns(1)
    cols[0].text("Please enter the latest date/time you want results for.")

    cols = st.columns((1, 1))
    end_date = cols[0].date_input("End date: ", value=datetime.datetime.now(tz))
    m = datetime.datetime.now(tz).minute - 10
    h = datetime.datetime.now(tz).hour
    if m < 0:
        m += 60
        h -= 1

    end_time = cols[1].time_input("End time: ", value=datetime.time(hour=h, minute=m))

    cols = st.columns(1)
    sort_order = cols[0].selectbox("Sort Order: ", ["Recency", "Relevancy"])

    cols = st.columns((1, 1))
    only_verified = cols[0].checkbox("Only Verified Users")

    submitted = st.form_submit_button(label="Submit")

if submitted:
    start_datetime = tz.localize(datetime.datetime(year=start_date.year, month=start_date.month, day=start_date.day,
                                       hour=start_time.hour, minute=start_time.minute))
    end_datetime = tz.localize(datetime.datetime(year=end_date.year, month=end_date.month, day=end_date.day, hour=end_time.hour,
                                     minute=end_time.minute))

    if end_datetime >= start_datetime:
        if start_datetime >= tz.localize(datetime.datetime.now() - datetime.timedelta(days=7)):
            if end_datetime < tz.localize(datetime.datetime.now() - datetime.timedelta(minutes=10)):
                if keyword != '':
                    get_data(keyword, start_datetime, end_datetime, tweet_amount, sort_order, only_verified)
                    if "meta" in data and data['meta']['result_count'] == 0:
                        st.warning("There were no tweets that fit your options.")
                    else:
                        st.balloons()
                        st.success("Your information was retrieved for a total of " + str(data['meta']['result_count']) + " tweets!")
                        responded = True
                else:
                    st.error("You must provide a keyward to search on!")
            else:
                st.error("Your end date/time has to be 10 minutes before the current time! (" + (
                    datetime.datetime.now(tz).strftime("%m/%d/%Y %H:%M")) + ")")
        else:
            st.error("Your start date/time has to be on/after " + (
                        tz.localize(datetime.datetime.now() - datetime.timedelta(days=6))).strftime("%m/%d/%Y"))
    else:
        st.error("Your end date/time is before your start date/time!")

if responded:

    user_metrics_expander = st.expander("View metrics data of the users")
    with user_metrics_expander:
        user_data = []

        for p in data["includes"]["users"]:
            if "public_metrics" in p:
                i = p['public_metrics']
                user_data.append([i['followers_count'], i['following_count'], i['tweet_count'], i['listed_count']])

        df = pd.DataFrame(
            user_data,
            columns=['Followers Count', 'Following Count', 'Tweet Count', 'Listed Count'])

        st.info(str(len(user_data)) + " tweets were used! (Other tweets were not applicable)")
        st.dataframe(df)

    user_created_expander = st.expander("View account created year of the users")
    with user_created_expander:
        user_data = {}

        for p in data["includes"]["users"]:
            if "created_at" in p:
                c = p['created_at']
                dt = datetime.datetime.fromisoformat(c[0:-1])
                if dt.year in user_data:
                    user_data[dt.year] += 1
                else:
                    user_data[dt.year] = 1

        user_data_array = []
        amount = 0

        for el in user_data:
            user_data_array.append([user_data[el]])
            amount += user_data[el]

        df = pd.DataFrame(user_data_array, index=list(user_data.keys()), columns=["Amount"])

        st.info(str(amount) + " tweets were used! (Other tweets were not applicable)")
        st.line_chart(df)

    user_platform_expander = st.expander("View the platform the users are using")
    with user_platform_expander:
        user_data = {"iPhone": 0, "Android": 0, "Web App": 0, "Other": 0}

        for p in data["data"]:
            if "source" in p:
                s = p['source']
                if "iPhone" in s:
                    user_data["iPhone"] += 1
                elif "Android" in s:
                    user_data["Android"] += 1
                elif "Web App" in s:
                    user_data["Web App"] += 1
                else:
                    user_data["Other"] += 1

        user_data_array = []
        amount = 0

        for el in user_data:
            user_data_array.append([user_data[el]])
            amount += user_data[el]

        df = pd.DataFrame(user_data_array, index=list(user_data.keys()), columns=["Amount"])

        st.info(str(amount) + " tweets were used! (Other tweets were not applicable)")
        st.bar_chart(df)

    location_expander = st.expander("View location of the users")
    with location_expander:
        locations = []
        amount = 0

        for p in data["includes"]["users"]:
            if "location" in p:
                local = get_local(p['location'])
                if local != '':
                    amount += 1
                    locations.append(local)

        df = pd.DataFrame(locations, columns=['lat', 'lon'])

        st.info(str(amount) + " tweets were used! (Other tweets were not applicable)")
        st.map(df)
