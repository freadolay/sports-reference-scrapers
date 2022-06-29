from bs4 import BeautifulSoup
import pandas as pd
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
import pathlib


class Scraper:
    def __init__(self):
        # Selenium Info
        self.selenium_options = Options()
        self.selenium_options.headless = True
        self.selenium_instructions = ['window.scrollTo(1,5000)']
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
            season_sum_html = self.load_season_summary(season)
            if season_sum_html is None:
                self.request_season_summaries([season])
                season_sum_html = self.load_season_summary(season)
            season_sum_df = self.scrape_season_summary(season_sum_html)
            num_weeks = season_sum_df['num_weeks']
            week_labels = week_sum_df['week_labels'][0].split(',')
            # Get Week Summaries
            for week in range(1, num_weeks+1):
                week_sum_html = self.load_week_summary(
                    season=season, week=week)
                if week_sum_html is None:
                    self.request_week_summaries(season=season, weeks=week)
                    week_sum_html = self.load_week_summary(
                        season=season, week=week)
                week_sum_df = self.scrape_week_summary(week_sum_html)
                game_links = week_sum_df['game_summary_links'][0].split(',')
                for game_link in game_links:
                    game_html = self.get_with_requests(
                        self.base_url+game_link)
                    # Add Additional Info At this level
                    game_summary_df = pd.DataFrame()
                    game_summary_df['pfr_link'] = [game_link]
                    game_summary_df['week_no'] = week
                    game_summary_df['week_label'] = week_labels[week-1]
                    game_summary_df = self.scrape_game_summary(
                        game_html, game_summary_df)

                    if game_summaries_df is None:
                        game_summaries_df = game_summary_df
                    game_summaries_df = pd.concat(
                        [game_summaries_df, game_summary_df], ignore_index=True)
                    # TODO - save summary and be able to load instead of request every time

    def scrape_game_summary(self, game_html, game_summary_df):
        game_soup = BeautifulSoup(game_html, 'html.parser')
        # Take link and parse ID
        game_summary_df['game_id']

        return None
