import os
import datetime
from datetime import date
import pandas as pd
import numpy as np
import marineHeatWaves as mhw
import plotly.graph_objs as go
import plotly.express as px
from flask import Flask, request, jsonify, render_template_string

import warnings
warnings.filterwarnings("ignore")

app = Flask(__name__)
app.secret_key = "mhw_secret_key"

APP_STATE = {
    'df': None,
    't_ord': None,
    'mhws_day': None,
    'clim_day': None,
    'mhws_night': None,
    'clim_night': None,
    'compound_df': pd.DataFrame(),
    'block_day': pd.DataFrame(),
    'block_night': pd.DataFrame(),
    'filtered_df': None,
    'batch_results': {}
}

# ----------------- HTML & Frontend (Embedded) -----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <title>Heatwave Modelling Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"/>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css"/>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow-x: hidden; }
        .top-navbar { background-color: #1f2326; padding: 10px 20px; border-bottom: 2px solid #3b4045; }
        .left-panel { background-color: #1a1d20; height: calc(100vh - 60px); overflow-y: auto; padding: 20px; border-right: 1px solid #3b4045; }
        .main-content { padding: 20px; height: calc(100vh - 60px); overflow-y: auto; }
        .card { background-color: #2b2f33; border: 1px solid #3b4045; margin-bottom: 15px; }
        .card-header { background-color: #1f2326; font-weight: bold; border-bottom: 1px solid #3b4045; }
        .form-control, .form-select { background-color: #3b4045; color: white; border: 1px solid #555; font-size: 0.9rem; }
        .form-control:focus, .form-select:focus { background-color: #4b5055; color: white; border-color: #0d6efd; box-shadow: none; }
        select[multiple] option:checked { background-color: #0d6efd; color: white; }
        select[multiple] option { padding: 4px 6px; }
        label { font-size: 0.85rem; color: #adb5bd; margin-bottom: 2px; }
        .btn-sm { font-size: 0.8rem; }
        pre { background-color: #1a1d20; padding: 15px; border-radius: 5px; color: #e6eef6; border: 1px solid #333; font-size: 0.8rem; }
        .log-view { background-color: #000; color: #0f0; font-family: monospace; font-size: 0.78rem; height: 160px; overflow-y: scroll; padding: 10px; border-radius: 4px; border: 1px solid #444; }
        .nav-tabs .nav-link.active { background-color: #2b2f33; color: white; border-color: #3b4045 #3b4045 #2b2f33; }
        .nav-tabs .nav-link { color: #adb5bd; }
        .sub-tabs { margin-bottom: 15px; border-bottom: 1px solid #444; }
        .status-bar { height: 20px; background-color: #3b4045; border-radius: 10px; overflow: hidden; margin-top: 10px; }
        .status-fill { height: 100%; background-color: #0d6efd; width: 0%; transition: width 0.3s; }
        #stationMap { height: 500px; border-radius: 6px; border: 1px solid #3b4045; z-index: 1; }
        .batch-station-list { height: 200px; overflow-y: auto; background-color: #3b4045; border: 1px solid #555; border-radius: 4px; }
        .batch-table th { background-color: #1f2326; font-size: 0.8rem; }
        .batch-table td { font-size: 0.78rem; }
        .task-completed { color: #20c997; }
        .task-running { color: #ffc107; }
        .task-error { color: #dc3545; }
        .station-badge { display: inline-block; background: #0d6efd22; border: 1px solid #0d6efd55; border-radius: 4px; padding: 2px 6px; margin: 2px; font-size: 0.75rem; color: #7eb3ff; }
        .map-controls { background-color: #1f2326; border: 1px solid #3b4045; border-radius: 6px; padding: 12px; margin-bottom: 12px; }
        .viz-plot-container { min-height: 420px; background-color: #1a1d20; border-radius: 6px; border: 1px solid #3b4045; padding: 8px; }
        .cal-legend { display:flex; align-items:center; gap:12px; font-size:0.8rem; color:#aaa; margin-top:8px; }
        .cal-legend-hw { display:inline-block; width:18px; height:18px; border:3px solid #a020f0; border-radius:3px; background:transparent; }
    </style>
</head>
<body>

<div class="top-navbar d-flex justify-content-between align-items-center">
    <h5 class="m-0 text-primary fw-bold">&#x1F321; CLI-HEALTH Heatwave Analytics</h5>
    <ul class="nav nav-pills" id="mainTabs" role="tablist">
        <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tab-summary" type="button"><span style="font-size: 30px;">&#x1F5C1;</span> Event Summary</button></li>
        <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-viz" type="button"><span style="font-size: 30px;">&#x1F5E0;</span> Data Visualization</button></li>
        <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-map" type="button"><span style="font-size: 30px;">&#x1F5FA;</span> Map</button></li>
        <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-batch" type="button"><span style="font-size: 30px;">&#x1F5D0;</span> Batch Run</button></li>
        <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tab-about" type="button"><span style="font-size: 30px;">&#x2139;</span> About</button></li>
    </ul>
    <div>
        <button class="btn btn-outline-success btn-sm me-2" onclick="saveCSV()">Save Outputs</button>
        <button class="btn btn-danger btn-sm fw-bold" onclick="forceStop()">&#9632; Stop</button>
    </div>
</div>

<div class="container-fluid p-0">
    <div class="row g-0">
        <div class="col-md-3 left-panel">
            <h6 class="text-uppercase text-muted mb-3 border-bottom pb-2">1. Data Selection</h6>
            <form id="uploadForm" class="mb-3">
                <input type="file" class="form-control form-control-sm mb-2" id="csvFile" accept=".csv" required>
                <button type="submit" class="btn btn-primary btn-sm w-100">&#x2191; Upload & Parse</button>
            </form>

            <h6 class="text-uppercase text-muted mb-3 border-bottom pb-2 mt-4">2. Column Mapping</h6>
            <div class="row g-2 mb-3">
                <div class="col-6">
                    <label>Date</label>
                    <select class="form-select col-dropdown" id="col_date"><option value="">-- Select --</option></select>
                </div>
                <div class="col-6">
                    <label>Station</label>
                    <select class="form-select col-dropdown" id="col_station" onchange="loadStations()"><option value="">-- Select --</option></select>
                </div>
                <div class="col-6">
                    <label>Day Temp (tx)</label>
                    <select class="form-select col-dropdown" id="col_day"><option value="">-- Select --</option></select>
                </div>
                <div class="col-6">
                    <label>Night Temp (tn)</label>
                    <select class="form-select col-dropdown" id="col_night"><option value="">-- Select --</option></select>
                </div>
                <div class="col-12">
                    <label>Target Station <span class="text-info" style="font-size:0.72rem;">(single station)</span></label>
                    <select class="form-select" id="target_station">
                        <option value="">-- Select station column first --</option>
                    </select>
                    <div id="target_station_info" class="text-muted mt-1" style="font-size:0.72rem;"></div>
                </div>
            </div>

            <h6 class="text-uppercase text-muted mb-3 border-bottom pb-2 mt-4">3. Parameters</h6>
            <form id="detectForm">
                <div class="row g-2">
                    <div class="col-6"><label>Clim Start</label><input type="number" class="form-control" id="clim_start" value="1981"></div>
                    <div class="col-6"><label>Clim End</label><input type="number" class="form-control" id="clim_end" value="2010"></div>
                    <div class="col-6"><label>Percentile</label><input type="number" class="form-control" id="pctile" value="90"></div>
                    <div class="col-6"><label>Min Duration</label><input type="number" class="form-control" id="min_dur" value="3"></div>
                    <div class="col-6">
                        <label>Join Gaps</label>
                        <select class="form-select" id="join_gaps"><option value="false">No</option><option value="true">Yes</option></select>
                    </div>
                    <div class="col-6"><label>Max Gap</label><input type="number" class="form-control" id="max_gap" value="1"></div>
                </div>
                <button type="submit" class="btn btn-success w-100 mt-3 fw-bold">&#x25BA; Run Detection</button>
            </form>

            <h6 class="text-uppercase text-muted mb-2 border-bottom pb-2 mt-4">System Status</h6>
            <div class="status-bar mb-2"><div class="status-fill" id="status-bar-fill"></div></div>
            <div id="status-label" class="text-muted mb-1" style="font-size:0.75rem;">Ready</div>
            <div class="log-view" id="sys-log">&#x2713; System initialized... Ready for data.<br></div>
        </div>

        <div class="col-md-9 main-content">
            <div class="tab-content" id="mainTabContent">

                <div class="tab-pane fade show active" id="tab-summary">
                    <h4 class="mb-4">Detection Results <span id="current_station_display" class="text-info fs-6 ms-2"></span></h4>
                    <ul class="nav nav-tabs sub-tabs" role="tablist">
                        <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#sum-day" type="button">&#x1F31E; Daytime Events</button></li>
                        <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#sum-night" type="button">&#x1F319; Nighttime Events</button></li>
                        <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#sum-comp" type="button">&#x1F525; Compound Events</button></li>
                    </ul>
                    <div class="tab-content">
                        <div class="tab-pane fade show active" id="sum-day"><div class="card"><div class="card-body"><pre id="res_day"></pre><div id="table_day" class="mt-3"></div>Run detection to view daytime statistics...</pre></div></div></div>
                        <div class="tab-pane fade" id="sum-night"><div class="card"><div class="card-body"><pre id="res_night"></pre><div id="table_night" class="mt-3"></div>Run detection to view nighttime statistics...</pre></div></div></div>
                        <div class="tab-pane fade" id="sum-comp"><div class="card"><div class="card-body"><pre id="res_compound"></pre><div id="table_compound" class="mt-3"></div>Run detection to view compound event statistics...</pre></div></div></div>
                    </div>
                </div>

                <div class="tab-pane fade" id="tab-viz">
                    <ul class="nav nav-tabs sub-tabs" id="vizSubTabs" role="tablist">
                        <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#viz-interact" type="button">&#x1F4CA; Interactive Plots</button></li>
                        <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#viz-cal" type="button">&#x1F4C5; Calendar Heatmap</button></li>
                    </ul>

                    <div class="card mb-3">
                        <div class="card-body bg-dark py-2">
                            <form id="plotForm" class="row g-2 align-items-end">
                                <div class="col-auto">
                                    <label>Event Type</label>
                                    <select class="form-select form-select-sm" id="plot_event">
                                        <option value="day">Daytime</option>
                                        <option value="night">Nighttime</option>
                                    </select>
                                </div>
                                <div class="col-auto" id="plot_type_container">
                                    <label>Plot Type</label>
                                    <select class="form-select form-select-sm" id="plot_type">
                                        <option value="timeseries">Timeseries</option>
                                        <option value="block">Block Averages</option>
                                        <option value="category">Categories</option>
                                    </select>
                                </div>
                                <div class="col-auto" id="viz_start_container">
                                    <label>Start Year</label>
                                    <input type="number" class="form-control form-control-sm" id="plot_ys" value="1981" style="width:90px;">
                                </div>
                                <div class="col-auto" id="viz_end_container">
                                    <label>End Year</label>
                                    <input type="number" class="form-control form-control-sm" id="plot_ye" value="2018" style="width:90px;">
                                </div>
                                <div class="col-auto" id="cal_year_container" style="display:none;">
                                    <label>Calendar Year</label>
                                    <input type="number" class="form-control form-control-sm" id="cal_year" value="2018" style="width:100px;">
                                </div>
                                <div class="col-auto" id="btn_generate_container">
                                    <button type="submit" class="btn btn-outline-primary btn-sm" id="btn_generate_plot">
                                        &#x25BA; Generate Plot
                                    </button>
                                </div>
                                <div class="col-auto" id="btn_cal_container" style="display:none;">
                                    <button type="button" class="btn btn-outline-primary btn-sm" onclick="generateCalendarPlot()">
                                        &#x25BA; Generate Calendar
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>

                    <div class="tab-content">
                        <div class="tab-pane fade show active" id="viz-interact">
                            <div class="viz-plot-container" id="vizPlotContainer">
                                <div class="text-muted text-center py-5" id="vizPlotPlaceholder">
                                    <span style="font-size:2rem;">&#x1F4CA;</span><br>
                                    Select event type &amp; plot type above, then click <b>Generate Plot</b>.
                                </div>
                            </div>
                        </div>

                        <div class="tab-pane fade" id="viz-cal">
                            <div class="viz-plot-container" id="calendarPlotContainer" style="min-height:360px;">
                                <div class="text-muted text-center py-5" id="calendarPlotPlaceholder">
                                    <span style="font-size:2rem;">&#x1F4C5;</span><br>
                                    Select a year and event type above, then click <b>Generate Calendar</b>.
                                </div>
                                <div id="calendarPlotDiv" style="width:100%; display:none;"></div>
                            </div>
                            <div class="cal-legend mt-2" id="calLegend" style="display:none;">
                                <span class="cal-legend-hw"></span>
                                <span>Heatwave day (detected)</span>
                                <span style="margin-left:16px; font-size:0.75rem; color:#888;">Colour fill = temperature · Purple border = heatwave day</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="tab-pane fade" id="tab-map">
                    <h4 class="mb-3">&#x1F5FA; Station Spatial Map</h4>
                    <div class="map-controls">
                        <div class="row g-3 align-items-end">
                            <div class="col-md-3">
                                <label>Latitude Column</label>
                                <select class="form-select col-dropdown" id="col_lat"><option value="">-- Upload data first --</option></select>
                            </div>
                            <div class="col-md-3">
                                <label>Longitude Column</label>
                                <select class="form-select col-dropdown" id="col_lon"><option value="">-- Upload data first --</option></select>
                            </div>
                            <div class="col-md-3">
                                <label>Station Label Column</label>
                                <select class="form-select col-dropdown" id="map_station_col"><option value="">-- Optional --</option></select>
                            </div>
                            <div class="col-md-3">
                                <button class="btn btn-primary w-100" onclick="plotStationsOnMap()">
                                    &#x1F4CD; Plot Stations on Map
                                </button>
                            </div>
                        </div>
                        <div id="map_info" class="text-muted mt-2" style="font-size:0.8rem;"></div>
                    </div>
                    <div id="stationMap"></div>
                    <div id="map_legend" class="mt-2 text-muted" style="font-size:0.78rem;"></div>
                </div>

                <div class="tab-pane fade" id="tab-batch">
                    <h4 class="mb-1">&#x26A1; Batch Process Multiple Stations</h4>
                    <p class="text-muted mb-3" style="font-size:0.85rem;">Select one or more stations to run heatwave detection consecutively. Results and statistics are shown below.</p>

                    <div class="row g-3">
                        <div class="col-md-4">
                            <div class="card h-100">
                                <div class="card-header">Station Selection</div>
                                <div class="card-body">
                                    <label class="mb-1">Available Stations <span class="text-muted" style="font-size:0.72rem;">(Ctrl+Click to multi-select)</span></label>
                                    <select multiple class="form-select batch-station-list" id="batch_stations" style="height:180px; font-size:0.82rem;">
                                        <option disabled>Load data and set station column first</option>
                                    </select>
                                    <div class="d-flex gap-2 mt-2">
                                        <button class="btn btn-outline-secondary btn-sm flex-fill" onclick="batchSelectAll()">Select All</button>
                                        <button class="btn btn-outline-secondary btn-sm flex-fill" onclick="batchClearAll()">Clear</button>
                                    </div>
                                    <div id="batch_selection_info" class="text-info mt-2" style="font-size:0.75rem;"></div>
                                    <hr>
                                    <button class="btn btn-success w-100 fw-bold" id="batchRunBtn" onclick="runBatch()">
                                        &#x25BA; Run Batch Detection
                                    </button>
                                    <div id="batch_progress_label" class="text-muted mt-2 text-center" style="font-size:0.78rem;"></div>
                                </div>
                            </div>
                        </div>

                        <div class="col-md-8">
                            <ul class="nav nav-tabs sub-tabs" id="batchSubTabs" role="tablist">
                                <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#batch-results" type="button">&#x1F4CB; Batch Results</button></li>
                                <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#batch-stats" type="button">&#x1F4CA; Station Statistics</button></li>
                                <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#batch-log" type="button">&#x1F4DD; Task Log</button></li>
                            </ul>
                            <div class="tab-content">
                                <div class="tab-pane fade show active" id="batch-results">
                                    <div class="card">
                                        <div class="card-body p-2">
                                            <div id="batch_results_container">
                                                <div class="text-muted text-center py-5">Run batch detection to see results here.</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="tab-pane fade" id="batch-stats">
                                    <div class="card">
                                        <div class="card-body p-2">
                                            <div id="batch_stats_container">
                                                <div class="text-muted text-center py-5">Run batch detection to see comparative statistics.</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="tab-pane fade" id="batch-log">
                                    <div class="card">
                                        <div class="card-body p-0">
                                            <div id="batch_task_log" class="log-view" style="height:340px; border:none; border-radius:0;">
                                                Batch task log will appear here...<br>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                 
                <div class="tab-pane fade" id="tab-about">
                    <div class="card">
                        <div class="card-header">About This Application</div>
                            <div class="card-body" style="font-size:0.9rem; line-height:1.6;">
            
                            <h5 class="text-info">How to Use</h5>
                            <ul>
                                <li>Upload a CSV dataset containing temperature records.</li>
                                <li>Map the required columns (Date, Station, Daytime, Nighttime).</li>
                                <li>Select a station and configure detection parameters.</li>
                                <li>Run detection to identify heatwave events.</li>
                                <li>Explore outputs via Event Summary, Visualizations, Map, and Batch tools.</li>
                            </ul>

                            <hr>

                            <h5 class="text-info">Developer</h5>
                            <p>
                                <b><a href="https://scholar.google.com/citations?user=e5_WEhEAAAAJ&hl=en&oi=ao">Cosmos Senyo Wemegah (PhD.)</a></b><br>
                                <a href="https://uenr.edu.gh/staff/cosmos-senyo-wemegah-phd/">Research Fellow at EORIC-UENR, Ghana.</a><br><br>
                                This program was based on his PhD research findings on heat stress,
                                climate-health interactions, and extreme temperature analytics.
                                This was used to detect heatwaves in Ghanaian major cities including Accra, Kumasi and Tamale.
                                This was published as <a href="https://doi.org/10.1002/joc.8889">Evidence of Heatwaves: Characteristics and Trends in Selected Ghanaian Cities</a>
                            </p>

                            <hr>

                            <h5 class="text-info">Acknowledgment</h5>
                            <p>
                                This application builds upon the foundational work of the 
                                <b>marineHeatWaves</b> Python package developed by <a href="https://scholar.google.com/citations?user=0kE8u3EAAAAJ&hl=en">Eric C. J. Oliver</a>  
                                and collaborators for detecting and analyzing marine heatwave events published as <a href="https://doi.org/10.1016/j.pocean.2015.12.014">A hierarchical approach to defining marine heatwaves</a>.
                                Their methodology has been adapted here for atmospheric heatwave analysis in the article <a href="https://doi.org/10.1002/joc.8889">Evidence of Heatwaves: Characteristics and Trends in Selected Ghanaian Cities</a>.
                            </p>

                        </div>
                    </div>
                </div>
            </div></div>
    </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

<script>
    // ===== GLOBALS =====
    let leafletMap = null;
    let mapMarkers = [];
    let batchAborted = false;
    let batchData = {};

    const logBox = document.getElementById('sys-log');
    const batchLog = document.getElementById('batch_task_log');

    function logMsg(msg) {
        const time = new Date().toLocaleTimeString();
        logBox.innerHTML += `[${time}] ${msg}<br>`;
        logBox.scrollTop = logBox.scrollHeight;
    }

    function batchLogMsg(msg) {
        const time = new Date().toLocaleTimeString();
        batchLog.innerHTML += `[${time}] ${msg}<br>`;
        batchLog.scrollTop = batchLog.scrollHeight;
    }

    function setProgress(pct, label) {
        document.getElementById('status-bar-fill').style.width = pct + '%';
        if (label) document.getElementById('status-label').innerText = label;
    }

    function forceStop() {
        batchAborted = true;
        logMsg('<span class="task-error">&#9632; Process aborted by user.</span>');
        setProgress(0, 'Stopped');
    }

    function saveCSV() {
        logMsg('Outputs saved as CSV. (Hook backend /api/export here)');
    }

    // ===== UPLOAD =====
    document.getElementById('uploadForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        logMsg('Uploading file...');
        setProgress(30, 'Uploading...');

        let formData = new FormData();
        formData.append('file', document.getElementById('csvFile').files[0]);

        try {
            let res = await fetch('/api/upload', { method: 'POST', body: formData });
            let data = await res.json();
            if (data.error) throw new Error(data.error);

            logMsg(`&#x2713; File parsed. Rows: ${data.rows}. Columns: ${data.columns.length}`);
            setProgress(100, 'File loaded');

            const cols = data.columns;

            document.querySelectorAll('.col-dropdown').forEach(sel => {
                sel.innerHTML = '<option value="">-- Select --</option>';
                cols.forEach(c => sel.innerHTML += `<option value="${c}">${c}</option>`);
            });

            const guess = (id, names) => {
                for (let n of names) {
                    if (cols.includes(n)) { document.getElementById(id).value = n; break; }
                }
            };
            guess('col_date',        ['Date','date','DATE','time','Time']);
            guess('col_station',     ['station','Station','STATION','stn','STN']);
            guess('col_day',         ['tx','TX','Tx','tmax','TMAX','temp_day']);
            guess('col_night',       ['tn','TN','Tn','tmin','TMIN','temp_night']);
            guess('col_lat',         ['lat','LAT','Lat','latitude','Latitude','LATITUDE']);
            guess('col_lon',         ['lon','LON','Lon','longitude','Longitude','LONGITUDE','lng']);
            guess('map_station_col', ['station','Station','STATION','stn']);

            if (document.getElementById('col_station').value) {
                await loadStations();
            }
            setTimeout(() => setProgress(0, 'Ready'), 1000);
        } catch (err) {
            logMsg(`<span class="task-error">Error: ${err.message}</span>`);
            setProgress(0, 'Error');
        }
    });

    // ===== LOAD STATIONS =====
    async function loadStations() {
        const col = document.getElementById('col_station').value;
        if (!col) {
            document.getElementById('target_station').innerHTML = '<option value="">-- Select station column first --</option>';
            document.getElementById('target_station_info').innerText = '';
            return;
        }
        try {
            let res = await fetch(`/api/stations?col=${encodeURIComponent(col)}`);
            let data = await res.json();
            if (data.error) throw new Error(data.error);

            const stations = data.stations;
            const stationSel = document.getElementById('target_station');
            stationSel.innerHTML = '<option value="">-- Select a station --</option>';
            stations.forEach(s => stationSel.innerHTML += `<option value="${s}">${s}</option>`);
            document.getElementById('target_station_info').innerText = `${stations.length} station(s) available`;
            logMsg(`&#x2713; Loaded ${stations.length} stations from column "${col}".`);

            const batchSel = document.getElementById('batch_stations');
            batchSel.innerHTML = '';
            stations.forEach(s => batchSel.innerHTML += `<option value="${s}">${s}</option>`);
            updateBatchSelectionInfo();
        } catch (err) {
            logMsg(`<span class="task-error">Station load error: ${err.message}</span>`);
        }
    }

    // ===== DETECTION =====
    document.getElementById('detectForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const station = document.getElementById('target_station').value;
        if (!station) {
            logMsg('<span class="task-error">Please select a target station before running detection.</span>');
            return;
        }

        logMsg(`Starting MHW detection for station: <b>${station}</b>...`);
        setProgress(50, `Running: ${station}`);

        let payload = buildPayload(station);

        try {
            let res = await fetch('/api/detect', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify(payload)
            });
            let data = await res.json();
            if (data.error) throw new Error(data.error);

            document.getElementById('res_day').innerText     = data.day_summary;
            document.getElementById('res_night').innerText   = data.night_summary;
            document.getElementById('res_compound').innerText = data.compound_summary;
            document.getElementById('current_station_display').innerText = `\u2192 Station: ${station}`;
            renderEventTable(data.day_events, 'table_day', 'day');
            renderEventTable(data.night_events, 'table_night', 'night');
            renderEventTable(data.compound_events, 'table_compound', 'compound');
            if (data.year_max) {
                document.getElementById('cal_year').value  = data.year_max;
                document.getElementById('plot_ye').value   = data.year_max;
                document.getElementById('plot_ys').value   = data.year_min || data.year_max - 10;
            }

            logMsg(`<span class="task-completed">&#x2713; Detection complete for: ${station}</span>`);
            setProgress(100, 'Done');
            new bootstrap.Tab(document.querySelector('[data-bs-target="#tab-summary"]')).show();
            setTimeout(() => setProgress(0, 'Ready'), 1200);
        } catch (err) {
            logMsg(`<span class="task-error">Detection Failed: ${err.message}</span>`);
            setProgress(0, 'Error');
        }
    });

    function buildPayload(station) {
        return {
            col_date:       document.getElementById('col_date').value,
            col_day:        document.getElementById('col_day').value,
            col_night:      document.getElementById('col_night').value,
            col_station:    document.getElementById('col_station').value,
            target_station: station,
            clim_start:     parseInt(document.getElementById('clim_start').value),
            clim_end:       parseInt(document.getElementById('clim_end').value),
            pctile:         parseInt(document.getElementById('pctile').value),
            min_dur:        parseInt(document.getElementById('min_dur').value),
            join_gaps:      document.getElementById('join_gaps').value === 'true',
            max_gap:        parseInt(document.getElementById('max_gap').value)
        };
    }

    // ===== VIZ SUB-TAB TOGGLE =====
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
        tab.addEventListener('shown.bs.tab', event => {
            const target = event.target.getAttribute('data-bs-target');

            if (target === '#viz-cal') {
                document.getElementById('plot_type_container').style.display   = 'none';
                document.getElementById('viz_start_container').style.display   = 'none';
                document.getElementById('viz_end_container').style.display     = 'none';
                document.getElementById('cal_year_container').style.display    = 'block';
                document.getElementById('btn_generate_container').style.display = 'none';
                document.getElementById('btn_cal_container').style.display     = 'block';
            } else if (target === '#viz-interact') {
                document.getElementById('plot_type_container').style.display   = 'block';
                document.getElementById('viz_start_container').style.display   = 'block';
                document.getElementById('viz_end_container').style.display     = 'block';
                document.getElementById('cal_year_container').style.display    = 'none';
                document.getElementById('btn_generate_container').style.display = 'block';
                document.getElementById('btn_cal_container').style.display     = 'none';
            }

            if (target === '#tab-map' && leafletMap) {
                setTimeout(() => leafletMap.invalidateSize(), 100);
            }
        });
    });

    // ===== INTERACTIVE PLOTS (all types) =====
    document.getElementById('plotForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        logMsg('Generating interactive plot...');
        setProgress(40, 'Plotting...');

        const payload = {
            event: document.getElementById('plot_event').value,
            type:  document.getElementById('plot_type').value,
            ys:    parseInt(document.getElementById('plot_ys').value),
            ye:    parseInt(document.getElementById('plot_ye').value)
        };

        try {
            let res = await fetch('/api/plot_viz', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify(payload)
            });
            let data = await res.json();
            if (data.error) throw new Error(data.error);

            const container = document.getElementById('vizPlotContainer');
            container.innerHTML = '';

            data.plots.forEach((plotJson) => {
                let fig = JSON.parse(plotJson);
                let div = document.createElement('div');
                div.style.width         = '100%';
                div.style.marginBottom  = '12px';
                container.appendChild(div);
                Plotly.newPlot(div, fig.data, fig.layout, { responsive: true, displaylogo: false });
            });

            logMsg('<span class="task-completed">&#x2713; Interactive plots rendered.</span>');
            setProgress(100, 'Done');
            setTimeout(() => setProgress(0, 'Ready'), 1000);
        } catch (err) {
            logMsg(`<span class="task-error">Plot Error: ${err.message}</span>`);
            setProgress(0, 'Error');
        }
    });

    // ===== CALENDAR HEATMAP =====
    async function generateCalendarPlot() {
        const year     = parseInt(document.getElementById('cal_year').value);
        const tempType = document.getElementById('plot_event').value;

        logMsg(`Generating calendar heatmap for ${year} (${tempType})...`);
        setProgress(55, 'Building calendar...');

        try {
            let res = await fetch('/api/calendar_plot', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ year: year, tempType: tempType })
            });
            let data = await res.json();
            if (data.error) throw new Error(data.error);

            let fig = JSON.parse(data.plot);
            const plotDiv = document.getElementById('calendarPlotDiv');
            plotDiv.style.display = 'block';
            document.getElementById('calendarPlotPlaceholder').style.display = 'none';

            Plotly.react(plotDiv, fig.data, fig.layout, { responsive: true, displaylogo: false });
            document.getElementById('calLegend').style.display = data.hw_count > 0 ? 'flex' : 'none';

            logMsg(`<span class="task-completed">&#x2713; Calendar heatmap generated (${data.hw_count} heatwave day(s) highlighted).</span>`);
            setProgress(100, 'Done');
            setTimeout(() => setProgress(0, 'Ready'), 1000);
        } catch (err) {
            logMsg(`<span class="task-error">Calendar Error: ${err.message}</span>`);
            setProgress(0, 'Error');
        }
    }

    // ===== MAP =====
    function initMap() {
        if (leafletMap) return;
        leafletMap = L.map('stationMap').setView([0, 0], 2);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 18
        }).addTo(leafletMap);
    }

    async function plotStationsOnMap() {
        const colLat = document.getElementById('col_lat').value;
        const colLon = document.getElementById('col_lon').value;
        const colSt  = document.getElementById('map_station_col').value;

        if (!colLat || !colLon) {
            document.getElementById('map_info').innerHTML = '<span class="text-danger">Please select both Latitude and Longitude columns.</span>';
            return;
        }

        document.getElementById('map_info').innerHTML = '<span class="text-warning">Loading station data...</span>';
        logMsg('Fetching station coordinates for map...');

        try {
            let res = await fetch('/api/map_data', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ col_lat: colLat, col_lon: colLon, col_station: colSt })
            });
            let data = await res.json();
            if (data.error) throw new Error(data.error);

            initMap();
            leafletMap.invalidateSize();

            mapMarkers.forEach(m => leafletMap.removeLayer(m));
            mapMarkers = [];

            const stations = data.stations;
            if (!stations || stations.length === 0) {
                document.getElementById('map_info').innerHTML = '<span class="text-danger">No valid coordinate data found.</span>';
                return;
            }

            const bounds = [];
            stations.forEach(st => {
                const marker = L.circleMarker([st.lat, st.lon], {
                    radius: 8, fillColor: '#0d6efd', color: '#7eb3ff',
                    weight: 1.5, opacity: 1, fillOpacity: 0.8
                }).addTo(leafletMap);
                const label = st.name ? `<b>${st.name}</b><br>` : '';
                marker.bindPopup(`${label}Lat: ${st.lat.toFixed(4)}<br>Lon: ${st.lon.toFixed(4)}`);
                mapMarkers.push(marker);
                bounds.push([st.lat, st.lon]);
            });

            if (bounds.length > 0) leafletMap.fitBounds(bounds, { padding: [30, 30] });

            document.getElementById('map_info').innerHTML = `<span class="text-success">&#x2713; Plotted <b>${stations.length}</b> unique station location(s) on the map.</span>`;
            document.getElementById('map_legend').innerHTML = `<span class="station-badge">&#x25CF; ${stations.length} station(s) shown</span> &nbsp; Click a marker for details.`;
            logMsg(`<span class="task-completed">&#x2713; Map rendered with ${stations.length} stations.</span>`);
        } catch (err) {
            document.getElementById('map_info').innerHTML = `<span class="text-danger">Map Error: ${err.message}</span>`;
            logMsg(`<span class="task-error">Map Error: ${err.message}</span>`);
        }
    }

    // ===== BATCH =====
    function updateBatchSelectionInfo() {
        const sel   = document.getElementById('batch_stations');
        const count = sel ? Array.from(sel.selectedOptions).length : 0;
        document.getElementById('batch_selection_info').innerText = count > 0 ? `${count} station(s) selected` : 'No stations selected';
    }

    document.addEventListener('DOMContentLoaded', () => {
        const batchSel = document.getElementById('batch_stations');
        if (batchSel) batchSel.addEventListener('change', updateBatchSelectionInfo);
    });

    function batchSelectAll() {
        const sel = document.getElementById('batch_stations');
        Array.from(sel.options).forEach(o => o.selected = true);
        updateBatchSelectionInfo();
    }

    function batchClearAll() {
        const sel = document.getElementById('batch_stations');
        Array.from(sel.options).forEach(o => o.selected = false);
        updateBatchSelectionInfo();
    }

    async function runBatch() {
        const sel      = document.getElementById('batch_stations');
        const stations = Array.from(sel.selectedOptions).map(o => o.value);

        if (stations.length === 0) {
            batchLogMsg('<span class="task-error">No stations selected. Please select at least one.</span>');
            logMsg('<span class="task-error">Batch: No stations selected.</span>');
            return;
        }

        batchAborted = false;
        batchData    = {};
        document.getElementById('batchRunBtn').disabled = true;
        document.getElementById('batch_results_container').innerHTML = '';
        document.getElementById('batch_stats_container').innerHTML   = '';

        batchLogMsg(`<span class="task-running">&#x25BA; Starting batch for ${stations.length} station(s)...</span>`);
        logMsg(`<span class="task-running">&#x25BA; Batch started: ${stations.length} station(s)</span>`);

        let successCount = 0, failCount = 0;

        for (let i = 0; i < stations.length; i++) {
            if (batchAborted) { batchLogMsg('<span class="task-error">&#9632; Batch aborted by user.</span>'); break; }

            const station = stations[i];
            const pct = Math.round(((i) / stations.length) * 100);
            setProgress(pct, `Batch ${i+1}/${stations.length}`);
            document.getElementById('batch_progress_label').innerText = `Processing ${i+1} of ${stations.length}: ${station}`;
            batchLogMsg(`<span class="task-running">&#x25BA; [${i+1}/${stations.length}] Running: ${station}</span>`);

            try {
                let payload = buildPayload(station);
                let res = await fetch('/api/detect', {
                    method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
                });
                let data = await res.json();
                if (data.error) throw new Error(data.error);

                batchData[station] = data;
                successCount++;
                batchLogMsg(`<span class="task-completed">&#x2713; Completed: ${station}</span>`);
            } catch (err) {
                failCount++;
                batchData[station] = { error: err.message };
                batchLogMsg(`<span class="task-error">&#x2717; Failed: ${station} \u2014 ${err.message}</span>`);
            }
            await new Promise(r => setTimeout(r, 80));
        }

        setProgress(100, 'Batch complete');
        document.getElementById('batch_progress_label').innerText = '';
        document.getElementById('batchRunBtn').disabled = false;

        const summary = `Batch complete: ${successCount} succeeded, ${failCount} failed.`;
        batchLogMsg(`<span class="task-completed">&#x2713; ${summary}</span>`);
        logMsg(`<span class="task-completed">&#x2713; ${summary}</span>`);

        renderBatchResults();
        renderBatchStats();
        setTimeout(() => setProgress(0, 'Ready'), 1500);
        new bootstrap.Tab(document.querySelector('[data-bs-target="#batch-results"]')).show();
    }
    
    function renderEventTable(events, containerId, type) {
        const container = document.getElementById(containerId);

        if (!events || events.length === 0) {
            container.innerHTML = '<div class="text-muted">No events detected.</div>';
            return;
        }
    
        let html = `
        <div class="table-responsive">
        <table class="table table-dark table-sm table-bordered">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Start</th>
                    <th>Peak</th>
                    <th>End</th>
                    <th>Intensity</th>
                    <th>Duration</th>
                </tr>
            </thead>
            <tbody>
        `;

        events.forEach(e => {
            html += `
            <tr>
                <td>${e.id || '-'}</td>
                <td>${e.start || e.date_start}</td>
                <td>${e.peak || '-'}</td>
                <td>${e.end || e.date_end}</td>
                <td>${e.intensity ? e.intensity.toFixed(2) : '-'}</td>
                <td>${e.duration || '-'}</td>
            </tr>`;
        });
    
        html += `</tbody></table></div>`;
        container.innerHTML = html;
    }

    function renderBatchResults() {
        const container = document.getElementById('batch_results_container');
        if (Object.keys(batchData).length === 0) return;
        let html = '';
        Object.entries(batchData).forEach(([station, data]) => {
            if (data.error) {
                html += `<div class="card mb-2 border-danger"><div class="card-header text-danger">&#x2717; ${station}</div><div class="card-body p-2"><small class="text-danger">${data.error}</small></div></div>`;
            } else {
                html += `
                    <div class="card mb-2">
                        <div class="card-header text-success">&#x2713; Station: ${station}</div>
                        <div class="card-body p-2">
                            <div class="row g-2">
                                <div class="col-md-4"><small class="text-muted d-block mb-1">Daytime</small><pre class="mb-0 p-2" style="font-size:0.72rem; min-height:60px;">${data.day_summary}</pre></div>
                                <div class="col-md-4"><small class="text-muted d-block mb-1">Nighttime</small><pre class="mb-0 p-2" style="font-size:0.72rem; min-height:60px;">${data.night_summary}</pre></div>
                                <div class="col-md-4"><small class="text-muted d-block mb-1">Compound</small><pre class="mb-0 p-2" style="font-size:0.72rem; min-height:60px;">${data.compound_summary}</pre></div>
                            </div>
                        </div>
                    </div>`;
            }
        });
        container.innerHTML = html;
    }

    function renderBatchStats() {
        const container  = document.getElementById('batch_stats_container');
        const successData = Object.entries(batchData).filter(([, d]) => !d.error);
        if (successData.length === 0) return;

        function extractVal(text, key) {
            const re = new RegExp(key + '[:\\s]+([\\d.]+)');
            const m  = text.match(re);
            return m ? parseFloat(m[1]) : '\u2014';
        }

        let html = `
            <div class="table-responsive">
            <table class="table table-dark table-bordered table-sm batch-table mb-0">
                <thead>
                    <tr>
                        <th>Station</th>
                        <th colspan="3" class="text-center text-primary">Daytime</th>
                        <th colspan="3" class="text-center text-info">Nighttime</th>
                        <th class="text-center text-warning">Compound</th>
                    </tr>
                    <tr>
                        <th></th>
                        <th>Events</th><th>Avg MaxInt</th><th>Avg Dur (d)</th>
                        <th>Events</th><th>Avg MaxInt</th><th>Avg Dur (d)</th>
                        <th>Events</th>
                    </tr>
                </thead>
                <tbody>`;

        successData.forEach(([station, data]) => {
            const day   = data.day_summary   || '';
            const night = data.night_summary || '';
            const comp  = data.compound_summary || '';
            html += `<tr>
                <td class="text-info fw-bold">${station}</td>
                <td>${extractVal(day,   'Total Events')}</td>
                <td>${extractVal(day,   'Avg Max Intensity')}</td>
                <td>${extractVal(day,   'Avg Duration')}</td>
                <td>${extractVal(night, 'Total Events')}</td>
                <td>${extractVal(night, 'Avg Max Intensity')}</td>
                <td>${extractVal(night, 'Avg Duration')}</td>
                <td>${extractVal(comp,  'Total Events')}</td>
            </tr>`;
        });
        html += `</tbody></table></div>`;
        container.innerHTML = html;
    }
</script>
</body>
</html>
"""

# ----------------- Utilities -----------------
def dates_to_ord(dates):
    return np.array([d.toordinal() for d in pd.to_datetime(dates)])

def build_event_mask(mhws, t_ord):
    mask = np.zeros_like(t_ord, dtype=bool)
    if mhws is None or mhws.get('n_events', 0) == 0:
        return mask
    for i in range(mhws['n_events']):
        try:
            start = mhws['date_start'][i].toordinal()
            end   = mhws['date_end'][i].toordinal()
            mask |= (t_ord >= start) & (t_ord <= end)
        except Exception:
            continue
    return mask

def extract_compound_events(compound_mask, dates_ord):
    if compound_mask.sum() == 0:
        return pd.DataFrame()
    idx    = np.where(compound_mask)[0]
    splits = np.where(np.diff(idx) > 1)[0]
    groups = []
    start_idx = idx[0]
    for s in splits:
        end_idx = idx[s]
        groups.append((start_idx, end_idx))
        start_idx = idx[s + 1]
    groups.append((start_idx, idx[-1]))
    rows = []
    for (i0, i1) in groups:
        start_date = date.fromordinal(int(dates_ord[i0]))
        end_date   = date.fromordinal(int(dates_ord[i1]))
        duration   = i1 - i0 + 1
        rows.append({'date_start': start_date, 'date_end': end_date, 'duration': duration})
    return pd.DataFrame(rows)

def format_summary(mhws, label):
    if not mhws or mhws.get('n_events', 0) == 0:
        return f"{label}:\nNo events detected matching parameters."
    n_events = int(mhws.get('n_events', 0))
    mean_int = np.nanmean(mhws.get('intensity_mean', [0]))
    max_int  = np.nanmean(mhws.get('intensity_max',  [0]))
    cum_int  = np.nanmean(mhws.get('intensity_cumulative', [0]))
    dur      = np.nanmean(mhws.get('duration', [0]))
    return (
        f"{label} Statistics:\n"
        f"----------------------\n"
        f"Total Events: {n_events}\n"
        f"Avg Max Intensity: {max_int:.3f}\n"
        f"Avg Mean Intensity: {mean_int:.3f}\n"
        f"Avg Cumulative Intensity: {cum_int:.3f}\n"
        f"Avg Duration: {dur:.1f} days"
    )

def run_detection_for_station(df, req, station_label=None):
    col_date    = req.get('col_date')
    col_day     = req.get('col_day')
    col_night   = req.get('col_night')
    col_station = req.get('col_station')
    target_st   = req.get('target_station')

    work_df = df.copy()
    if target_st and col_station and col_station in work_df.columns:
        work_df = work_df[work_df[col_station].astype(str).str.strip() == str(target_st).strip()]
        if work_df.empty:
            raise ValueError(f'No data found for station "{target_st}".')

    work_df[col_date] = pd.to_datetime(work_df[col_date])
    work_df = work_df.sort_values(by=col_date).reset_index(drop=True)

    t_ord    = dates_to_ord(work_df[col_date])
    temp_day = pd.to_numeric(work_df[col_day], errors='coerce').to_numpy()

    kwargs = {
        'climatologyPeriod': [req.get('clim_start'), req.get('clim_end')],
        'pctile':            req.get('pctile'),
        'minDuration':       req.get('min_dur'),
        'joinAcrossGaps':    req.get('join_gaps')
    }
    if kwargs['joinAcrossGaps']:
        kwargs['maxGap'] = req.get('max_gap')

    mhws_day, clim_day = mhw.detect(t_ord, temp_day, **kwargs)

    block_day = pd.DataFrame()
    try:
        block_day = pd.DataFrame.from_dict(
            mhw.blockAverage(t_ord, mhws_day, clim=clim_day, temp=temp_day))
    except Exception:
        pass

    night_avail = col_night and col_night in work_df.columns
    if night_avail:
        temp_night = pd.to_numeric(work_df[col_night], errors='coerce').to_numpy()
        mhws_night, clim_night = mhw.detect(t_ord, temp_night, **kwargs)
        block_night = pd.DataFrame()
        try:
            block_night = pd.DataFrame.from_dict(
                mhw.blockAverage(t_ord, mhws_night, clim=clim_night, temp=temp_night))
        except Exception:
            pass
    else:
        mhws_night  = {'n_events': 0}
        clim_night  = None
        block_night = pd.DataFrame()

    mask_day    = build_event_mask(mhws_day, t_ord)
    mask_night  = build_event_mask(mhws_night, t_ord) if night_avail else np.zeros_like(mask_day)
    compound_mask = mask_day & mask_night
    compound_df   = extract_compound_events(compound_mask, t_ord)

    def build_event_table(mhws):
        if not mhws or mhws.get('n_events', 0) == 0:
            return []
    
        events = []
        for i in range(mhws['n_events']):
            events.append({
                'id': i + 1,
                'start': str(mhws['date_start'][i]),
                'peak': str(mhws['date_peak'][i]),
                'end': str(mhws['date_end'][i]),
                'intensity': float(mhws['intensity_max'][i]),
                'duration': int(mhws['duration'][i])
            })
        return events

    return {
        'work_df':          work_df,
        't_ord':            t_ord,
        'mhws_day':         mhws_day,
        'clim_day':         clim_day,
        'mhws_night':       mhws_night,
        'clim_night':       clim_night,
        'block_day':        block_day,
        'block_night':      block_night,
        'compound_df':      compound_df,
        'day_summary':      format_summary(mhws_day,   "Daytime MHWs"),
        'night_summary':    format_summary(mhws_night, "Nighttime MHWs"),
        'compound_summary': f"Compound MHWs (Concurrent):\n----------------------\nTotal Events: {len(compound_df)}",
        'day_events':       build_event_table(mhws_day),
        'night_events':     build_event_table(mhws_night),
        'compound_events':  compound_df.to_dict(orient='records')
    }

# ----------------- Routes -----------------

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    try:
        df = pd.read_csv(file)
        APP_STATE['df'] = df
        APP_STATE['filtered_df'] = None
        return jsonify({'rows': len(df), 'columns': list(df.columns)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stations', methods=['GET'])
def get_stations():
    df = APP_STATE.get('df')
    if df is None:
        return jsonify({'error': 'No data loaded.'}), 400
    col = request.args.get('col', '')
    if not col or col not in df.columns:
        return jsonify({'error': f'Column "{col}" not found.'}), 400
    stations = sorted(df[col].dropna().astype(str).str.strip().unique().tolist())
    return jsonify({'stations': stations, 'count': len(stations)})

@app.route('/api/detect', methods=['POST'])
def detect():
    global_df = APP_STATE.get('df')
    if global_df is None:
        return jsonify({'error': 'No data loaded. Please upload a CSV first.'}), 400

    req      = request.json
    col_date = req.get('col_date')
    col_day  = req.get('col_day')

    if not col_date or not col_day:
        return jsonify({'error': 'Date and Daytime temperature columns must be selected.'}), 400
    if col_date not in global_df.columns or col_day not in global_df.columns:
        return jsonify({'error': 'Missing selected date or daytime temp column in data.'}), 400

    try:
        result = run_detection_for_station(global_df, req)

        APP_STATE['filtered_df'] = result['work_df']
        APP_STATE['col_date']    = req.get('col_date')
        APP_STATE['col_day']     = req.get('col_day')
        APP_STATE['col_night']   = req.get('col_night')
        APP_STATE['t_ord']       = result['t_ord']
        APP_STATE['mhws_day']    = result['mhws_day']
        APP_STATE['clim_day']    = result['clim_day']
        APP_STATE['mhws_night']  = result['mhws_night']
        APP_STATE['clim_night']  = result['clim_night']
        APP_STATE['block_day']   = result['block_day']
        APP_STATE['block_night'] = result['block_night']
        APP_STATE['compound_df'] = result['compound_df']

        # Compute year range for frontend defaults
        dates_series = pd.to_datetime(result['work_df'][col_date])
        year_max = int(dates_series.dt.year.max())
        year_min = int(dates_series.dt.year.min())

        return jsonify({
            'day_summary':       result['day_summary'],
            'night_summary':     result['night_summary'],
            'compound_summary':  result['compound_summary'],

            # 🔽 ADD THESE NEW LINES HERE
            'day_events':        result['day_events'],
            'night_events':      result['night_events'],
            'compound_events':   result['compound_events'],

            # existing fields
            'year_max':          year_max,
            'year_min':          year_min
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/map_data', methods=['POST'])
def map_data():
    df = APP_STATE.get('df')
    if df is None:
        return jsonify({'error': 'No data loaded.'}), 400

    req         = request.json
    col_lat     = req.get('col_lat')
    col_lon     = req.get('col_lon')
    col_station = req.get('col_station', '')

    if not col_lat or col_lat not in df.columns:
        return jsonify({'error': f'Latitude column "{col_lat}" not found.'}), 400
    if not col_lon or col_lon not in df.columns:
        return jsonify({'error': f'Longitude column "{col_lon}" not found.'}), 400

    try:
        cols = [col_lat, col_lon]
        if col_station and col_station in df.columns:
            cols.append(col_station)

        sub = df[cols].dropna(subset=[col_lat, col_lon]).copy()
        sub[col_lat] = pd.to_numeric(sub[col_lat], errors='coerce')
        sub[col_lon] = pd.to_numeric(sub[col_lon], errors='coerce')
        sub = sub.dropna(subset=[col_lat, col_lon])

        if col_station and col_station in df.columns:
            sub = sub.drop_duplicates(subset=[col_station])
        else:
            sub = sub.drop_duplicates(subset=[col_lat, col_lon])

        stations = []
        for _, row in sub.iterrows():
            entry = {'lat': float(row[col_lat]), 'lon': float(row[col_lon])}
            if col_station and col_station in row:
                entry['name'] = str(row[col_station])
            stations.append(entry)

        return jsonify({'stations': stations, 'count': len(stations)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ----------------------------------------------------------------
#  /api/plot_viz  –  All interactive plot types via Plotly
# ----------------------------------------------------------------
@app.route('/api/plot_viz', methods=['POST'])
def plot_viz():
    req        = request.json
    event_type = req.get('event', 'day')
    plot_type  = req.get('type',  'timeseries')
    ys         = req.get('ys', 1981)
    ye         = req.get('ye', 2020)

    df = APP_STATE.get('filtered_df')
    if df is None or df.empty:
        return jsonify({'error': 'Run detection first'}), 400

    col_date = APP_STATE.get('col_date')
    col_temp = APP_STATE.get('col_day') if event_type == 'day' else APP_STATE.get('col_night')

    if not col_date or col_date not in df.columns:
        return jsonify({'error': 'Date column not mapped'}), 400
    if not col_temp or col_temp not in df.columns:
        return jsonify({'error': f'Temperature column not mapped for {event_type}'}), 400

    dates  = pd.to_datetime(df[col_date])
    temp   = pd.to_numeric(df[col_temp], errors='coerce')
    clim   = APP_STATE.get(f'clim_{event_type}')
    mhws   = APP_STATE.get(f'mhws_{event_type}')
    t_ord  = APP_STATE.get('t_ord')
    label  = 'Daytime' if event_type == 'day' else 'Nighttime'

    _DARK = dict(template='plotly_dark', paper_bgcolor='#1a1d20', plot_bgcolor='#151819')
    plots  = []

    # ---- Timeseries ----
    if plot_type == 'timeseries':
        mask_ts = (dates.dt.year >= ys) & (dates.dt.year <= ye)
        
        # Rigorously force native Python lists to avoid ANY Pandas index serialization bugs (e.g. X-axis 0 to 25k)
        plot_dates_list = dates[mask_ts].dt.strftime('%Y-%m-%d').tolist()
        plot_temp_list = temp[mask_ts].tolist()
        
        # Safely align clim arrays
        thresh_series = pd.Series(clim['thresh'], index=dates.index) if clim else pd.Series([None]*len(dates), index=dates.index)
        seas_series = pd.Series(clim['seas'], index=dates.index) if clim else pd.Series([None]*len(dates), index=dates.index)
        
        plot_thresh_list = thresh_series[mask_ts].tolist()
        plot_seas_list = seas_series[mask_ts].tolist()

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=plot_dates_list, y=plot_seas_list, mode='lines', name='Climatology',
            line=dict(color='#66bb6a', dash='dot', width=1.0),
            hovertemplate='Clim: %{y:.2f}°C<extra></extra>'
        ))
        fig.add_trace(go.Scatter(
            x=plot_dates_list, y=plot_thresh_list, mode='lines', name='Threshold',
            line=dict(color='#ffa726', dash='dash', width=1.2),
            hovertemplate='Thresh: %{y:.2f}°C<extra></extra>'
        ))
        fig.add_trace(go.Scatter(
            x=plot_dates_list, y=plot_temp_list, mode='lines', name='Temperature',
            line=dict(color='#4fc3f7', width=1.3),
            hovertemplate='%{x}<br>Temp: %{y:.2f}°C<extra></extra>'
        ))

        if mhws and mhws.get('n_events', 0) > 0:
            for i in range(mhws['n_events']):
                idx_start = mhws['index_start'][i]
                idx_end   = mhws['index_end'][i]
                
                # index_start and end map to the direct array position of the sequence
                seg_idx = np.arange(idx_start, idx_end + 1)
                
                # Double check boundaries to respect ys & ye selection
                seg_dates = dates.iloc[seg_idx]
                valid_mask = (seg_dates.dt.year >= ys) & (seg_dates.dt.year <= ye)
                
                if not valid_mask.any(): 
                    continue
                
                # Extract clean lists again! No pandas series leakage.
                seg_dates_valid = seg_dates[valid_mask].dt.strftime('%Y-%m-%d').tolist()
                seg_temp_valid = temp.iloc[seg_idx][valid_mask].tolist()
                seg_thresh_valid = thresh_series.iloc[seg_idx][valid_mask].tolist()

                fig.add_trace(go.Scatter(
                    x=seg_dates_valid, y=seg_thresh_valid,
                    mode='lines', line=dict(width=0),
                    showlegend=False, hoverinfo='skip'
                ))
                fig.add_trace(go.Scatter(
                    x=seg_dates_valid, y=seg_temp_valid,
                    mode='lines', line=dict(color='#ef5350', width=1.5),
                    fill='tonexty', fillcolor='rgba(239,83,80,0.5)',
                    name='Heatwave',
                    showlegend=(i == 0),
                    hovertemplate='Heatwave Day<br>%{x}<br>Temp: %{y:.2f}°C<extra></extra>'
                ))

        fig.update_layout(
            **_DARK,
            title=dict(text=f'<b>Temperature Timeseries</b> — {label} ({ys}–{ye})', font=dict(size=15)),
            xaxis_title='Date',
            yaxis_title='Temperature (°C)',
            hovermode='x unified',
            legend=dict(orientation='h', y=1.04, x=0, font=dict(size=11)),
            height=430,
            margin=dict(l=60, r=30, t=55, b=50)
        )
        plots.append(fig.to_json())

        hw_mask = build_event_mask(mhws, t_ord)
        hw_mask_ts = hw_mask[mask_ts]
        total_hw = int(hw_mask_ts.sum())
        normal   = max(0, int(len(plot_dates_list) - total_hw))
        fig_pie  = go.Figure(data=[go.Pie(
            labels=['Heatwave Days', 'Normal Days'],
            values=[total_hw, normal],
            hole=0.56,
            marker=dict(colors=['#ef5350', '#42a5f5']),
            textinfo='label+percent',
            hovertemplate='%{label}: %{value:,} days<extra></extra>',
            pull=[0.04, 0]
        )])
        fig_pie.update_layout(
            **_DARK,
            title=dict(text=f'<b>Heatwave Proportion</b> — {label} ({ys}–{ye})', font=dict(size=15)),
            height=360,
            margin=dict(l=20, r=20, t=55, b=20),
            legend=dict(font=dict(size=12))
        )
        plots.append(fig_pie.to_json())

    # ---- Block averages ----
    elif plot_type == 'block':
        block_df = APP_STATE.get(f'block_{event_type}')
        if block_df is None or block_df.empty:
            fig = go.Figure()
            fig.update_layout(**_DARK, title=dict(text="No Block Data Available", font=dict(size=15)))
            plots.append(fig.to_json())
        else:
            mask = (block_df['years_centre'] >= ys) & (block_df['years_centre'] <= ye)
            dp = block_df[mask].copy()
            
            # Explicit tolist() removes index serialization bug causing "0 to 6" axis bounds
            x_years = dp['years_centre'].tolist()
            y_count = dp['count'].tolist()
            
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=x_years, y=y_count,
                mode='lines+markers', name='Events / Year',
                line=dict(color='#42a5f5', width=2),
                marker=dict(size=7, color='#42a5f5', line=dict(color='white', width=1)),
                hovertemplate='Year: %{x}<br>Events: %{y}<extra></extra>'
            ))

            if 'duration_mean' in dp.columns:
                y_dur = dp['duration_mean'].tolist()
                fig.add_trace(go.Scatter(
                    x=x_years, y=y_dur,
                    mode='lines+markers', name='Avg Duration (days)',
                    yaxis='y2',
                    line=dict(color='#ffa726', width=2, dash='dash'),
                    marker=dict(size=7, symbol='diamond'),
                    hovertemplate='Avg Duration: %{y:.1f} days<extra></extra>'
                ))

            fig.update_layout(
                **_DARK,
                title=dict(text=f'<b>Block Averages</b> — {label} ({ys}–{ye})', font=dict(size=15)),
                xaxis_title='Year',
                yaxis_title='Number of Events',
                yaxis2=dict(title='Avg Duration (days)', overlaying='y', side='right', showgrid=False),
                hovermode='x unified',
                legend=dict(orientation='h', y=1.04, x=0),
                height=430,
                margin=dict(l=60, r=70, t=55, b=50)
            )
            plots.append(fig.to_json())

    # ---- Category days ----
    elif plot_type == 'category':
        diff = temp - clim['seas']
        thresh_diff = clim['thresh'] - clim['seas']
        
        with np.errstate(divide='ignore', invalid='ignore'):
            ratio = np.where(thresh_diff > 0, diff / thresh_diff, 0)
            
        hw_mask = build_event_mask(mhws, t_ord)
        
        cat_mod    = (hw_mask) & (ratio >= 1) & (ratio < 2)
        cat_strong = (hw_mask) & (ratio >= 2) & (ratio < 3)
        cat_severe = (hw_mask) & (ratio >= 3) & (ratio < 4)
        cat_ext    = (hw_mask) & (ratio >= 4)
        cat_dip    = (hw_mask) & (ratio < 1) 
        cat_mod    = cat_mod | cat_dip

        df_stats = pd.DataFrame({
            'year': dates.dt.year,
            'moderate': cat_mod,
            'strong': cat_strong,
            'severe': cat_severe,
            'extreme': cat_ext
        }).groupby('year').sum().reset_index()

        mask = (df_stats['year'] >= ys) & (df_stats['year'] <= ye)
        dp = df_stats[mask]

        # Use Python lists strictly to prevent plotly dumping `year` index numbers (0, 1, 2, 3...)
        x_years = dp['year'].tolist()

        fig = go.Figure()
        fig.add_trace(go.Bar(x=x_years, y=dp['moderate'].tolist(), name='Moderate', marker_color='#ff9800'))
        fig.add_trace(go.Bar(x=x_years, y=dp['strong'].tolist(), name='Strong', marker_color='#f44336'))
        fig.add_trace(go.Bar(x=x_years, y=dp['severe'].tolist(), name='Severe', marker_color='#9c27b0'))
        fig.add_trace(go.Bar(x=x_years, y=dp['extreme'].tolist(), name='Extreme', marker_color='#37474f'))

        fig.update_layout(
            **_DARK,
            barmode='stack',
            title=dict(text=f'<b>Heatwave Category Days</b> — {label} ({ys}–{ye})', font=dict(size=15)),
            xaxis_title='Year',
            yaxis_title='Number of Days',
            legend=dict(orientation='h', y=1.04, x=0),
            height=430,
            margin=dict(l=60, r=30, t=55, b=50)
        )
        plots.append(fig.to_json())

    return jsonify({'plots': plots})


# ----------------------------------------------------------------
#  /api/calendar_plot  –  Proper monthly calendar heatmap
# ----------------------------------------------------------------
@app.route('/api/calendar_plot', methods=['POST'])
def generate_calendar_plot():
    req       = request.json
    year      = req.get('year')
    temp_type = req.get('tempType', 'day')

    df = APP_STATE.get('filtered_df')
    if df is None or df.empty:
        return jsonify({'error': 'Run detection first'}), 400

    col_date = APP_STATE.get('col_date')
    col_temp = APP_STATE.get('col_day') if temp_type == 'day' else APP_STATE.get('col_night')

    if not col_date or col_date not in df.columns:
        return jsonify({'error': 'Date column mapping missing'}), 400
    if not col_temp or col_temp not in df.columns:
        return jsonify({'error': f'Temperature column mapping missing for {temp_type}'}), 400

    df = df.copy()
    df[col_date] = pd.to_datetime(df[col_date])

    year_max = int(df[col_date].dt.year.max())
    if not year:
        year = year_max
    else:
        year = int(year)

    df_year = df[df[col_date].dt.year == year].copy()
    if df_year.empty:
        return jsonify({'error': f'No data for year {year}'}), 400

    df_year['_date'] = df_year[col_date].dt.normalize()
    df_year['_temp'] = pd.to_numeric(df_year[col_temp], errors='coerce')
    daily = df_year.groupby('_date')['_temp'].mean().reset_index()
    daily.columns = ['date', 'temp']

    year_start   = pd.Timestamp(f"{year}-01-01")
    year_end     = pd.Timestamp(f"{year}-12-31")
    cal_df       = pd.DataFrame({'date': pd.date_range(year_start, year_end, freq='D')})
    cal_df       = cal_df.merge(daily, on='date', how='left')

    jan1_wd         = year_start.weekday()   
    cal_df['week_col'] = (cal_df['date'].dt.dayofyear - 1 + jan1_wd) // 7
    cal_df['weekday']  = cal_df['date'].dt.weekday        
    n_weeks            = int(cal_df['week_col'].max()) + 1

    z           = [[None]*n_weeks for _ in range(7)]
    hover_texts = [['' for _ in range(n_weeks)] for _ in range(7)]

    for _, row in cal_df.iterrows():
        r = int(row['weekday'])
        c = int(row['week_col'])
        val = row['temp']
        z[r][c] = float(val) if pd.notna(val) else None
        
        t_str = f"{val:.1f}°C" if pd.notna(val) else 'No data'
        hover_texts[r][c] = (
            f"<b>{row['date'].strftime('%A, %d %B %Y')}</b><br>"
            f"Temperature: <b>{t_str}</b>"
        )

    hw_dates = set()
    mhws     = APP_STATE.get(f'mhws_{temp_type}')
    if mhws and mhws.get('n_events', 0) > 0:
        for i in range(mhws['n_events']):
            try:
                s = mhws['date_start'][i]
                e = mhws['date_end'][i]
                
                if hasattr(s, 'date'):
                    s = s.date()
                else:
                    s = pd.Timestamp(s).date()
                if hasattr(e, 'date'):
                    e = e.date()
                else:
                    e = pd.Timestamp(e).date()

                cur = s
                while cur <= e:
                    if cur.year == year:
                        hw_dates.add(cur)
                    cur += datetime.timedelta(days=1)
            except Exception:
                continue

    fig = go.Figure()

    day_labels   = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    months_abbr  = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    SEP_COLOR    = 'rgba(190,190,190,0.45)'
    SEP_W        = 1.5

    fig.add_trace(go.Heatmap(
        x=list(range(n_weeks)),
        y=list(range(7)),
        z=z,
        colorscale='hot_r',
        showscale=True,
        hovertext=hover_texts,
        hoverinfo='text',
        xgap=3,
        ygap=3,
        colorbar=dict(
            title=dict(text='°C', side='right', font=dict(color='#cccccc', size=12)),
            tickfont=dict(color='#cccccc'),
            thickness=14,
            len=0.85,
            x=1.01
        )
    ))

    for m in range(1, 13):
        first_day = pd.Timestamp(f"{year}-{m:02d}-01")
        w  = (first_day.dayofyear - 1 + jan1_wd) // 7   
        wd = first_day.weekday()                        

        fig.add_annotation(
            x=float(w) + (0.0 if wd == 0 else 0.0),
            y=-0.65,
            text=f"<b>{months_abbr[m-1]}</b>",
            showarrow=False,
            font=dict(color='#bbbbbb', size=10),
            xanchor='left',
            xref='x', yref='y'
        )

        if m == 1:
            continue

        if wd == 0:
            fig.add_shape(type='line',
                x0=w - 0.5, x1=w - 0.5,
                y0=-0.5, y1=6.5,
                line=dict(color=SEP_COLOR, width=SEP_W))
        else:
            fig.add_shape(type='line',
                x0=w - 0.5, x1=w - 0.5,
                y0=-0.5, y1=float(wd) - 0.5,
                line=dict(color=SEP_COLOR, width=SEP_W))
            fig.add_shape(type='line',
                x0=w - 0.5, x1=w + 0.5,
                y0=float(wd) - 0.5, y1=float(wd) - 0.5,
                line=dict(color=SEP_COLOR, width=SEP_W))
            fig.add_shape(type='line',
                x0=w + 0.5, x1=w + 0.5,
                y0=float(wd) - 0.5, y1=6.5,
                line=dict(color=SEP_COLOR, width=SEP_W))

    for _, row in cal_df.iterrows():
        d = row['date'].date()
        if d in hw_dates:
            c = int(row['week_col'])
            r = int(row['weekday'])
            fig.add_shape(
                type='rect',
                x0=c - 0.44, x1=c + 0.44,
                y0=r - 0.44, y1=r + 0.44,
                line=dict(color='rgba(160,32,240,1.0)', width=3.5),
                fillcolor='rgba(0,0,0,0)',
                layer='above'
            )

    type_label = 'Daytime (Tx)' if temp_type == 'day' else 'Nighttime (Tn)'
    hw_count   = len(hw_dates)
    hw_note    = (f"  ·  <span style='color:#c040ff;font-size:13px;'>▪</span> "
                  f"<span style='font-size:13px;color:#c040ff;'>{hw_count} heatwave day(s)</span>"
                  if hw_count > 0 else "")

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#1a1d20',
        plot_bgcolor='#151819',
        title=dict(
            text=f"<b>{year} Heatwave Calendar</b>  ·  {type_label}{hw_note}",
            font=dict(size=15, color='#e0e0e0'),
            x=0.0, xanchor='left'
        ),
        height=320,
        margin=dict(l=55, r=65, t=52, b=20),
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[-0.5, n_weeks - 0.5], fixedrange=True
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=list(range(7)),
            ticktext=day_labels,
            autorange='reversed',
            range=[-1.1, 6.5],
            showgrid=False, zeroline=False,
            fixedrange=True,
            tickfont=dict(color='#aaaaaa', size=10)
        )
    )

    return jsonify({
        'plot':     fig.to_json(),
        'year':     year,
        'hw_count': hw_count
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)