# Agile_Web_Development


**Epidemic Monitoring – A Private Data Analytics & Sharing Platform**

**Overview:**
Epidemic Monitoring is a secure, web-based data analytics tool that empowers individuals, health professionals, and local authorities to upload datasets related to infectious disease outbreaks, visualize epidemic trends geographically and statistically, and selectively share critical insights with others.

This system transforms raw outbreak data (e.g. infection rates, hotspots) into meaningful insights, helping communities identify, understand, and respond to health crises while maintaining privacy and control over sensitive data.


**Purpose of the Application**
The application is designed to:

1. Enable uploading of outbreak-related data (e.g. infections per suburb or GPS location).

2. Provide automated visualization of trends, clusters, and severity levels.

3. Allow selective sharing of data insights with trusted users or authorities.

4. Respect privacy and control, ensuring that data remains secure and access is granted explicitly.


**Key Features**:
1. Introductory View
Overview of the Epidemic Monitoring tool.

Sign-up and login functionality.

Motivation for data sharing in outbreak control.

2. Upload Data View
Users upload CSV or JSON files (e.g. date, suburb, cases).

Optionally fill out a dynamic manual entry form.

Real-time validation and data preview before submission.

3. Visualize Data View
Line and bar graphs for infection rates over time.

Heatmaps and markers on geographic maps using Leaflet.js.

Filters for region, time period, and severity.

4. Share Data View
View previously uploaded datasets and their analyses.

Select datasets and share with specific users.

Modify or revoke sharing permissions anytime.


**Design Philosophy:**
Engaging:  	Uses a clean UI with Tailwind CSS, real-time feedback on uploads, and rich charts.

Effective: 	Delivers instant visualizations, daily/weekly trend analysis, and heatmaps.

Intuitive:	Minimal-click workflows, form validation, and AJAX-driven interactions.


**Technologies Used:**
Frontend         HTML, CSS, jQuery
Backend          Flask, SQLite
Interactivity    AJAX
Visualization    charts.js


**Project Structure (Example):**
epidemic_monitoring
|
|---app.py
|---assets/
|---models.py
|---README.md





**Planned Milestones:
**
Task                              |     Week#
--------------------------------------------------------------------------
Repository + App Setup            |    1
                                  |
User Authentication               |    2
                                  |
Upload View + File Validation     |    2-4
                                  |
Data Visualization Engine         |    3
                                  |
Data Sharing Logic + Permissions  |    3-4
                                  |
Final UI + Bug Fixes              |    5
                                  | 
Documentation + Testing           |    6




**Example CSV file Structure:
**
 Column Name	 |     Type	       |            Description
--------------------------------------------------------------------------
date	         | YYYY-MM-DD	   |   Date of record (e.g., 2025-04-08)
suburb	       | string	       |   Name of the suburb or region
postcode	     | string	       |   4-digit postcode (e.g., 6000)
cases	         | integer       |   Number of new confirmed cases
deaths	       | integer	     |   Number of deaths on that day (optional)
lat	           | float	       |   Latitude of the location (optional)
long	         | float	       |   Longitude of the location






    date   | suburb   | postcode  | cases | deaths | lat      | long
--------------------------------------------------------------------------
2025-04-01 |Perth     | 6000      |  12   |  0     | -31.9505 | 115.8605
2025-04-01 |Fremantle | 6160      |   8   |  1     |-32.0569  | 115.7496
2025-04-02 |Perth     | 6000      |  15   |  0     |-31.9505  | 115.8605
