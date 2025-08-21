import pandas as pd
import xml.etree.ElementTree as ET
import os
import json 
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.utils import PlotlyJSONEncoder

## Import the Link parameter file
param_file = "LinkParams.json"
with open(param_file) as f:
    LINK_PARAMS = json.load(f)


def parse_xml(xml_path, ts):
    # Parse the XML data
    print(f"\n[X] Reading file {ts}sec...", end=" ")
    root = ET.parse(xml_path)

    # Prepare data list
    data = []

    # Iterate through intervals
    for interval in root.findall('interval'):
        interval_data = {
            'begin': float(interval.get('begin')),
            'end': float(interval.get('end')),
            'id': interval.get('id')
        }

        # Check if there's an edge element
        edge = interval.find('edge')
        if edge is not None:
            interval_data.update({
                'laneid': edge.get('id'),
                'sampledSeconds': float(edge.get('sampledSeconds', 'nan')),
                'overlapTraveltime': float(edge.get('overlapTraveltime', 'nan')),
                'density': float(edge.get('density', 'nan')),
                'laneDensity': float(edge.get('laneDensity', 'nan')),
                'occupancy': float(edge.get('occupancy', 'nan')),
                'waitingTime': float(edge.get('waitingTime', 'nan')),
                'timeLoss': float(edge.get('timeLoss', 'nan')),
                'speed': float(edge.get('speed', 'nan')),
                'speedRelative': float(edge.get('speedRelative', 'nan')),
                'departed': int(edge.get('departed', '0')),
                'arrived': int(edge.get('arrived', '0')),
                'entered': int(edge.get('entered', '0')),
                'left': int(edge.get('left', '0')),
                'laneChangedFrom': int(edge.get('laneChangedFrom', '0')),
                'laneChangedTo': int(edge.get('laneChangedTo', '0'))
            })
        else:
            # If no edge element, fill with NaN or appropriate default values
            interval_data.update({
                'laneid': None,
                'sampledSeconds': float('nan'),
                'overlapTraveltime': float('nan'),
                'density': float('nan'),
                'laneDensity': float('nan'),
                'occupancy': float('nan'),
                'waitingTime': float('nan'),
                'timeLoss': float('nan'),
                'speed': float('nan'),
                'speedRelative': float('nan'),
                'departed': 0,
                'arrived': 0,
                'entered': 0,
                'left': 0,
                'laneChangedFrom': 0,
                'laneChangedTo': 0
            })

        data.append(interval_data)

    # Create DataFrame
    df = pd.DataFrame(data)

    # Reorder columns as specified
    columns = ['begin', 'end', 'id', 'laneid', 'sampledSeconds', 'overlapTraveltime', 'density', 
               'laneDensity', 'occupancy', 'waitingTime', 'timeLoss', 'speed', 'speedRelative', 
               'departed', 'arrived', 'entered', 'left', 'laneChangedFrom', 'laneChangedTo']
    df = df[columns]
    df = df[df['laneid'].notna()]

    ## Add flow and density info 
    df.reset_index(inplace=True, drop=True)
    print("Done!")

    return df


def get_fd_plot(df, title=None):
    fig = make_subplots(rows=1, cols=3)
    ## Speed/Density plot
    fig.add_trace(go.Scatter(x=df['laneDensity'],
                             y=df["speed"],
                             mode="markers",
                             name="Speed vs Density",
                             hovertemplate='Density: %{x}<br>Speed: %{y}'),
                             row=1, col=1)

    ## Flow/Density plot
    fig.add_trace(go.Scatter(x=df['laneDensity'],
                             y=df["flow"],
                             mode="markers",
                             name="Flow vs Density",
                             hovertemplate='Density: %{x}<br>Flow: %{y}'),
                             row=1, col=2)

    ## Speed/Flow
    fig.add_trace(go.Scatter(x=df["flow"],
                             y=df["speed"],
                             mode="markers",
                             name="Speed vs Flow",
                             hovertemplate='Flow: %{x}<br>Speed: %{y}'),
                             row=1, col=3)

    # Update axis information
    fig.update_xaxes(title_text='Density [veh/km]',
                     # range=[0, 266.66],
                     showgrid=True, griddash='dash', gridcolor='black', gridwidth=0.5, 
                     showline=True, linewidth=1, linecolor='black', mirror=True,
                     zeroline=True, zerolinecolor="black",
                     row=1, col=1)
    fig.update_xaxes(title_text='Density [veh/km]',
                     # range=[0, 266.66],
                     showgrid=True, griddash='dash', gridcolor='black', gridwidth=0.5, 
                     showline=True, linewidth=1, linecolor='black', mirror=True,
                     zeroline=True, zerolinecolor="black",
                     row=1, col=2)
    fig.update_xaxes(title_text='Flow [veh/hr]',
                     # range=[0, Qmax],
                     showgrid=True, griddash='dash', gridcolor='black', gridwidth=0.5, 
                     showline=True, linewidth=1, linecolor='black', mirror=True,
                     zeroline=True, zerolinecolor="black",
                     row=1, col=3)
    fig.update_yaxes(title_text='Speed [km/hr]', 
                     showgrid=True, griddash='dash', gridcolor='black', gridwidth=0.5, 
                     showline=True, linewidth=1, linecolor='black', mirror=True,
                     zeroline=True, zerolinecolor="black",
                     row=1, col=1)
    fig.update_yaxes(title_text='Flow [veh/hr]',
                     showgrid=True, griddash='dash', gridcolor='black', gridwidth=0.5, 
                     showline=True, linewidth=1, linecolor='black', mirror=True,
                     zeroline=True, zerolinecolor="black",
                     row=1, col=2)
    fig.update_yaxes(title_text='Speed [km/hr]', 
                     showgrid=True, griddash='dash', gridcolor='black', gridwidth=0.5, 
                     showline=True, linewidth=1, linecolor='black', mirror=True,
                     zeroline=True, zerolinecolor="black",
                     row=1, col=3)

    fig.update_layout(title=title,
                    font_size=20,  font_color="black",
                    title_x=0.5, margin={"r":10,"t":40,"l":10,"b":0},
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False)
    return fig

def plotlyfig2json(fig, fpath=None):
    """
    Modified from https://github.com/nteract/nteract/issues/1229
    """

    redata = json.loads(json.dumps(fig.data, cls=PlotlyJSONEncoder))
    relayout = json.loads(json.dumps(fig.layout, cls=PlotlyJSONEncoder))

    fig_json=json.dumps({'data': redata,'layout': relayout})

    if fpath:
        with open(fpath, 'w') as f:
            f.write(fig_json)
    else:
        return fig_json

def plotlyfromjson(fpath):
    """Render a plotly figure from a json file"""
    with open(fpath, 'r') as f:
        v = json.loads(f.read())

    fig = go.Figure(data=v['data'], layout=v['layout'])
    return fig



if __name__ == "__main__":

    """
    # READ THE XML FILES FOR EACH FD-SAMPLING TIMESTEP.
    # CONVERT THE FD DATA TO USEFUL UNITS.
    # SAVE THE CONVERTED XML DATA TO DATAFRAME
    # """
    ###################### IMPORTANT VARIABLS ######################
    # Sampling times
    timesteps = [2, 3, 4, 5, 6, 7, 8]

    # Number of Lanes on the detecion lane
    n_lanes = 2

    ###################### LOOP ACROSS TIMESTEPS ######################
    ## Loop across each different file and create a corresponding dataframe
    for ts in timesteps:
        # CONVERT XML TO FEATHER
        cwd = os.getcwd()
        xml_path = os.path.join(cwd, f"sumo_ingolstadt/simulation/output/fd-¨{ts}sec.xml")
        edge = parse_xml(xml_path, ts)

        # UNIT CONVERSION FOR LATER USE
        # Convert speed from m/s to km/h
        edge['speed'] = edge['speed'] * 3.6
        # Convert the density from veh/km/lane to veh/km
        edge['laneDensity'] = edge['laneDensity']*n_lanes
        # Calculate flow (veh/h)
        edge['flow'] = edge['laneDensity']*edge['speed']
        # Convert timestamps to hours
        edge['begin-hr'] = edge['begin']/3600
        edge['end-hr']   = edge['end']/3600
        # Traffic flow into the lane
        edge['inflow']  = 3600 * (edge['entered'] / ts)
        edge['outflow'] = 3600 * (edge['left'] / ts)

        # EDGE SUMMARY
        print("\n", "-"*50)
        print("LANE ID:")
        print(edge.laneid.unique())
        print(edge[['density', 'laneDensity', 'occupancy', 'entered', 'left']].describe())
        print("-"*50)

        # SAVE TO FEATHER
        print("[X] Saving as feather ...", end=" ")
        parent_dir = os.path.abspath(os.path.join(xml_path, os.pardir))
        output_path = os.path.join(parent_dir, f"fd-{ts}sec.feather")
        edge.to_feather(output_path)
        print("Done!")
    ###################################################################################


