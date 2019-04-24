import pandas as pd
from pandas.io.json import json_normalize
import requests
import gzip 
import shutil
import os
import time
import logging
import match

class API_Key:
    def __init__(self, key_string):
        self.key_string = key_string
        self.limit_max = -1
        self.limit_remaining = -1
        self.limit_reset = -1

class Match_Samples_Response:
    def __init__(self, response_code):
        self.response_code = response_code
        self.match_ids = []

def main():
    # Check API key
    api_keys = []
    with open('api_keys.txt') as api_keys_file:
        for key in api_keys_file:
            api_keys.append(API_Key(key.rstrip()))

    # Get matches and test keys
    sample_matches = None
    match_id_queue = []
    for key in api_keys:
        if key.limit_reset < time.time():
            key.limit_remaining = key.limit_max
        if key.limit_remaining == 0:
            continue
        sample_matches = get_sample_matches(key)
        if sample_matches.response_code == 200:
            match_id_queue.extend(sample_matches.match_ids)
            break

    if len(match_id_queue) < 1:
        logging.error("Could not get any match ids")

    # Survey all downloaded files to make list of all downloaded matches
    # TODO

    # For all matches not yet downloaded, put them in an array
    # TODO

    # Query each match on the API and dump its info, logging telemetry URL in an array
    if sample_matches is None:
        logging.exception("No match ids found to download, quitting")
        exit()
    for match in sample_matches.match_ids:
        get_match_stats(match)

    # Download matches from the array
    # TODO

    # Decompress matches
    # TODO


# Get a list of random match IDs from the PUBG API
def get_sample_matches(api_key):
    logging.info("Getting sample matches")
    logging.debug("Using API key %s to get sample matches", api_key.key_string)
    # Header for auth
    header = {"Authorization": "Bearer %s" % api_key.key_string,
              "Accept": "application/vnd.api+json"}

    # Get the API call data
    api_result = requests.get("https://api.pubg.com/shards/steam/samples", headers=header)
    api_key.limit_remaining = api_result.headers.get("X-Ratelimit-Remaining")
    api_key.limit_qty = api_result.headers.get("X-Ratelimit-Limit")
    api_key.limit_reset = api_result.headers.get("X-Ratelimit-Reset")
    sample_matches = Match_Samples_Response(api_result.status_code)

    if api_result.status_code == 200:
        logging.info("Received sample matches (HTTP status code 200), extracting match ids")
        # Dump json data into pandas for better formatting
        samples_df = pd.DataFrame(api_result.json())

        # Extract just the match data
        samples_norm = json_normalize(samples_df.loc['relationships'])
        match_ids_dataframe = samples_norm['matches.data'].apply(pd.Series).T[0].apply(pd.Series)
        sample_matches.match_ids = match_ids_dataframe['id'].values
    else:
        logging.info("HTTP status code %s encountered while retrieving matches", api_result.status_code)

    return sample_matches


# Given a match ID, pull the data for that match and return it as a pandas DataFrame
def get_match_stats(match_id):
    header = {"accept": "application/vnd.api+json"}
    apireq = requests.get("https://api.pubg.com/shards/steam/matches/%s" % match_id, headers=header)

    # API response is structured: { data : {...}
    #                               included: [...] }
    # where data has information about the IDs of the match objects (players, rosters, etc) and
    # included contains links to the actual objects about the match (look up by ID from data)

    # Import the "data" portion of the API response into Pandas
    api_response_data_dataframe = pd.DataFrame(apireq.json()['data'])
    # Import the "included" portion of the API response into Pandas
    api_response_included_dataframe = pd.DataFrame(apireq.json()['included'])

    # Get the telemetry URL from its asset UID.
    # The telemetry UID is different from the match UID so we must retrieve the telemetry UID.
    # The telemetry UID the only "id" field in the only "data" entry of "type": "asset" ...
    # ... under "data" -> "relationships" -> "assets"

    # Get the assets portion of the data
    assets = pd.DataFrame(api_response_data_dataframe.loc['assets', 'relationships'])['data'].apply(pd.Series)
    # The telemetry id is the only entry of type "data" under section "assets", so grab it
    telemetry_id = assets[assets.type == "asset"]['id'].values[0]
    # Get the telemetry object from the "included" dataframe
    telemetry_object = api_response_included_dataframe[api_response_included_dataframe.id == telemetry_id]
    # Get the url from the telemetry object
    telemetry_url = telemetry_object['attributes'].apply(pd.Series)['URL']

    # Extract match statistics and create a match object
    game_mode = api_response_data_dataframe.loc['gameMode', 'attributes']
    map = api_response_data_dataframe.loc['mapName', 'attributes']
    start_time = api_response_data_dataframe.loc['createdAt', 'attributes']
    duration = api_response_data_dataframe.loc['duration', 'attributes']
    match_data_object = match.match(match_id, game_mode, map, start_time, duration, telemetry_url)
    return match_data_object

# Given location of gzips and location of where to extract to -> unzips gzip files
def extract_gzip(gzip_indir, gzip_outdir): 
    
    # Check if directories exist
    if not os.path.isdir(gzip_indir): 
        print("Cannot find directory '" + gzip_indir + "'")
        exit()
    elif not os.path.isdir(gzip_outdir):
        print("Cannot find directory '" + gzip_outdir + "'")
        exit()

    # Get name of all files to unzip
    files = os.listdir(gzip_indir)
    for f in files: 
        outfile  = f.replace(".gz", "")
        try: 
            with gzip.open(gzip_indir + f, 'rb') as g:
                print("Copying '" + f + "'")

                # Copy files to output directory
                with open(gzip_outdir + outfile, 'wb') as g_copy: 
                    shutil.copyfileobj(g, g_copy)

        except: 
            print("Unable to copy file '" + gzip_indir + f + "'\n")

    print("Copying data - done")

if __name__== "__main__":
    main()
