import pandas as pd
import xml.etree.ElementTree as ET
import os
from tqdm import tqdm
import json
import plotly.express as px
import numpy as np 
import math

## Import the Link parameter file
param_file = "LinkParams.json"
with open(param_file) as f:
    LINK_PARAMS = json.load(f)


def parse_xml(xml_path):
    """
    READ THE XML FILES FOR FCD.
    """
    # Parse the XML data
    print("\n[X] Reading file ...", end=" ")
    root = ET.parse(xml_path)
    # Data extracted from the xml 
    data = []

    # Loop for all timesteps in the xml
    for timestep in root.findall('timestep'):
        time = float(timestep.get('time'))
        vehicles = timestep.findall('vehicle')

        if vehicles:
            for vehicle in vehicles:
                vehicle_data = {
                    'time': time,
                    'id': vehicle.get('id'),
                    'x': float(vehicle.get('x', float('nan'))),
                    'y': float(vehicle.get('y', float('nan'))),
                    'angle': float(vehicle.get('angle', float('nan'))),
                    'type': vehicle.get('type'),
                    'speed': float(vehicle.get('speed', float('nan'))),
                    'pos': float(vehicle.get('pos', float('nan'))),
                    'lane': vehicle.get('lane'),
                    'slope': float(vehicle.get('slope', float('nan')))
                }
                data.append(vehicle_data)
        else:
            data.append({
                'time': time,
                'id': None,
                'x': float('nan'),
                'y': float('nan'),
                'angle': float('nan'),
                'type': None,
                'speed': float('nan'),
                'pos': float('nan'),
                'lane': None,
                'slope': float('nan')
            })

    # Create DataFrame
    df = pd.DataFrame(data)
    print("Done!")

    # Ensure all columns are present, even if no data
    columns = ["time", "id", "x", "y", "angle", "type", "speed", "pos", "lane", "slope"]
    for col in columns:
        if col not in df.columns:
            df[col] = None
    # Reorder columns
    df = df[columns]

    return df


def convert_to_feather(fcd, xml_path):
    """
    CONVERT THE FD DATA TO USEFUL UNITS.
    SAVE THE CONVERTED XML DATA TO DATAFRAME

    Args:
        xml_path (_type_): _description_

    Returns:
        _type_: _description_
    """

    # UNIT CONVERSION FOR LATER USE
    # Convert speed from m/s to km/h
    fcd['speed'] = fcd['speed'] * 3.6
    # Convert position from m to km
    fcd['pos'] = fcd['pos'] / 1000
    # Convert time from seconds to hours
    fcd['time'] = fcd['time'] / 3600

    # LINKS in the FCD
    print("\n", "-"*50)
    print("LANE ID:")
    print(fcd.lane.unique())
    print("-"*50)

    # SAVE TO FEATHER
    print("[X] Saving as feather ...", end=" ")
    parent_dir = os.path.abspath(os.path.join(xml_path, os.pardir))
    output_path = os.path.join(parent_dir, "fcd.feather")
    fcd.to_feather(output_path)
    print("Done!")

    return fcd



def average_vehicle_length(fcd):
    """
    ANALYSIS FOR AVERAGE LENGTH OF DIFFERENT TYPE OF VEHICLE ON THE LINK
    """
    ## EDIT the type of vehicles in the dataset
    fcd["type_editied"] = fcd.type.apply(lambda x: "_".join(x.split("_")[:-1]) if x is not None else None)

    ## RESULT table
    # Length of each different vehicle
    result = pd.DataFrame()
    result["count"] = fcd.groupby("type_editied")["type_editied"].count()
    ## Add the length information for each type of vehicle
    result["length"] = [5] # Only opti-driver

    # Mean length of vehicles on the link
    mean_length_of_vehicles = (result["count"] * result.length).sum() / ((result["count"]).sum())

    print("\n NUMBER OF VEHICLE OF EACH TYPE")
    print(result)
    print("\n MEAN LENGTH OF VEHICLES: ", mean_length_of_vehicles)




def get_detectData(fcd, detectlinks):
    ### DETECTED VEHICLES
    links = detectlinks.copy()
    # Filter the data that only for the link
    mask = (fcd["lane"] == links.pop())
    for link in links:
        mask |= (fcd["lane"] == link)
    carVeh = fcd[mask]
    carVeh = carVeh[carVeh["pos"].notnull()]
    carVeh.reset_index(inplace=True, drop=True)
    return carVeh


def get_probeData(fcd, probelinks):
    ### PROBE VEHICLES
    links = probelinks.copy()
    # Filter the data that only for the link
    mask = (fcd["lane"] == links.pop())
    for link in links:
        mask |= (fcd["lane"] == link)
    probeVeh = fcd[mask]
    probeVeh = probeVeh[probeVeh["pos"].notnull()]
    # To make the probe vehicle trajectory start in opposite direction
    probeVeh["pos"] = fcd['pos'].max() - probeVeh["pos"]
    probeVeh.reset_index(inplace=True, drop=True)
    return probeVeh


def generate_expData(ids, probeData, carData):
    ### Loop over all the different IDS to create a sperate folder for each run
    print("\n")
    for idx in (pbar := tqdm(ids)):
        pbar.set_description("Generating data for Probe ID: ")

        ### First check if the probe_id alread exits
        # EXP Directory
        exp_folder = os.path.join(os.getcwd(), "exp/")
        if not os.path.exists(exp_folder):
            os.mkdir(exp_folder)


        # If the probe_id does not exits, then generate data
        output_folder = os.path.join(exp_folder, f"{idx}")
        if not os.path.exists(output_folder):

            # Probe data
            probe = probeData[probeData["id"] == idx]
            # print("Length of Probe: ", len(probe))
            # Detected veh data
            min_time = probe.time.min()
            max_time = probe.time.max()
            detect = carData[(carData["time"] >= min_time) & (carData["time"] <= max_time)]
            # print("Length of Detect:", len(detect))

            # If the length of detection is greater than 1, meaning there are detected vehicles.
            if len(detect) > 1:
                os.mkdir(output_folder)

                ########### SAVING DATA ###########
                # Save the probe data
                path = os.path.join(output_folder, "ProbeTraj.csv")
                probe.to_csv(path, sep=";", decimal=",")
                # Save the detect data
                path = os.path.join(output_folder, "DetectTraj.csv")
                detect.to_csv(path, sep=";", decimal=",")

                ##### Inflow and Outflow data for each FD-timestep
                # Inflow and outflow data
                timesteps = [2, 3, 4, 5, 6, 7, 8]
                for ts in timesteps:
                    fd_data_path = os.path.join("sumo_ingolstadt/simulation/output/ABESEC/", f"fd-{ts}sec.feather")
                    fd = pd.read_feather(fd_data_path)
                    mask = ((fd['begin-hr'] >= probe.time.min()) & (fd['begin-hr'] <= probe.time.max()) | (fd['end-hr'] >= probe.time.min()) & (fd['end-hr'] <= probe.time.max()))
                    df = fd[mask]
                    inflow  = df[['begin-hr', 'end-hr','inflow']]
                    outflow = df[['begin-hr', 'end-hr','outflow']]

                    ## Save the files
                    path = os.path.join(output_folder, f"inflow-{ts}sec.csv")
                    inflow.to_csv(path, sep=";", decimal=",")
                    # Save the outflow data
                    path = os.path.join(output_folder, f"outflow-{ts}sec.csv")
                    outflow.to_csv(path, sep=";", decimal=",")

            else:
                print(f"\nERROR!!! Not detection done on link on {idx}")
                print("Length of Probe : ", len(probe))
                print("Length of Detect: ", len(detect))
        else:
            print(f"\nProbeID {idx} data already exits")




def extract_space_time_diagrams(fcd):
    """
    EXTRACTING SEVERAL SPACE_TIME DIAGRAM FOR EACH PROBE RUN
    """
    ##################### Extracting PROBE and CAR Trajectories #####################
    # Amount of vehicles that I assume contains the camera (in ratio %)
    peneration_rate = LINK_PARAMS["PENERATION_RATE"]  # between (0, 1)

    # LINKS in the FCD
    print("\n", "-"*50)
    print("LANE ID in the FCD data:")
    print(fcd.lane.unique())
    print("-"*50)

    # Links that are part of detection lane
    detectLink = LINK_PARAMS["DETECTION_LANE"]
    # Links that are part of probe lane
    probeLink  = LINK_PARAMS["PROBE_LANE"]


    # DETECTED VEHICLES
    carData = get_detectData(fcd, detectlinks=detectLink)
    # PROBE VEHICLES
    probeData = get_probeData(fcd, probelinks=probeLink)
    print("\nNUMBER OF VEHICELS IN EACH LANE")
    print("Detect Link :", detectLink)
    print(len(carData.id.unique()))
    print("Probe  Link :", probeLink)
    print(len(probeData.id.unique()))

    # Sample random IDs that are marked as probe
    total_cars = probeData["id"].nunique()
    n_samples = int(total_cars * peneration_rate)
    ids = probeData["id"].sample(n=n_samples, replace=False, random_state=100).to_list()
    print("\nPENERATION RATE: ", peneration_rate)
    print("NUMBER OF PROBE IDS SAMPLES: ", len(ids))

    # GENERATE THE PROBE AND DETECT TRAJECTORY DATA FOR EACH PROBE-ID
    generate_expData(ids, probeData, carData)


def unique_interval_values(intervals)->list:
    """
    Function to return unique values from the interval
    """
    lst = intervals.to_list()
    temp = [k.left for k in lst]
    temp.append(lst[-1].right)
    return temp


def convert_hours_to_hms(decimal_hours):
    # Calculate total seconds from decimal hours
    total_seconds = decimal_hours * 3600
    # Extract hours
    hours = int(total_seconds // 3600)
    # Extract minutes
    minutes = int((total_seconds % 3600) // 60)
    # Extract seconds
    seconds = round(total_seconds % 60, 2)
    # Format that to string
    string = f"{hours}:{minutes}:{seconds}"
    return string


def create_space_time_grid(deltaX, deltaT, road_space: list, time_space: list):
    """
    Create space time grid from the road length and time-stamps.
    Returns deltaT, deltaX and space-time cells as a dict. 
    """

    # # Creating Round number cells - Adjusting the deltaX to match integer number cells.
    # num_cells = math.ceil((road_space[0]  - road_space[1])/deltaX)
    # deltaX = (road_space[0]  - road_space[1]) / num_cells

    # Discrete Cells
    t1 = np.arange(road_space[0], road_space[1], deltaX)
    t2 = np.arange(road_space[0]+deltaX, road_space[1]+deltaX, deltaX)
    if len(t1) != len(t2):
        t1 = np.arange(road_space[0], road_space[1]+deltaX, deltaX)
    cellSpace = pd.IntervalIndex.from_arrays(t1, t2)

    t1 = np.arange(time_space[0], time_space[1], deltaT)
    t2 = np.arange(time_space[0]+deltaT, time_space[1]+deltaT, deltaT)
    cellTime = pd.IntervalIndex.from_arrays(t1, t2)
    cellTime = cellTime[:-1]

    return dict(deltaT= deltaT,
                deltaX= deltaX,
                road_length = road_space,
                total_time  = time_space,
                cell_time= cellTime,
                cell_space= cellSpace,
                num_time=len(cellTime),
                num_space=len(cellSpace))



def plot_contineous_traj(probe, traj, grid=None, camView=False, probeViewDistance=None, title=None):
    # Plot for the detected trajectories
    fig = px.line(traj, x="time", y="pos", color='id', markers=True)
    fig.update_traces(line=dict(width=2), marker=dict(size=2))

    # Plot for probe vehicle
    fg  = px.line(probe, x="time", y="pos", color="id", markers=True,
                    line_dash_sequence=['longdashdot' for _ in range(len(probe))])
    fg.update_traces(line=dict(width=2), marker=dict(size=5))

    # Add the probe plot to detected trajectory plot
    for trace in fg.data:
        trace['line']['color']="#ff0000"
        trace['name'] ='Probe'
        fig.add_trace(trace)

    if camView:
        ## Camera View Area (CameraBand)
        for idx in probe.index:
            fig.add_shape(type="rect",
                x0=probe.loc[idx]["time"]-(0.125/3600),
                y0=probe.loc[idx]["pos"]-probeViewDistance[1],
                x1=probe.loc[idx]["time"]+(0.125/3600),
                y1=probe.loc[idx]["pos"]-probeViewDistance[0],
                line=dict(
                color="Red",
                    width=.1,
                ),
                fillcolor="Red",
                opacity=0.1,
            )
    for ts in unique_interval_values(grid["cell_time"]):
        fig.add_vline(x=ts, line_width=0.8, line_color="black", line_dash="dash")
    for sp in unique_interval_values(grid["cell_space"]):
            fig.add_hline(y=sp, line_width=0.8, line_color="black", line_dash="dash")


    fig.update_layout(legend_title_text='VehicleID', 
                      legend = dict(font = dict(size = 8)),
                      legend_title = dict(font = dict(size=15)),
                      font_size=20, 
                      font_color="black")
    
    # Update tick values
    ticks = []
    for intvl in grid["cell_time"]:
        ticks.append(intvl.right)
        ticks.append(intvl.left)
    fig.update_xaxes(title_text='Time [hr]',
                     range=grid['total_time'],
                     tickmode = 'array',
                     tickvals = list(set(ticks)),
                     ticktext = [convert_hours_to_hms(t) for t in set(ticks)],
                     # showgrid=True, griddash='dash', gridcolor='black', gridwidth=1, 
                     showline=True, linewidth=1, linecolor='black', mirror=True,
                     zeroline=True, zerolinecolor="black")

    # Update tick values
    ticks = []
    for intvl in grid["cell_space"]:
        ticks.append(intvl.right)
        ticks.append(intvl.left)
    fig.update_yaxes(title_text='Space [km]',
                     range=grid['road_length'],
                     tickmode = 'array',
                     tickvals = list(set(ticks)),
                     ticktext = list(set(ticks)),
                     # showgrid=True, griddash='dash', gridcolor='black', gridwidth=1, 
                     showline=True, linewidth=1, linecolor='black', mirror=True, 
                     zeroline=True, zerolinecolor="black")
    fig.update_layout(title_x=0.5, margin={"r":10,"t":40,"l":10,"b":0}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
    return fig





if __name__ == "__main__":
    ## Create XML to Feather
    xml_path="sumo_ingolstadt/simulation/output/fcd.xml"
    fcd = parse_xml(xml_path)

    ## Convert to feather
    fcd = convert_to_feather(fcd)

    ## Average length of vehicles
    average_vehicle_length(fcd)

    ## Extract space-time diagrams for all fcd in the simulation
    extract_space_time_diagrams(fcd)
