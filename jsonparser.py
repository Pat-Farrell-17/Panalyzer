import pickle
import os
import matplotlib.pyplot as plt

# TODO: remove global...
CM_TO_KM = 100000           # CM in a KM
MAX_MAP_SIZE = 8            # In KM

def search(json_object, player_id, start_range, end_range, event_type):
    # TODO
    return


# Return the dict from the pickle file name
def load_pickle(pickle_file):
    with open(pickle_file, 'rb') as f:
        telemetry_data = pickle.load(f)
    f.close()
    return telemetry_data


# Get the location the plane starts in (not quite sure it's useful yet...)
def get_plane_start(telemetry):
    start_loc = None
    for log_entry in telemetry:
        if log_entry["_T"] == "LogMatchStart":
            start_loc = log_entry["characters"][0]['location']      # All players start at the exact same location, so we only need first
    return start_loc


# Get the map name from telemetry
def get_map(telemetry):
    for log_entry in telemetry:
        if log_entry["_T"] == "LogMatchStart":
            return log_entry["mapName"]
    return None


# Get the result for each player in the match from the telemetry data
# Return the results as a list of dicts:
#       [{'name' : playerName, 'ranking': ranking},
#        ...]
def get_rankings(telemetry):
    results = []
    for log_entry in telemetry:
        if log_entry["_T"] == "LogMatchEnd":
            for character in log_entry['characters']:
                results.append({'name': character['name'],
                                'ranking': character['ranking']})
    return results


# Get the location of each player's landing from the telemetry data
# Return as a dict:
#           {playerName: [x, y],
#            ...}
def get_all_landings(telemetry):
    landings = {}
    for log_entry in telemetry:
        if log_entry["_T"] == "LogParachuteLanding":
            landing_loc = log_entry['character']['location']
            x = landing_loc['x']
            y = landing_loc['y']
            landings[log_entry['character']['name']] = [x, y]
    return landings


def get_flight_data(telemetry):
    first_coordinate = None # First player exit event from plane
    current_coordinate = None # Last player exist even from plane
    for log_entry in telemetry:
        if log_entry.get("_T") == "LogVehicleLeave" and log_entry.get("vehicle").get("vehicleId") == "DummyTransportAircraft_C":
            current_coordinate = log_entry.get("character").get("location")
            if first_coordinate == None:
                first_coordinate = current_coordinate
    return first_coordinate, current_coordinate


# Plot the drop locations of each player (in blue), with opacity in relation to their rank in that match
# (more opaque = lower rank), along with the location the first person left the plane (in green)
# and the last person to leave the plane (in red)
def display_drop_locations(telemetry, fig, fig_x, fig_y, fig_num, match_num):
    landings = get_all_landings(telemetry)
    rankings = get_rankings(telemetry)
    mapName = get_map(telemetry)

    # Set up plot scale
    if mapName == "Savage_Main":                        # 4km map
        x_max = MAX_MAP_SIZE * (1/2)
        y_max = x_max
    elif mapName in ["Erangel_Main", "Desert_Main"]:    # 8km maps
        x_max = MAX_MAP_SIZE
        y_max = MAX_MAP_SIZE
    elif mapName == "DihorOtok_Main":                   # 6km map
        x_max = MAX_MAP_SIZE * (3/4)
        y_max = x_max

    first_launch, last_launch = get_flight_data(telemetry)

    if first_launch is not None:
        launch_x = [first_launch['x'], last_launch['x']]
        launch_y = [first_launch['y'], last_launch['y']]

        ax = fig.add_subplot(fig_x, fig_y, fig_num)

        # plot first and last jump locations
        ax.scatter(launch_x[0] / CM_TO_KM, launch_y[0] / CM_TO_KM, s=100,  color='green', edgecolors='black')
        ax.scatter(launch_x[1] / CM_TO_KM, launch_y[1] / CM_TO_KM, s=100, color='red', edgecolors='black')

        # plot line between them
        ax.plot([x_ / CM_TO_KM for x_ in launch_x],
                [y_ / CM_TO_KM for y_ in launch_y], 'grey', linestyle='--', marker='')

        # plot each player according to their ranking
        for ranking in rankings:
            landing_loc = landings[ranking['name']]
            print("Player {} landing at position\t ({}, {}) and ended up rank : {}".format(ranking['name'],
                                                                                       landing_loc[0],
                                                                                       landing_loc[1],
                                                                                       ranking['ranking']))
            if ranking['ranking'] == 1:
                ax.scatter(landing_loc[0] / CM_TO_KM, landing_loc[1] / CM_TO_KM, color='yellow', edgecolors='black')
            else:
                ax.scatter(landing_loc[0] / CM_TO_KM, landing_loc[1] / CM_TO_KM, color='blue', alpha=1/ranking['ranking'])
        plt.ylim(0, y_max)
        plt.xlim(0, x_max)
        plt.xlabel('km')
        plt.ylabel('km')
        plt.title(mapName)
        plt.savefig('.\\match_landings\\match_{}.png'.format(match_num))
        plt.show()
    else:
        print("Could not get launch data")

def main():
    data_dir = ".\\data\\"
    matche_files = []
    telemetry_files = []

    for file in os.listdir(data_dir):
        if "_match" in file:
            matche_files.append(file)
        elif "_telemetry" in file:
            telemetry_files.append(file)

    # Plots each match landing locations on a new plot
    for match_num in range(0, 20):
        telemetry = load_pickle(data_dir + telemetry_files[match_num])
        display_drop_locations(telemetry, plt.figure(), 1, 1, 1, match_num)

if __name__ == "__main__":
    main()


