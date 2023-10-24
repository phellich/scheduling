## Summary of Each File

### EDA.ipynb
This notebook stands for **Exploratory Data Analysis**:
- Represents the initial exploration steps over the provided CSV files.
- Might not be very organized and may lack comprehensive comments.
- Designed for first-time explorations.

### preprocessing.ipynb
Handles data preprocessing:
- Processes data to generate two output files:
  1. Parameters for each facility.
  2. Coordinates for individual homes and their preferences.
- Files can be generated with arbitrary sizes to test the program's solution quality or computational efficiency.
- Might lack extensive comments but is straightforward. Uncommentable print statements can aid understanding.
- Requires **Python 3.10** or newer.

### main.py
Performs the following tasks:
- Reads preprocessed CSV files.
- Initializes C variables in Python using `ctypes`.
- Invokes `main()` from the C program for each individual.
- Extracts:
  - Number of DSSR iterations.
  - Execution time.
  - Daily schedule.
- Saves data in JSON format.

### scheduling Folder
Contains incremental versions of Fabian's code:
- **v0:** Original, unmodified code enriched with comments.
- **v1:** Minor modifications and some code cleaning.
- **v2:** Major changes:
  - Moved initialization of activities, utility matrices, etc., to `main.py`.
  - Established interface between Python and C.
  - Further code cleaning and removal of `printf` statements.
- **v3:** Significant modifications including changes to utility model, preference model, and the group checking loop.
