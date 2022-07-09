import traceback
from bs4 import BeautifulSoup
import pandas as pd
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
import pathlib
from . import helpers
from datetime import datetime
import numpy as np


class Scraper:
    def __init__(self):
        # Selenium Info
        self.selenium_options = Options()
        self.selenium_options.headless = True
        self.selenium_instructions = ['window.scrollTo(1,6000)']
        self.selenium_delay = 30
        self.chromedriver_path = '/Users/Jared/dev_work/chromedriver'

    def get_with_selenium(self, url):
        driver = webdriver.Chrome(
            executable_path=self.chromedriver_path,
            options=self.selenium_options
        )
        driver.get(url)
        for instruction in self.selenium_instructions:
            driver.execute_script(instruction)
        time.sleep(self.selenium_delay)  # this seems to work best
        html_source = driver.execute_script("return document.body.innerHTML;")
        driver.quit()
        return html_source

    def get_with_requests(self, url):
        html_source = requests.get(url).text
        time.sleep(2)
        return html_source


class PfrScraper(Scraper):
    def __init__(self, base_save_loc, build_existing_lkp=False):
        # Bring in Scraper base class to use if needed
        Scraper.__init__(self)
        # Save Locations
        self.base_save_loc = base_save_loc
        self.season_save_loc = base_save_loc+'/pfr_season_summaries'
        self.week_save_loc = base_save_loc+'/pfr_week_summaries'
        self.game_save_loc = base_save_loc+'/pfr_game_summaries'

        # Pro Football Reference Info
        self.base_url = 'https://www.pro-football-reference.com'
        self.season_url = self.base_url + '/years'

        # Using Filesystem as DB for now - Maybe create a SQLLite db instead in the future? - TODO
        # self.team_abbrevs

    def build_lkp(self):
        """
        If called, this method builds up a dictionary of information on each season and week of html files already pulled and saved previously
        """
        print('build_existing_lkp is a future feature')

    def request_season_summaries(self, seasons, overwrite_existing=False, suppress_skipped_msg=True):
        """
        Input Range object, html files to be saved in season_save_location folder
        """
        # TODO: Add input checks for type (list or range())
        if type(seasons) is int:
            seasons = [seasons]  # Make iterable

        for season in seasons:
            # Check if this season was already requested
            save_loc = f'{self.season_save_loc}/{season}_summary.html'
            season_html = self.load_season_summary(season)
            if (not overwrite_existing) & (season_html is not None):
                if not suppress_skipped_msg:
                    print(
                        f'{season} Season Summary already saved locally, skipping')
                continue
            # Go forward with request (with Selenium) and save
            print(f'Requesting {season} Season Summary')
            html = self.get_with_selenium(f'{self.season_url}/{season}')
            print(f'Received, Saving to {save_loc}')
            with open(save_loc, 'w+') as f:
                f.write(html)

    def load_season_summary(self, season):
        save_loc = f'{self.season_save_loc}/{season}_summary.html'
        if not pathlib.Path(save_loc).is_file():
            return None
        with open(save_loc) as f:
            return f.read()

    def scrape_season_summary(self, season_html):
        if season_html is None:
            print(f'{season} Season not yet requested - Requesting now...')
            self.request_season_summaries(seasons=[season])
            return None

        seasoned_soup = BeautifulSoup(season_html, 'html.parser')
        season = seasoned_soup.find(id='meta').find_all(
            'div')[1].find('h1').find('span').get_text()
        week_elements = seasoned_soup.find(id='div_week_games').find_all('a')
        num_weeks = len(week_elements)
        week_summary_links = []
        week_labels = []
        for week in range(1, num_weeks+1):
            week_summary_links.append(week_elements[week-1]['href'])
            week_labels.append(week_elements[week-1].get_text())
        df = pd.DataFrame({
            'season': int(season),
            'num_weeks': num_weeks,
            'week_summary_links': ','.join(week_summary_links),
            'week_labels': ','.join(week_labels)},
            index=[0]
        )
        return df

    def request_week_summaries(self, season, weeks='all', overwrite_existing=False, suppress_skipped_msg=True):
        # Input Check:
        if type(weeks) is int:
            weeks = [weeks]  # Make weeks iterable

        # Check if this season was already requested
        season_html = self.load_season_summary(season)
        if season_html is None:
            print(f'First Need to Request {season} Season Summary')
            self.request_season_summaries([season])
            season_html = self.load_season_summary(season)

        # Get weeks list
        season_summary_df = self.scrape_season_summary(season_html)
        if weeks == 'all':
            weeks = range(1, season_summary_df['num_weeks'][0])
        week_extensions = season_summary_df['week_summary_links'][0].split(',')
        for week in weeks:
            week_html = self.load_week_summary(
                season=season_summary_df['season'][0],
                week=week)
            if (not overwrite_existing) & (week_html is not None):
                if not suppress_skipped_msg:
                    print(
                        f'{season} Season, Week {week} already requested, skipping')
                continue
            # Go forward with request (with 'requests') and save
            print(f'Requesting {season} Season, Week {week} Summary')
            week_html = self.get_with_requests(
                self.base_url+week_extensions[week-1])
            print(
                f'Received, Saving to {self.week_save_loc}/{season}_week{week}_summary.html')
            with open(f'{self.week_save_loc}/{season}_week{week}_summary.html', 'w+') as f:
                f.write(week_html)

    def load_week_summary(self, season, week):
        save_loc = f'{self.week_save_loc}/{season}_week{week}_summary.html'
        if not pathlib.Path(save_loc).is_file():
            return None
        with open(save_loc) as f:
            return f.read()

    def scrape_week_summary(self, week_html):
        if week_html is None:
            raise ValueError(
                'Week not yet requested - Please request before attempting scrape')

        week_soup = BeautifulSoup(week_html, 'html.parser')
        game_link_elements = week_soup.find_all('td', class_='right gamelink')
        game_links = []
        for game_link_element in game_link_elements:
            game_links.append(game_link_element.find('a')['href'])
        df = pd.DataFrame({
            'num_games': len(game_link_elements),
            'game_summary_links': ','.join(game_links)},
            index=[0]
        )
        return df

    def get_game_summaries(self, seasons='all', weeks='all', teams='all', overwrite_existing=False, save_html=True):
        try:
            # Input Check:
            if type(seasons) is int:
                seasons = [seasons]
            if type(weeks) is int:
                weeks = [weeks]
            if teams != 'all':
                print('Specific Team Selection not allowed at this point.')
                return None

            game_summaries_df = None
            for season in seasons:
                # Get Season Summary
                print(f'--- getting season {season} ---')
                season_sum_html = self.load_season_summary(season)
                if season_sum_html is None:
                    self.request_season_summaries([season])
                    season_sum_html = self.load_season_summary(season)
                season_sum_df = self.scrape_season_summary(season_sum_html)
                num_weeks = season_sum_df['num_weeks'][0]
                if weeks == 'all':
                    weeks_range = range(1, num_weeks+1)
                else:
                    weeks_range = weeks
                week_labels = season_sum_df['week_labels'][0].split(',')
                # Get Week Summaries
                for week in weeks_range:
                    if week > num_weeks:
                        break
                    print(f'-- getting week: {week} --')
                    week_sum_html = self.load_week_summary(
                        season=season, week=week)
                    if week_sum_html is None:
                        self.request_week_summaries(season=season, weeks=week)
                        week_sum_html = self.load_week_summary(
                            season=season, week=week)
                    week_sum_df = self.scrape_week_summary(week_sum_html)
                    game_links = week_sum_df['game_summary_links'][0].split(
                        ',')
                    for game_link in game_links:
                        # Add Additional Info At this level
                        game_summary_df = pd.DataFrame()
                        game_summary_df['pfr_link'] = [game_link]
                        game_summary_df['season'] = season
                        game_summary_df['week_no'] = week
                        game_summary_df['week_label'] = week_labels[week-1]
                        # Parse inputted attributes
                        pfr_game_id = game_summary_df['pfr_link'][0].split(
                            '/')[2].split('.')[0]
                        game_summary_df['pfr_game_id'] = pfr_game_id
                        game_summary_df['is_playoff_game'] = ~game_summary_df['week_label'].str.contains(
                            'Week')
                        # Request html if needed
                        game_html = self.load_game_summary(pfr_game_id)
                        if game_html is None:
                            for attempt in range(1, 4):
                                try:
                                    print(
                                        f'- requesting game: {game_link} (attempt {attempt}/3) -')
                                    game_html = self.get_with_selenium(
                                        self.base_url+game_link)
                                    with open(f'{self.game_save_loc}/{pfr_game_id}.html', 'w+') as f:
                                        f.write(game_html)
                                    break
                                except:
                                    if attempt == 3:
                                        raise ValueError(
                                            'Attempted Request too many times')
                                    else:
                                        print(traceback.format_exc())
                                        continue
                        else:
                            print(f'- loaded saved game: {game_link} -')
                        game_summary_df = self.scrape_game_summary(
                            game_html, game_summary_df)

                        if game_summaries_df is None:
                            game_summaries_df = game_summary_df
                            continue
                        game_summaries_df = pd.concat(
                            [game_summaries_df, game_summary_df], ignore_index=True)
            return game_summaries_df
        except:
            print('ran into exception -- exiting')
            print(traceback.format_exc())
            return game_summaries_df
        # TODO - save summary and be able to load instead of request every time

    def load_game_summary(self, pfr_game_id):
        save_loc = f'{self.game_save_loc}/{pfr_game_id}.html'
        if not pathlib.Path(save_loc).is_file():
            return None
        with open(save_loc) as f:
            return f.read()

    def scrape_game_summary(self, game_html, game_summary_df):
        # Use BS to parse html
        game_soup = BeautifulSoup(game_html, 'html.parser')

        ## Scorebox Parsing ##
        scorebox_text_list = [x.get_text() for x in game_soup.find(
            class_='scorebox_meta').find_all('div')]

        # Datetime info
        date_of_game = scorebox_text_list[0]
        date_of_game_split = date_of_game.split(' ')
        day_of_week = date_of_game_split[0]
        game_summary_df['day_of_week'] = day_of_week

        month_str = date_of_game_split[1]
        month_str_full = helpers.month_abrv_lkp(month_str)
        day_num = date_of_game_split[2][:-1]
        year = date_of_game_split[3]

        # Check if Datetime info is in scorebox, if not, return np.nan
        exists, start_time = helpers.check_if_startswith(
            'Start Time: ', scorebox_text_list)
        if exists:
            hh_mm = start_time[:-2]
            ampm = start_time[-2:].upper()
            date_str = f"{day_num}-{month_str}-{year} {hh_mm} {ampm}"
            dt_obj = datetime.strptime(date_str, "%d-%b-%Y %I:%M %p")
            game_summary_df['game_start_datetime'] = dt_obj
        else:
            game_summary_df['game_start_datetime'] = np.nan

        # Get stadium (if exists)
        exists, stadium = helpers.check_if_startswith(
            'Stadium: ', scorebox_text_list)
        if exists:
            game_summary_df['stadium'] = stadium
        else:
            game_summary_df['stadium'] = np.nan

        # Get Attendance (if exists)
        exists, attendance = helpers.check_if_startswith(
            'Attendance: ', scorebox_text_list)
        if exists:
            game_summary_df['attendance'] = attendance
        else:
            game_summary_df['attendance'] = np.nan

        # Get Game Length (if exists)
        exists, game_length = helpers.check_if_startswith(
            'Time of Game: ', scorebox_text_list)
        if exists:
            game_length_split = game_length.split(':')
            hrs = float(
                game_length_split[0])+round(float(game_length_split[1])/60, ndigits=3)
            game_summary_df['game_duration_hrs'] = hrs
        else:
            game_summary_df['game_duration_hrs'] = np.nan

        # Parse Out Game Info Table Attributes
        tbl = game_soup.find('table', id='game_info')
        game_info_tbl = pd.read_html(str(tbl))[0]
        # Coin Toss Winner
        tf, ct_winner = helpers.game_info_check(
            header='Won Toss', tbl=game_info_tbl)
        if tf:
            game_summary_df['coin_toss_winner'] = ct_winner
        else:
            game_summary_df['coin_toss_winner'] = np.nan

        # Roof
        tf, roof = helpers.game_info_check(header='Roof', tbl=game_info_tbl)
        if tf:
            game_summary_df['roof'] = roof
        else:
            game_summary_df['roof'] = np.nan

        # Surface
        tf, surface = helpers.game_info_check(
            header='Surface', tbl=game_info_tbl)
        if tf:
            game_summary_df['surface'] = surface
        else:
            game_summary_df['surface'] = np.nan

        # Weather
        tf, weather = helpers.game_info_check(
            header='Weather', tbl=game_info_tbl)
        if tf:
            game_summary_df['weather'] = weather
        else:
            game_summary_df['weather'] = np.nan

        # Game Summary Info
        # Get Linescore
        linescore = str(
            game_soup.find('table', class_='linescore nohover stats_table no_freeze'))
        linescore_df = pd.read_html(linescore)[0]

        # Check Overtime
        if 'OT' in linescore_df.columns:
            game_summary_df['overtime_played'] = True
            ot_score_home = linescore_df['OT'][1]
            ot_score_away = linescore_df['OT'][0]
        else:
            game_summary_df['overtime_played'] = False
            ot_score_home = 0
            ot_score_away = 0

        game_summary_df['home_team'] = linescore_df['Unnamed: 1'][1]

        # Get Coach:
        coach = game_soup.find('div', class_='scorebox').find_all('div')[
            7].get_text()
        if coach.startswith('Coach: '):
            game_summary_df['home_team_coach'] = coach[len('Coach: '):]
        else:
            game_summary_df['home_team_coach'] = np.nan

        # Get W/L/T
        home_team_wl = game_soup.find('div', class_='scorebox').find_all('div')[
            0].find_all('div')[4].get_text().split('-')
        game_summary_df['home_team_wins'] = home_team_wl[0]
        game_summary_df['home_team_losses'] = home_team_wl[1]
        if len(home_team_wl) == 3:
            game_summary_df['home_team_ties'] = home_team_wl[2]
        else:
            game_summary_df['home_team_ties'] = 0

        game_summary_df['home_team_score_q1'] = linescore_df['1'][1]
        game_summary_df['home_team_score_q2'] = linescore_df['2'][1]
        game_summary_df['home_team_score_q3'] = linescore_df['3'][1]
        game_summary_df['home_team_score_q4'] = linescore_df['4'][1]
        game_summary_df['home_team_score_overtime'] = ot_score_home
        game_summary_df['home_team_score_final'] = linescore_df['Final'][1]
        game_summary_df['away_team'] = linescore_df['Unnamed: 1'][0]

        # Get Coach:
        coach = game_soup.find('div', class_='scorebox').find_all('div')[
            15].get_text()
        if coach.startswith('Coach: '):
            game_summary_df['away_team_coach'] = coach[len('Coach: '):]
        else:
            game_summary_df['away_team_coach'] = np.nan

        away_team_wl = game_soup.find('div', class_='scorebox').find_all('div')[
            8].find_all('div')[4].get_text().split('-')
        game_summary_df['away_team_wins'] = away_team_wl[0]
        game_summary_df['away_team_losses'] = away_team_wl[1]
        if len(away_team_wl) == 3:
            game_summary_df['away_team_ties'] = away_team_wl[2]
        else:
            game_summary_df['away_team_ties'] = 0
        game_summary_df['away_team_score_q1'] = linescore_df['1'][0]
        game_summary_df['away_team_score_q2'] = linescore_df['2'][0]
        game_summary_df['away_team_score_q3'] = linescore_df['3'][0]
        game_summary_df['away_team_score_q4'] = linescore_df['4'][0]
        game_summary_df['away_team_score_overtime'] = ot_score_away
        game_summary_df['away_team_score_final'] = linescore_df['Final'][0]

        return game_summary_df
