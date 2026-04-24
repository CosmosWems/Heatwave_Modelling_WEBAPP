##Heatwave Modelling Dashboard

##Overview

The Heatwave Modelling Dashboard is a web application designed to detect, visualise, and analyse heatwave events using temperature data. This application provides a user-friendly interface for uploading datasets, running analyses, and generating informative visualisations and maps related to heatwave occurrences.

## Features

- **Data Upload**: Upload temperature data in CSV format.
- **Event Detection**: Identify heatwave events based on user-defined parameters.
- **Visualisation**: Interactive plots and calendar heatmaps to visualize temperature data and detected heatwave events.
- **Batch Processing**: Process multiple stations of data consecutively.
- **Map Display**: Visualise locations of stations on an interactive map.

## Requirements

Before using the application, ensure you have the following:

- Python 3.x
- Flask
- Pandas
- Numpy
- Plotly
- marineHeatWaves package

## Installation

1. Clone the repository or download the application files.
2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install the required packages using pip:
   ```bash
   pip install Flask pandas numpy plotly marineHeatWaves
   ```
4. Run the application:
   ```bash
   python app.py
   ```
5. Access the dashboard at `http://127.0.0.1:5000`.

## User Manual

### 1. Uploading Data
- **Upload a CSV dataset**: Click on the “Upload & Parse” button and select a CSV file containing temperature records.
- **Column Mapping**: After uploading, select the appropriate columns for date, station, daytime temperature, and nighttime temperature.

### 2. Configuring Parameters
- Define the climatology period (start and end years), percentile for detection, minimum duration for heatwaves, and other parameters. 

### 3. Running Detection
- **Select a target station** from the drop-down menu.
- Click on the “Run Detection” button to identify heatwave events based on the selected parameters.

### 4. Viewing Results
- Navigate to the "Event Summary" tab to view detection results. The summary includes daytime, nighttime, and compound events.
- Data tables display detailed information about each detected heatwave event.

### 5. Visualizations
- Use the "Data Visualization" tab to generate interactive plots:
  - Select the type of event (day or night), plot type (timeseries, block averages, or categories), and define the year range for plotting. 
  - Click “Generate Plot” to view the interactive graph or heatmap.

### 6. Using the Map Feature
- In the "Map" tab, select columns for latitude and longitude to plot the station locations on the map.
- Click on “Plot Stations on Map” to visualize station positions.

### 7. Batch Processing
- Use the "Batch Run" tab to process multiple stations. Select your station(s) and click on “Run Batch Detection” to execute detection for all selected stations.
- Results and statistics will be displayed upon completion.

### 8. Saving Outputs
- Outputs can be saved as CSV files. Click on the "Save Outputs" button.

### 9. Monitoring System Status
- The status bar and log area display the progress of data uploads, detection activities, and errors if any occur during the process.

## Acknowledgments
The application builds on the methodologies provided by the marineHeatWaves package, allowing for efficient detection and analysis of marine heatwave events. Special thanks to Eric C. J. Oliver and collaborators for their foundational work in this field.

## Developer
**Cosmos Senyo Wemegah** (PhD.)  
Research Fellow at EORIC-UENR, Ghana


## Support
For any issues or questions regarding the application, please contact the developer or create an issue on the project's repository page.