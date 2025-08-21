import streamlit as st 
import json
import os
import pandas as pd 

from fd_data import plotlyfromjson
from fcd_data import plot_contineous_traj, create_space_time_grid

def page_configuration() -> None:
    # Configure the page
    st.set_page_config(
        page_title="SUMO Simulation Dashboard",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded"
    )





def fd_analysis(link) -> None:

    # Show FD plot
    fd_plot_path = f"data/{link}/fd_plot-{link}.json"
    st.plotly_chart(plotlyfromjson(fd_plot_path))


def fcd_trajectories(link):

    main_folder = f"data/{link}/exp/"

    ## List out the exp
    exp_list = [exp for exp in os.listdir(main_folder)]
    exp_name = st.selectbox("Select Experiment: ",
                    exp_list,
                    accept_new_options=False)

    ## Probe and FCD
    exp_folder = os.path.join(main_folder, exp_name)
    probe = pd.read_csv(os.path.join(exp_folder, "ProbeTraj.csv"), sep=";", decimal=",", index_col=0)
    traj = pd.read_csv(os.path.join(exp_folder,  "DetectTraj.csv"), sep=";", decimal=",", index_col=0)


    # Discritization
    delta_params = {"Link-1": {"DELTAX": 0.086, "DELTAT": 3/3600}, 
                    "Link-2": {"DELTAX": 0.052, "DELTAT": 3/3600}, 
                    "Link-3": {"DELTAX": 0.043, "DELTAT": 2/3600}, 
    }
    grid = create_space_time_grid(delta_params[link]["DELTAX"], delta_params[link]["DELTAT"], 
                                 road_space=[0, 0.4],
                                 time_space=[probe["time"].min(), probe["time"].max()])
    actual_traj = plot_contineous_traj(probe, traj, grid, camView=True, probeViewDistance=[0, 0.140])
    st.plotly_chart(actual_traj, use_container_width=True)



def main() -> None:
    ## Page config
    page_configuration()

    ## Main Page View
    st.title("SUMO Simulated Data Dashboard")
    st.markdown("""
    Dashboard to visualize FCD and FD data extracted from Ingolstadt model.
    The FCD data is collected for three links from the simulation. Link details are in table below:

        |       **Attribute**       	|      **Link 1**      	|     **Link 2**     	|  **Link 3** 	|
        |:-------------------------:	|:--------------------:	|:------------------:	|:-----------:	|
        | Street Name               	| Westliche Ringstraße 	| Geroflinger Straße 	| Schloßlande 	|
        | Length [m]                	| 430                  	| 312                	| 215         	|
        | Direction                 	| S to N               	| W to E             	| NE to SW    	|
        | Lanes (Probe)             	| 2                    	| 1                  	| 2           	|
        | Lanes (Det.)              	| 1                    	| 2                  	| 2           	|
    """)
    st.image("images/recording.gif", caption="Ingolstadt Simulation", 
             use_container_width=False)


    #################################################
    st.header("Analysis of the Data", divider=True)
    link = st.selectbox("Select Link: ",
                        ("Link-1", "Link-2", "Link-3"),
                        accept_new_options=False)

    fd_analysis(link)
    fcd_trajectories(link)

if __name__ == "__main__":
    main()