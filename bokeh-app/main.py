# -*- coding: utf-8 -*-
"""
Created on Tue May 12 10:24:18 2020

@author: tangu
"""

""" Libraries """
# usual libraries
import numpy as np 
import pandas as pd 
import json
import datetime

# Function to convert the date in pandas format datetime64 to format datetime
# It is easier to get dates as String after that
def convert_datetime64_to_datetime( usert: np.datetime64 )->datetime.datetime:
    t = np.datetime64( usert, 'us').astype(datetime.datetime)
    return(t)


# import from bokeh library
from bokeh.models import ColorBar, LogColorMapper, LogTicker, LinearColorMapper
from bokeh.plotting import figure
from bokeh.io import curdoc
from bokeh.layouts import layout
from bokeh.models import (Button, CategoricalColorMapper, ColumnDataSource,
                          HoverTool, Label, SingleIntervalTicker, Slider, RadioButtonGroup, PreText)
from bokeh.layouts import row, widgetbox, layout



""" Load GeoJson file and store data in dictionary"""
# Load geojson file with department data
def get_department_data():
    with open('data/departements.geojson.txt') as f:
        geodata = json.load(f)
        
    
    # Initialization
    department = {}          # To store geodata for each department
    lat_by_department = []   # List of lists of lat for each department
    lon_by_department = []   # List of list of lon for each department
    name_department = []     # List of names of departments
    
    
    # Loop on all department in the geojson loaded file
    for feature in geodata['features']:
        
        # Retrieves the number of the department and add it to list
        number = feature['properties']['code'] 
        
        
        # Retrieves the name of the department and add it to list
        name = feature['properties']['nom']
        name_department.append(name)
        
        # Retrieves the coordinates of the shape of the department
        coordinates = feature['geometry']['coordinates']  
        
        lat = []
        lon = []
        
        # For some region, the coordinates are entered in a really weird way
        # You have to play with lists nested in lists
        for j in range(len(coordinates)):
            lat_intermediate = []
            lon_intermediate = []
            for i in range(len(coordinates[j])):
                if len(coordinates[j][i]) == 2:
                    lat_intermediate.append(coordinates[j][i][1])
                    lon_intermediate.append(coordinates[j][i][0])
                else:
                    for k in range(len(coordinates[j][i])):
                        lat_intermediate.append(coordinates[j][i][k][1])
                        lon_intermediate.append(coordinates[j][i][k][0])
            if len(lat_intermediate) > len(lat):
                lat = lat_intermediate
                lon = lon_intermediate
               
    
        # Add to list of lat and lon for each department
        lat_by_department.append(lat)
        lon_by_department.append(lon)    
        
        # Add new entry to dictionary
        # The number of department is the key
        # The value of the dictionary is a dictionary containign both the name of the department, and list with latitudes and longitudes
        department[number] = {'name':name, 'lat': lat, 'lon': lon}
        
    return(lat_by_department, lon_by_department, name_department, department)


""" Match department and regions """
def get_matching_region_department(department):
    # load dataset
    df_match_region_department = pd.read_csv("data/region_to_department.csv", sep=";")
    
    # Drop NA
    df_match_region_department = df_match_region_department.dropna()
    
    """ ------------ Create matching dictionary ------------"""
    # Initialize
    region_to_department = {}
    
    # Fill dictionnary
    for id in list(df_match_region_department["NUMÉRO"].unique()):
        region = list(df_match_region_department.loc[df_match_region_department['NUMÉRO'] == id, 'REGION'])[0]
        
        # Adapt to dataframe way of writting Grand-Est
        if region == "Grand Est":
            region = "Grand-Est"
            
        region_to_department[id] = region
        
    return(region_to_department)
    
    
    
    
""" Load energy data and store data in dicitionaries"""
def prepare_energy_data(lat_by_department, lon_by_department, department, region_to_department):
    # Load data
    df_energy = pd.read_csv("data/eco2mix-regional-tr.csv", sep=";")
    
    # Keep only data we are interested in
    df_energy = df_energy[['Région', 'Date', 'Heure', 'Consommation (MW)', 'Thermique (MW)', 'Nucléaire (MW)']]
    
    
    # Rename columns
    df_energy.rename(columns={"Région":"region",
                               "Date":"date",    
                               "Heure":"hour",
                               "Consommation (MW)":"general_consumption",
                               "Thermique (MW)":"thermal_power",
                               "Nucléaire (MW)":"nuclear_power"
                               }, inplace=True)
    
    # Drop NA values
    #df_energy = df_energy.dropna()
    df_energy = df_energy.dropna(subset=['date'])
    
    # Convert string date to datetime
    df_energy["date"] = pd.to_datetime(df_energy["date"], format='%Y-%m-%d')
    
    # The consumption reading is taken every quarter of an hour in a day. 
    # We're interested in daily data, so we're summing by day
    df_energy_by_department_and_date = df_energy.groupby(['region', 'date']).sum()
    
    """ Treatment for energy data per day """
    """ Initialization for all type of maps"""

    # Get list of dates in the dataframe
    energy_dates = list(df_energy['date'].unique())
    
    # Get list of regions in dataframe
    energy_regions = list(df_energy['region'].unique())
    
    # Initialization of list to fill with dates from dataframe as String
    energy_dates_str = [] 
    
    # Initizialisation of a counter of dates
    # We want each date to be provided an unique int id to use if in bokeh later
    id_date = 0
    
    """ Initialization concerning maps with non cumulated data """
    
    # Initialization of dictionaries to contain data for each date and each department
    general_consumption_by_date_as_integer = {}
    thermal_power_by_date_as_integer = {}
    nuclear_power_by_date_as_integer = {}
    
    
    
    """ Fill all dictionaries """
    # Create a dictionary with all dates as key, and list of related data for each department as the related date as value
    # The list of data for each department is field in the same order as the department appear in the department dictionary
    for date in energy_dates:
        
        # Initialization
        general_consumption_by_department_at_date = []
        thermal_power_by_department_at_date = []
        nuclear_power_by_department_at_date = []
        
        # Find values in dataframe
        for id in department:
            region = region_to_department[id]
        
            # Only 7 regions ar ein the dataset
            # Overseas regions are not included in the dataset. They are assigned negative consumption values
            if region not in energy_regions:
                general_consumption_by_department_at_date.append(0)
                thermal_power_by_department_at_date.append(0)
                nuclear_power_by_department_at_date.append(0)
                
            # For some region we miss data at some date
            # We replace the values with -1 values for now
            # Would be better to replace it with an average of surrounding values
            elif (region, date) not in df_energy_by_department_and_date.index:
                general_consumption_by_department_at_date.append(0)
                thermal_power_by_department_at_date.append(0)
                nuclear_power_by_department_at_date.append(0)
    
            else:
                general_consumption_by_department_at_date.append(df_energy_by_department_and_date.at[(region, date), 'general_consumption'])
                thermal_power_by_department_at_date.append(df_energy_by_department_and_date.at[(region, date), 'thermal_power'])
                nuclear_power_by_department_at_date.append(df_energy_by_department_and_date.at[(region, date), 'nuclear_power'])
        
        
        # Convert the date in pandas format datetime64 to format datetime
        date = convert_datetime64_to_datetime(date)
        
        # Convert the date in datetime format as a String
        date = date.strftime("%m/%d/%Y")
        
        # Add to the String converted date list
        energy_dates_str.append(date)
        
        # Update non cumulated data dictionaries
        general_consumption_by_date_as_integer[id_date] = general_consumption_by_department_at_date
        thermal_power_by_date_as_integer[id_date] = thermal_power_by_department_at_date
        nuclear_power_by_date_as_integer[id_date] = nuclear_power_by_department_at_date
        
            
        # Increase counter
        id_date += 1
        
    """ Arranges dictionaries for all three features, cumulated or not """
    
    # Create and fill dictionary
    energy_data_by_feature = {}
    
    # Here we have only one feature
    energy_data_by_feature['by_date'] = {"general_consumption":general_consumption_by_date_as_integer,
                                 "thermal_power": thermal_power_by_date_as_integer,
                                 "nuclear_power": nuclear_power_by_date_as_integer}
    
  
    
    # Dictionary of min / max values for each combo of mode/feature which doesn't take 0 values into account
    # Usefull as some regions doesn't use any thermal/nuclear energy
    energy_data_min_max_without_0 = {}          
    
    df_energy_by_department_and_date_without_0 =  df_energy_by_department_and_date[(df_energy_by_department_and_date != 0).all(1)]
    
    energy_data_min_max_without_0['by_date'] = {"general_consumption": {"min": df_energy_by_department_and_date_without_0["general_consumption"].min(),
                                                           "max": df_energy_by_department_and_date_without_0["general_consumption"].max()},
                                 "thermal_power": {"min": df_energy_by_department_and_date_without_0["thermal_power"].min(),
                                                           "max": df_energy_by_department_and_date_without_0["thermal_power"].max()},
                                 "nuclear_power": {"min": df_energy_by_department_and_date_without_0["nuclear_power"].min(),
                                                           "max": df_energy_by_department_and_date_without_0["nuclear_power"].max()}
                                         }

    return(energy_data_by_feature, energy_data_min_max_without_0, energy_dates_str)
    

""" -------------------- General variables for plot --------------------  """   
title = "General Energy Consumption per Day"
lat_by_department, lon_by_department, name_department, department = get_department_data() 
region_to_department = get_matching_region_department(department)
data_rate, data_min_max, energy_dates_str  = prepare_energy_data(lat_by_department, lon_by_department, department, region_to_department)

# Chosen color palette
from bokeh.palettes import Inferno256 as palette_inferno
palette = tuple(reversed(palette_inferno))

# List of tools used in the map
tools = "pan,wheel_zoom,reset,hover,save"

# Size Maps
plot_width=450
plot_height=400

name_tooltips = "Energy consumption in the region"  


""" ----------- Create the color mapper -----------  """
color_mapper = LogColorMapper(palette=palette, low=data_min_max['by_date']['general_consumption']['min'], high=data_min_max['by_date']['general_consumption']['max'])


""" ----------- Dictionnary of data to pass to bokeh as argument and variables -----------  """
mode = 'by_date' #mode by default and the only one implemented yet

data=dict(x = lon_by_department,
          y = lat_by_department,
          name = name_department,
          rate = data_rate["by_date"]['general_consumption'][0])

source=ColumnDataSource(data)

""" ----------- Create the figure -----------  """
p = figure(title=title, tools=tools,
           x_axis_location=None, y_axis_location=None,
           plot_width=plot_width, plot_height=plot_height,
           tooltips=[("Name", "@name"), (name_tooltips, "@rate"), ("(Long, Lat)", "($x, $y)")]
          )
p.grid.grid_line_color = None
p.hover.point_policy = "follow_mouse"

p.patches('x', 'y', source=source,
          fill_color={'field': 'rate', 'transform': color_mapper},
          fill_alpha=0.7, line_color="black", line_width=0.5)

#Add color bar to figure
color_bar = ColorBar(color_mapper=color_mapper, ticker=LogTicker(),
                     label_standoff=12, border_line_color=None, location=(0,0))

p.add_layout(color_bar, 'right')


""" ----------- Set up callbacks -----------  """
# Update Map while changing feature or mode
def update_map(attrname, old, new):
    
    # Retrieve the new feature to use
    feature = label_features[button_choice.active] 
    
    # Update the title of the graph
    title_update(feature, mode)
    
    # Update the color map
    color_mapper_update(feature, mode)
    
    # Update map
    int_date = date_slider.value # Get integer for the currently chosen date in the slider
    source.data['rate'] = data_rate[mode][feature][int_date]



# Update title of map when feature or mode is changed
def title_update(feature, mode):
    if mode == 'by_date':
        if feature == "general_consumption":
            new_title = "General energy consumption per Day"
        if feature == "thermal_power":
            new_title = "Thermal power consumption per Day"
        if feature == "nuclear_power":
            new_title = "Nuclear power consumption per Day"
    p.title.text = new_title
            
  
    
# Update color mapper of map when features or mode displayed are changed
def color_mapper_update(feature, mode):
    # Change the limits of the Color Mapper
    color_mapper.update(low = data_min_max[mode][feature]["min"], high = data_min_max[mode][feature]["max"])
        

# Update the slider on a click of the user
def slider_update(attrname, old, new):
    # Retrieve current date
    int_date = date_slider.value 
    date_slider.title = "Date :" + energy_dates_str[int_date]
    
    # Retrieve current feature Label
    feature = label_features[button_choice.active]
    
    # Change data
    source.data['rate'] = data_rate[mode][feature][int_date]


# Update the slider automatically when clicking on the animation button
def animate_update():
    int_date = date_slider.value + 1
    # Go back to the beginning if slider reach the end
    if int_date > len(energy_dates_str) - 1 :
        int_date = 0
    date_slider.value = int_date


# Change the button label depending if it is playing or not
callback_id = None
def animate():
    global callback_id
    if button_animation.label == '► Play':
        button_animation.label = '❚❚ Pause'
        callback_id = curdoc().add_periodic_callback(animate_update, 200)
    else:
        button_animation.label = '► Play'
        curdoc().remove_periodic_callback(callback_id)
    
    
""" ----------- Set up widgets and events -----------  """
# Button to choose the feature to display in the map
label_features = ["general_consumption", "thermal_power", "nuclear_power"] # labels of possible features
button_choice = RadioButtonGroup(labels=["General Consumption", "Thermal Power", "Nuclear Power"], active=0)
button_choice.on_change('active', update_map)
# As the RadioButton isn't implemented with a title option, we add a PreText object before it
title_button_choice = PreText(text= "Choose the feature to display", style={'font-size':'12pt', 
                 'color': 'black', 
                 'font-family': 'sans-serif'})


# Slider for the date
date_slider = Slider(title="Date "+ energy_dates_str[0], start = 0, end = len(energy_dates_str)-1, value = 0, step=1, show_value=False)
date_slider.on_change('value', slider_update)

# Button to animate the slider
button_animation = Button(label='► Play', width=60)
button_animation.on_click(animate)
button_animation.visible = False # Initially the slider is not visible

# Special mention 
title_explanation = PreText(text= "Departments in yellow have an unknown consumption", style={'font-size':'9pt', 
                 'color': 'black', 
                 'font-family': 'sans-serif'})
   

# Set up layouts and add to document
inputs = widgetbox(title_button_choice, button_choice, date_slider, button_animation, title_explanation)
layout = row(p, inputs)

# Render in HTML
curdoc().add_root(layout)
curdoc().title = title
