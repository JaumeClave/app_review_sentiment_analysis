# %%
import pandas as pd
import numpy as np
import requests 
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')
import json 
from google_play_scraper import Sort, reviews
import plotly.graph_objects as go

class app_reviews:
    
    def __init__(self, app_name):
        self.app_name = app_name
    
    ## Function to get app id through app name
    def android_app_id(self):

        url = f'https://play.google.com/store/search?q={self.app_name}&c=apps'
        resp = requests.get(url)
        soup = BeautifulSoup(resp.content, features = 'html')

        links = list()

        data = soup.findAll("div", {"class": "ImZGtf mpg5gc"})
        for div in data:
            a_tag = div.findAll('a')
            for href in a_tag[:1]:
                links.append(href['href'])

        links = [char.replace('/store/apps/details?id=', '') for char in links]
        app_id = links[0]

        return app_id

    
    ## Function to get similar apps based on names
    def android_similar_apps(self, app_id):

        url = f'https://play.google.com/store/apps/details?id={app_id}'
        resp = requests.get(url)
        soup = BeautifulSoup(resp.content, features = 'html')

        links = list()

        data = soup.findAll("div", {"class": "WHE7ib mpg5gc"})
        for div in data:
            a_tag = div.findAll('a')
            for href in a_tag:
                links.append(href['href'])

        links = set(links)
        links = [s for s in links if "/store/apps/details?id=" in s]
        links = [char.replace('/store/apps/details?id=', '') for char in links]
        similar_apps_df = pd.DataFrame(links)
        similar_apps_df.columns = ['similar_app_id']

        return similar_apps_df
    
    
    ## Function to get app reviews from id
    def get_android_reviews(self, app_id, review_count = 200, country = 'gb'):

        try: 
            result, continuation_token = reviews(
                app_id,
                lang = 'en', 
                country = country, 
                sort = Sort.NEWEST, # defaults to Sort.MOST_RELEVANT, # defaults to 100
                count = review_count
            )

            result, _ = reviews(
                app_id,
                continuation_token = continuation_token # defaults to None(load from the beginning)
            )
        except:
            raise ValueError('the %a has less than %r reviews. Try entering a lower review count.' % (app_id, review_count))


        review_entries = list()

        for entry in range(len(result)):
            review_entry = dict()
            review_entry['updated'] = result[entry]['at']
            review_entry['id'] = result[entry]['reviewId']
            review_entry['content'] = result[entry]['content']
            review_entry['rating'] = result[entry]['score']
            review_entry['version'] = result[entry]['reviewCreatedVersion']
            review_entry['author'] = result[entry]['userName']
            review_entry['OS'] = 'Android'
            review_entry['country'] = country
            review_entries.append(review_entry)

        df = pd.DataFrame(review_entries, columns = ['updated', 'id', 'title', 'content', \
                                                     'rating', 'version', 'author', 'OS', 'country']).set_index('id')
            

        return df
    
    
    ## Function to return app id based on name
    def ios_app_id(self):

        url = f'https://www.apple.com/uk/search/{self.app_name}?sel=explore&src=serp'
        resp = requests.get(url)
        soup = BeautifulSoup(resp.content, features = 'xml')

        links = list()

        data = soup.findAll("div", {"class": "as-explore-product position-1"})
        for div in data:
            a_tag = div.findAll('a')
            for href in a_tag[:10]:
                links.append(href['href'])

        links = [char for char in links if char != '#'] # remove all '#'
        links = [char.replace('https://apps.apple.com/gb/app/', '') for char in links]
        links = [char.replace('id', '') for char in links]

        app_id_df = pd.DataFrame(links)
        app_id_df[['app', 'id']] = app_id_df[0].str.split('/', expand = True)
        app_id_df = app_id_df.drop(app_id_df.columns[0], axis = 1)

        return app_id_df, app_id_df['id'].iloc[0]
    
    
    ## Function to request apple reviews
    def get_ios_reviews(self, app_id, country = 'gb'):
        df = pd.DataFrame()

        count = 1

        for i in range(20):
            url = f'https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/page={count}/xml'
            resp = requests.get(url)
            soup = BeautifulSoup(resp.content, features = 'xml')

            entries = soup.findAll('entry')
            if not entries:
                return df

            review_entries = list()

            for entry in entries:
                review_entry = dict()
                review_entry['updated'] = entry.updated.text
                review_entry['id'] = entry.id.text
                review_entry['title'] = entry.title.text
                review_entry['content'] = entry.content.text
                review_entry['rating'] = entry.rating.text
                review_entry['version'] = entry.version.text
                review_entry['author'] = entry.author.text.split('https:')[0]
                review_entry['OS'] = 'iOS'
                review_entry['country'] = country
                review_entries.append(review_entry)

            review_entries_df = pd.DataFrame(review_entries, columns = ['updated', 'id', 'title', 'content', \
                                                                        'rating', 'version', 'author', 'OS', 'country']\
                                            ).set_index('id')
            df = df.append(review_entries_df)
            count += 1
    
    
    ## to_json (can save as)
    def to_json(self, df_list):
        
        if len(df_list) == 2:
            dataframe = df_list[0].append(df_list[1])
        elif len(df_list) == 1:
            dataframe = df_list[0]
        json_string = dataframe.reset_index().to_json(orient = 'index')
        obj = json.loads(json_string)
        
        return obj      
    
    
    def visualise(self, df_list):
    
        if len(df_list) == 2:
            app_data = df_list[0].append(df_list[1])
        elif len(df_list) == 1:
            app_data = df_list[0]

        app_data['month'] = pd.to_datetime(app_data['updated']).dt.month
        app_data['week'] = pd.to_datetime(app_data['updated']).dt.week
        app_data['year'] = pd.to_datetime(app_data['updated']).dt.year
        app_data['dates'] = app_data['year'] * 100 + app_data['week']
        app_data['week_year'] = pd.to_datetime(app_data['dates'].astype(str) + '0', format='%Y%W%w')
        app_data['month_year'] = app_data['month'].astype(str) + '-' + app_data['year'].astype(str)
        app_data['month_year']  = pd.to_datetime(app_data['month_year'])

        months = set(app_data['month_year'])
        weeks = set(app_data['week_year'])

        if len(months) <= 5:
            time_var = app_data['week_year']
            name = 'week'
            settime = weeks
        else:
            time_var = app_data['month_year']
            name = 'month'
            settime = months

        ratings_df = pd.DataFrame()

        for month in settime:
            df = app_data[time_var == month]
            df['rating'] = df['rating'].astype(int)
            try:
                four_five_val = (len(df[df['rating'] == 5]) + len(df[df['rating'] == 4])) / len(df)
            except:
                four_five_val = 0
            try:
                one_two_val = (len(df[df['rating'] == 1]) + len(df[df['rating'] == 2])) / len(df)
            except:
                one_two_val = 0
            val_df = pd.DataFrame([month, four_five_val, one_two_val]).T
            ratings_df = ratings_df.append(val_df)

        ratings_df.columns = [name, '4/5', '1/2']

        # Create figure with secondary y-axis
        fig = go.Figure()
        # Create traces
        fig.add_trace(go.Scatter(x=ratings_df[name].sort_values(), y=ratings_df['4/5'], 
                                    mode='lines',
                                    name='4 & 5 star reviews', line = dict(color='#33a02c')))

        fig.add_trace(go.Scatter(x=ratings_df[name].sort_values(), y=ratings_df['1/2'],
                                    mode='lines',
                                    name='1 & 2 star reviews', line = dict(color='#e31a1c')))

        fig.update_xaxes(
            rangeslider_visible=True,
            range = (ratings_df[name].min(), ratings_df[name].max()),
            rangeselector=dict(
                buttons=list([
                    dict(count=7, label="7d", step="day", stepmode="backward"),
                    dict(count=30, label="1m", step="day", stepmode="backward"),
                    dict(count=90, label="3m", step="day", stepmode="backward"),
                    dict(count=180, label="6m", step="day", stepmode="backward"),
                    dict(count=365, label="YTD", step="day", stepmode="todate"),
                    dict(count=365, label="1y", step="day", stepmode="backward"),
                    dict(step="all")
                ])
            )
        )

        fig.update_layout(
            title = 'How Happy Are Reviewers With The App?',
            autosize = False,
            width = 950,
            height = 700,
            margin = dict(
                l = 50,
                r = 50,
                b = 50,
                t = 100,
                pad = 2
            ),
            yaxis=dict(tickformat=".0%"),
            template = "plotly_white",
            hovermode='x'
        )


        fig.show()

def get_app_reviews(appname):

    app = app_reviews(appname)

    android_app = app.android_app_id()
    print(f'The android app id for "Airbnb" is: {android_app}')

    similar_android_apps_df = app.android_similar_apps(android_app)

    android_app_reviews_df = app.get_android_reviews(android_app, country = 'gb')

    ios_app = app.ios_app_id()
    ios_app_id = ios_app[1]
    print(f'The ios app id for "Airbnb" is: {ios_app_id}')

    ## Get similar apps (iOS Store)
    similar_ios_apps_df = ios_app[0]

    ## Get app reviews (iOS Store)
    ios_app_reviews_df = app.get_ios_reviews(ios_app_id, country = 'gb')

    ## Visualise ratings over time
    app.visualise([ios_app_reviews_df, android_app_reviews_df])

    ## Save reviews as JSON
    app_review_json = app.to_json([ios_app_reviews_df, android_app_reviews_df])
    print('An example entry from the exported JSON is:', '\n \n', f"{app_review_json['0']}")
# %%
#get_app_reviews('airbnb')

# %%
