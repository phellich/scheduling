# See [associated paper of the project](./Semester_project.pdf)

## What is the structure of the github ? 

### Data folder
- **1_Original:** MATSim data for canton of Vaud
- **2_Original:** Pre processed data after running the eponym notebook : 
    - population : one line by individual, his/her home work coordinates and his/her preferences
    - activities : one line by facility, with their coordinates, type (shop, leisure or education) and some time constraints for their execution
- **3_Generated:** One JSON by simulated scenario. You can take a look to see their structure
- **4_PostProcessed:** JSON files transformed in CSV to be used in the epidemiologic model of Cloe (more explanation in the description of `Post_processing.py`)

### Pre-processing.ipynb
Handles data preprocessing:
- Processes data to generate two output files:
  1. Parameters for each facility.
  2. Coordinates for individual homes and their preferences.
- Files can be generated with arbitrary sizes to test the program's solution quality or computational efficiency.
- Might lack extensive comments but is straightforward. Uncommentable print statements can aid understanding.
- Requires **Python 3.10** or newer.

### Main.py
Performs the following tasks:
- Reads preprocessed CSV files.
- Initializes C variables in Python using `ctypes`.
- Invokes `main()` from the C program for each individual.
- Extracts:
  - Number of DSSR iterations.
  - Execution time.
  - Daily schedule.
  - ...
- Saves data in JSON format.

### Scheduling algorythm Folder
Contains incremental versions of Fabian's code:
- **v0:** Original, unmodified code enriched with comments.
- **v1:** Minor modifications and some code cleaning.
- **v2:** Major changes:
  - Moved initialization of activities, utility matrices, etc., to `Main.py`.
  - Established interface between Python and C.
  - Further code cleaning and removal of `printf` statements.
- **v3:** Significant modifications including changes to utility model, preference model, and the group checking loop.
- **v4:** Fixing major bugs : operationnal algorythm !
- **v5:** Scaling up the code + add randomness to scheduling preferences + workplace already attributed
- **v6:** Modify Label structure to trace deviation from preferences (I know github is done to avoid that haha, I just wanted to copy paste some stuff faster)

### Post_processing.py
- Transform all the generated json into usefull csv files that will serve as input for Cloe's epidemiologic model 
- The csv created are very similar to original Matsim data, but without the trip.csv file
- **population_{city}:** contains the attributes of all people living in the place where the simulation took place
- **activities_{scenario}:** contains the schedules of all individuals in the case of the precised scenario. A scenario of an individual is represented by few lines, where each line is a new facility accomplished

### Results_exploration.ipynb
Handles data preprocessing:
- Processes data to generate two output files:
  1. Parameters for each facility.
  2. Coordinates for individual homes and their preferences.
- Files can be generated with arbitrary sizes to test the program's solution quality or computational efficiency.
- Might lack extensive comments but is straightforward. Uncommentable print statements can aid understanding.
- Requires **Python 3.10** or newer.
- Compare statistics netween different scenarios
- Check the adaptation of an individual to the scenarios

### Old material Folder
- Represents the initial exploration steps over the provided CSV files.
- Might not be very organized and may lack comprehensive comments.
- EDA designed for first-time explorations.
- Deprecated Main that was working with the arbritrary data from Fabian, and some others (I know github is done to avoid that haha, I just wanted to copy paste some stuff faster)

### Image Folder
- Saved screens of dataframes 
- Saved plots about the original dataset distribution and the predicted schedules

## How to use that program ?

### Installation
- Fork the github and open it in a code editor

### Pre-processing
- Precise the global parameters : 
  - LOCAL : which city in Vaud you want to study
  - FRACT_ACT : the proportion of facilities where people would be able to go
  - FRACT_POP : the proportion of the population of the city you want to study
  - TIME_INTERVAL : which granularity of schedules do you want ? Either 5m or 10m. 
- Run all the notebook

### Run Main.py 
- Adjust the parameters of the `Main.py` : 
  - `TODO` : explanation of each
- Run `Main.py` from your terminal
