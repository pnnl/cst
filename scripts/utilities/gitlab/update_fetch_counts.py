"""
Created on 01/15/2023

Simple query to pull in the fetch count for each of the past 16 days.

This stores the data in a 

@author: Trevor Hardy
trevor.hardy@pnnl.gov
"""

# Install gitlab: pip install --upgrade python-gitlab
import gitlab
import json
import logging
import datetime as dt
import argparse
import sys
import os
import pathlib


logger = logging.getLogger(__name__)


def _open_file(file_path: str, type='r'):
    """Utilty function to open file with reasonable error handling.


    Args:
        file_path (str) - Path to the file to be opened

        type (str) - Type of the open method. Default is read ('r')


    Returns:
        fh (file object) - File handle for the open file
    """
    try:
        fh = open(file_path, type)
    except IOError:
        logger.error('Unable to open {}'.format(file_path))
    else:
        return fh

def _auto_run(args):
    # Set current working directory to where this script is
    # Assumes the fetches_data.json file is in the same folder
    os.chdir(pathlib.Path(__file__).parent.resolve())


    # Open up previous results file
    fetches_fh = _open_file(args.data_file)
    fetches_data = json.load(fetches_fh)
    fetches_fh.close()

    # Get todays date
    today_date = dt.date.today().strftime('%Y-%m-%d')

    # Define your GitLab private token and instance URL
    TOKEN = '-z5zHpbWBQcN_pU5xsWf'
    GITLAB_URL = 'https://devops.pnnl.gov'
    PROJECT_ID = 2066 # This can be a numeric ID or a project path

    # Initialize a connection to the GitLab server
    gl = gitlab.Gitlab(GITLAB_URL, private_token=TOKEN)

    # Get the project
    #project = gl.projects.get(PROJECT_ID)

    # Get project statistics
    # 2025-01-15: This was not working for Trevor. The `project`
    # object did not have a `statistics` method or attribute
    #statistics = project.statistics()

    # Collects fetch count for each day over the past 16 days
    statistics = gl.http_get(f'/projects/{PROJECT_ID}/statistics')
    for day in statistics["fetches"]["days"]:
        if day["date"] not in fetches_data.keys():
            if day["date"] != today_date:
                fetches_data[day["date"]] = {"count": day["count"]}
    
    if args.add_zeros:
        # Convert date strings to datetime objects and sort them
        dates = [dt.datetime.strptime(date_str, "%Y-%m-%d") for date_str in fetches_data]
        dates.sort()

        # Determine the date range
        start_date = dates[0]
        end_date = dates[-1]

        # Construct a new dictionary with all dates in the range
        filled_data = {}
        current_date = start_date

        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str in fetches_data:
                filled_data[date_str] = fetches_data[date_str]
            else:
                filled_data[date_str] = {"count": 0}
            current_date += dt.timedelta(days=1)

        # Display the filled dictionary
        # for date, data in filled_data.items():
        #     print(f"{date}: {data}")

        fetches_data = filled_data


    # Write out updated JSON
    fetches_fh = _open_file(args.data_file, 'w')
    json.dump(fetches_data, fetches_fh)
    fetches_fh.close()


if __name__ == '__main__':
    # This slightly complex mess allows lower importance messages
    # to be sent to the log file and ERROR messages to additionally
    # be sent to the console as well. Thus, when bad things happen
    # the user will get an error message in both places which,
    # hopefully, will aid in trouble-shooting.
    fileHandle = logging.FileHandler("update_fetch_counts.log",'w')
    fileHandle.setLevel(logging.DEBUG)
    streamHandle = logging.StreamHandler(sys.stdout)
    streamHandle.setLevel(logging.ERROR)
    logging.basicConfig(level=logging.DEBUG,
                        handlers=[fileHandle, streamHandle])
    parser = argparse.ArgumentParser(description="Evaluates disk space used,"
                                     "writes results to disk, and makes a graph.")
    parser.add_argument('-d', '--data_file',
                        help="number of fetches per day stored in ",
                        nargs='?',
                        default="fetch_counts.json")
    parser.add_argument('-z', '--add_zeros',
                        help="flag to add dates where there were zero fetches)",
                        action=argparse.BooleanOptionalAction)
    args = parser.parse_args()
    _auto_run(args)
