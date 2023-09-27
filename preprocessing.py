import pandas as pd
import gzip

# Specify the file paths
activity_file = 'data_original/vaud_activities.csv.gz'
population_file = 'data_original/vaud_population.csv.gz'
trip_file = 'data_original/vaud_trips.csv.gz'

# Read the gzipped CSV files
def read_gzipped_csv(file_path):
    with gzip.open(file_path, 'rt') as file:
        df = pd.read_csv(file)
    return df

# Read the dataframes
activity_df = read_gzipped_csv(activity_file)
population_df = read_gzipped_csv(population_file)
trip_df = read_gzipped_csv(trip_file)

print("File opened and read \n")

# filter the population


# filter the facilities


# filter relevant schedules (not necessary?)



