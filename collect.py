# -*- coding=utf-8 -*-
#!/usr/bin/env python3

"""
Inspired by [A systematic review on open source clinical software on GitHub for improving software
reuse in smart healthcare](https://www.mdpi.com/2076-3417/9/1/150) by Zhengru Shen and Marco Spruit

@author Simon Renger

"""
from typing import final
from github import Github, enable_console_debug_logging
import pandas as pd
from pathlib import Path
import argparse
import json
import math
import os
import time
from datetime import datetime, timedelta
import copy

# -- Debugger Logger

global__debugger = False


def debug__print(msg):
    print("[DEBUG] {}".format(msg))

# -- utility


def split_time(timerange, splitsize):
    """
    split timerange into multiple timeranges so that each timerange would only contains less than 1000
    repos
    @see https://github.com/ianshan0915/clinical-opensource-projects
    """

    times = timerange.split('..')
    start = times[0]
    end = times[1]
    time_format = '%Y-%m-%d'
    timeranges_year = []
    duration_days = (datetime.strptime(end, time_format) -
                     datetime.strptime(start, time_format)).days
    delta_days = duration_days//splitsize
    for i in range(splitsize):
        if i < splitsize-1:
            end_tmp = datetime.strptime(
                start, time_format) + timedelta(days=delta_days)
            timerange_tmp = start + '..' + end_tmp.strftime(time_format)
            start_tmp = end_tmp + timedelta(days=1)
            start = start_tmp.strftime(time_format)
        else:
            timerange_tmp = start + '..' + end

        timeranges_year.append(timerange_tmp)

    return timeranges_year


def search_time_range_year(type, year):
    """
    get search timerange on a given year
    @see https://github.com/ianshan0915/clinical-opensource-projects
    """
    if type == 1:
        timerange = '<' + str(year) + '-01-01'
    else:
        start = str(year) + '-01-01'
        if year == datetime.now().year:
            end = datetime.now().strftime('%Y-%m-%d')
        else:
            end = str(year) + '-12-31'
        timerange = start + '..' + end

    return timerange

# -- GitHubQuery


class GitHubQuery:
    def __init__(self, token, config):
        self.token = token
        self.read_config(config)
        if "output" in self.config:
            self.output = Path(self.config['output'])
        else:
            self.output = Path("./")
        if token is None:
            self.token = self.config["token"]

    def read_config(self, config):
        fd = open(config, "r")
        data = fd.read()
        fd.close()
        self.config = json.loads(data)

    def connect(self):
        if global__debugger:
            enable_console_debug_logging()
        self.conn = Github(self.token)
        debug__print("Connecting to GitHub")

    def time_range(self, term):
        time_min = self.config['criteria']['time']['min']
        time_max = self.config['criteria']['time']['max']
        timeranges = []
        timerange_pre = search_time_range_year(
            1, time_min)
        query.connect()
        # double-check if the cutoff year is good or not
        search_term = term + " created:"+timerange_pre
        pagedlist_pre = self.conn.search_repositories(
            query=search_term)
        if pagedlist_pre.totalCount > 1000:
            debug__print(
                'the cutoff year is not correct, should choose a time before it')
        elif pagedlist_pre.totalCount > 0:
            timeranges.append(timerange_pre)
        while time_min <= time_max:
            timerange = search_time_range_year(2, time_min)
            # print(timerange)
            search_term = term + " created:"+timerange
            pagedlist_tmp = self.conn.search_repositories(
                query=search_term)
            if pagedlist_tmp.totalCount > 0:
                splitsize = math.ceil(pagedlist_tmp.totalCount/1000) + 2
                timerange_lst = split_time(timerange, splitsize)
                timeranges = timeranges + timerange_lst
            time_min += 1

        return timeranges

    def sleep_time(self):
        """
        Calculate the amount of seconds it needs to wait before remaining rate reset
        """

        tdelta = datetime.fromtimestamp(
            self.conn.rate_limiting_resettime) - datetime.now()

        return tdelta.seconds + 30  # 30 seconds after the remaining rate reset

    def fetch_content(self, repo, contentName):
        """
        check if a repo has a given content
        """
        url = repo.url + '/' + contentName
        status = repo._requester.requestJson('GET', url)[0]
        if status == 200:
            content = repo.get_readme()
            if "readme_dir" in self.config:
                dest = self.config["readme_dir"]
                isExist = os.path.exists(dest)
                if not isExist:
                    os.makedirs(dest)
                dest = os.path.join(dest, repo.name)
                isExist = os.path.exists(dest)
                if not isExist:
                    os.makedirs(dest)
                dest = os.path.join(dest, "readme.md")
                f = open(dest, "w")
                f.write(content.content)
                f.close()
                return content.url
        else:
            return None

    def query_repo(self, term, timeranges, remaining_rate):
        """
        obtain repos list based on query terms
        """
        # get repositories for each timerange
        repos = []
        iteration = 0
        for timerange in timeranges:
            iteration = iteration + 1
            debug__print("timerange is {}".format(timerange))
            debug__print("Remaining rates are {}".format(remaining_rate))
            search_term = term + " created:"+timerange
            paged_list = self.conn.search_repositories(
                query=search_term)
            if paged_list.totalCount > 1000:
                debug__print(
                    'too many repos in this time range ({})'.format(timerange))
                break
            if paged_list.totalCount == 0:
                debug__print("Skip()")
                sleep_dur = self.sleep_time()
                debug__print("sleep for {}".format(sleep_dur))
                time.sleep(sleep_dur)
                continue
            elif remaining_rate < paged_list.totalCount*2:
                debug__print("no left rates, how to break")
                self.connect()
                sleep_dur = self.sleep_time()
                debug__print("sleep for {}".format(sleep_dur))
                time.sleep(sleep_dur)
                debug__print("Sleep finished()")
                search_term = term + " created:"+timerange
                paged_list = self.conn.search_repositories(
                    query=search_term)
                repos_tmp = [[item._rawData[k] for k in self.config['attrs']] + [self.fetch_content(
                    item, 'readme')] + [item._rawData['owner']['type']] for item in paged_list]
                repos = repos + repos_tmp
                debug__print("remaining_rate < paged_list.totalCount*2")
            else:
                debug__print("process: {}".format(paged_list.totalCount))
                repos_tmp = [[item._rawData[k] for k in self.config['attrs']] + [self.fetch_content(
                    item, 'readme')] + [item._rawData['owner']['type']] for item in paged_list]
                repos = repos + repos_tmp
                debug__print("finished processing batch")
                time.sleep(120)
                self.connect()
                remaining_rate = self.conn.rate_limiting[0]
                debug__print("query::else")
        return repos

    def process(self):
        repos = []
        for term in self.config["terms"]:
            try:
                debug__print("search for: {}".format(term))
                timeranges = self.time_range(term)
                # debugging print
                # for timerange in timeranges:
                #     print(timerange)
                self.connect()
                remaining_rate = self.conn.rate_limiting[0]
                debug__print(
                    "remaining rate after split big query: {}".format(remaining_rate))
                # conduct small queries
                repos = repos + \
                    self.query_repo(term, timeranges, remaining_rate)
                debug__print("found repo {}".format(len(repos)))
            except Exception as e:
                debug__print("Oops! {} occurred.".format(e.__class__))
                debug__print("repos: {}".format(len(repos)))
                debug__print("Next entry.")

        rindex = 0
        for repoList in repos:
            index = 0
            for repo in repoList:
                try:
                    if self.config['attrs'].index("license") == index:
                        if repo != None and "key" in repo:
                            repos[rindex][index] = repo["key"]
                finally:
                    value = "Error"
                index = index + 1
            rindex = 1 + rindex

        df_repos = pd.DataFrame(repos, columns=self.config['attrs'] +
                                ['readme_url', 'owner_type'])
        df = df_repos.drop_duplicates(subset=['id'])
        df_duplicates = df_repos.loc[~df_repos.index.isin(df.index)]
        self.data_output(df, "repos")
        self.data_output(df_duplicates, "repos_duplicates")

    def data_output(self, df, name):
        isExist = os.path.exists(self.output)
        if not isExist:
            os.makedirs(self.output)
        dt = int(time.time())
        if "format" in self.config:
            debug__print("File output: <{}> {}".format(
                self.config["format"], "{}_{}.csv".format(name, dt)))
            if self.config["format"] == "CSV":
                df.to_csv(os.path.join(
                    self.output, "{}_{}.csv".format(name, dt)), index=False)
            elif self.config["format"] == "JSON":
                df.to_json(os.path.join(
                    self.output, "{}_{}.json".format(name, dt)))
            elif self.config["format"] == "MARKDOWN":
                df.to_markdown(os.path.join(
                    self.output, "{}_{}.mk".format(name, dt)))
            elif self.config["format"] == "HTML":
                df.to_html(os.path.join(
                    self.output, "{}_{}.html".format(name, dt)))
            else:
                df.to_csv(os.path.join(
                    self.output, "{}_{}.csv".format(name, dt)), index=False)
        else:
            df.to_csv(os.path.join(
                self.output, "{}_{}.csv".format(name, dt)), index=False)

    def check_remain_rates(self):
        """
        check whether there if any remaining rates
        """

        remaining = self.conn.rate_limiting[0]
        debug__print("left rates: {}".format(remaining))
        if remaining == 0:
            debug__print('No remaining rates left!')
            return False
        else:
            return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Gather information about GitHub Repositories.')
    parser.add_argument('--token', type=str, dest='token',
                        help='Github Token')
    parser.add_argument('config', metavar='config_json', type=str,
                        help='an integer for the accumulator')

    args = parser.parse_args()
    query = GitHubQuery(args.token, args.config)
    query.connect()
    if query.check_remain_rates():
        debug__print('we have rates!')
        query.process()
    else:
        sleep_dur = query.sleep_time()
        debug__print('sleep for {}'.format(sleep_dur))
        time.sleep(sleep_dur)

        # double check if the rate is larger than 0
        try:
            query.connect()
            query.process()
            pass
        except Exception as e:
            raise e
