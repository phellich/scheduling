## Summary of Each File

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

### Post-processing.ipynb
Handles data preprocessing:
- Processes data to generate two output files:
  1. Parameters for each facility.
  2. Coordinates for individual homes and their preferences.
- Files can be generated with arbitrary sizes to test the program's solution quality or computational efficiency.
- Might lack extensive comments but is straightforward. Uncommentable print statements can aid understanding.
- Requires **Python 3.10** or newer.

### Old material Folder
- Represents the initial exploration steps over the provided CSV files.
- Might not be very organized and may lack comprehensive comments.
- EDA designed for first-time explorations.
- Deprecated Main that was working with the arbritrary data from Fabian

### Image Folder
- Saved screens of dataframes 
- Saved plots about the original dataset distribution and the predicted schedules