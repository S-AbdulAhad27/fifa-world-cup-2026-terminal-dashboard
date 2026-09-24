# FIFA WORLD CUP 2026 TERMINAL DASHBOARD

####  CS50P Final Project Submission
####  Video URL: [https://youtu.be/3hw0L69IV0o]

---

## Project Overview
This project is an interactive, terminal based dashboard designed to track real time historical analytical data for The FIFA World Cup 2026.

This Final Project Built entirely in python, The application fetches live data from dynamic servers and gives cleanly formated user experience ASCII tables with Python tabulate library.

The Software is created with high resilience, featuring an automated Json-based local cache system, If live servers go offline or a network error occurs, the application instantly drops back to local files to guarantee zero-downtime performance.

 ---

## User Interface and Dashboard Options
When the application launched, the program displays a main menu offering five central navigation paths:

1. **`1` Live Match Scores:** Provide Real-updates for In Play matches with current scores and updated feeds.
2. **`2` Group Standings:**  Points tables of sorted Group matrices teams by points, goal differences, an games played.
3. **`3.` Knockout Stages Screen:** Tounament brackets completed and upcoming matches logs.
4. **`4.` Player Statistics Leaderboard:** Top-5 tounament Leaders matrics for both players eliye attakers (goals, assits) and goalkeepers (save, clean sheets).
5. **`5.` Exit Dasboard:** Securely Exits the dashboard instance with an exit message and clear memory.

## Architecture & Core Components
 The project is modulary structured across multiple Python modules (comprising 16 to 18 operational functions). The execution pipeline relies on two primary script drivers:

 ### 🖥️ `project.py`
 This houses the absolute core engine of the interface:

* **` main(): `** Server as abolute engine core of the interface it clears terminal data displays the start screen and called build_terminal_dashboard() function, runs a continues loop to fetch the user input it also handles exceptions raised during execution.

* **`build_terminal_dashboard()`**: This function determines the user input/screen selections. routes user inputs to relevant sub-processors, fetches the needed datasets, formats them, and renders tables cleanly on screen.

### 🌐 `api.py`
This file contains all internet networking, data storage routines, and resilience mechanisms:
* **`get_server_data(url)`**: Fetches data from  remote server. If the server returns a successful `200 OK` HTTP status code, it saving it to storage subsystem. If the server is unreachable, it automatically calls `load_file_data()`.
* **`save_server_data(data, url)`**: Process the incoming API data, identifies content context via the endpoint URL, and updates corresponding  JSON maps (`players_stats.json`, `matches.json`, `standings.json`, etc.).
* **`load_file_data(user_choice_url)`**: Reads saved data from a local file when the internet or API is not working. This allows the program to keep working without an internet connection.

---

## 📦 Key Libraries & Technologies
* **`tabulate`**: Used to create nice tables in the terminal. It takes data and displays it in an easy-to-read table format.
* **`requests`**: Used to connect to the internet and get World Cup data from an external server/API.
* **`json`**: Used to read and write JSON files. It helps the program save data locally and load it again later.
* **`logging`**: Used to record errors and important events. If something goes wrong, such as a network error or timeout, the program records the error and also shows a simple message to the user. The errors are saved in app.log file for later checking.
---

## ⚙️ Installation & Getting Started

### Prerequisites
* Python 3.8 or higher installed on your system.

### Step 1: Clone the Project
```bash
  git clone https://github.com
cd S-AbdulAhad27
```

### Step 2: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Launch the Application
```bash
python project.py
```
---

## 🧪 Testing
The different functions in the project are tested using pytest. Testing helps us check that the functions are working correctly.
To run the tests, use:
```bash
pytest test_project.py
```

