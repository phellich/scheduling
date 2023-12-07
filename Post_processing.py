import pandas as pd
from pandas import json_normalize
import gzip
from datetime import time

TIME_INTERVAL=None
######################################################################################
## Clean schedules ###################################################################

def json_to_flat_dataframe(json_path):
    '''
    Normalize the 'daily_schedule' data to create a flat table
    Concatenate all the schedules along with their top-level data such as 'id', 'execution_time', etc.    
    '''
    with open(json_path, 'r') as file:
        data = pd.read_json(file)
    flat_data = pd.DataFrame()  # Empty df
    for record in data.to_dict(orient='records'):
        schedule_df = json_normalize(record, 'daily_schedule', errors='ignore') # Normalize the daily_schedule for each record
        for col in data.columns.difference(['daily_schedule']):  # Adding the top-level data as new columns to the schedule_df
            schedule_df[col] = record[col]
        flat_data = pd.concat([flat_data, schedule_df], ignore_index=True) # append
    return flat_data

def minutes_to_time(minute_value):
    total_minutes = minute_value * TIME_INTERVAL
    hours, minutes = divmod(total_minutes, 60)
    if hours >= 24:
        hours = hours % 24
    return time(hour=int(hours), minute=int(minutes))

def filter_and_sort_activities(df):
    ''' 
    Keep lines correcponding to the maximum duration of each triplet ('acity', 'id', 'start')
    Sort the resulting dataframe by ['id', 'start']
    '''
    df['duration_td'] = df['duration'].apply(lambda x: pd.to_timedelta(x.strftime('%H:%M:%S'))) # temp col of timedelta obj
    # Group by 'acity' and find the index of the row with the maximum duration
    idx = df.groupby(['acity', 'id', 'start'])['duration_td'].idxmax()
    max_duration_df = df.loc[idx] # Select only those rows 
    max_duration_df = max_duration_df.drop(columns=['duration_td']) # drop temp col
    max_duration_df = max_duration_df.sort_values(by=['id', 'start'], ascending = True) # sort output
    return max_duration_df

def reorder_columns(df):
    new_order = [
        'id', 'group', 'facility', 'start', 'duration', 'end_time', 'x', 'y', 'deviation_start', 'deviation_dur', # mandatory info
        'total_deviation_start', 'total_deviation_dur', 'utility', 'DSSR_iterations', 'execution_time', 'cum_utility' # additional info
    ]
    df.rename({'group': 'type', 'start': 'start_time', 'duration': 'duration_time', 'cum_utility':'cumulative_utility'})
    df = df[new_order]
    return df

def calculate_end_time(row):
    ''' Calculate the end time of activities '''
    def time_to_minutes(t):
        return t.hour * 60 + t.minute
    start_minutes = time_to_minutes(row['start'])
    duration_minutes = time_to_minutes(row['duration'])
    end_minutes = start_minutes + duration_minutes
    if end_minutes >= 1440: # for the end of the day
        return time(23, 59, 0)
    hours, minutes = divmod(end_minutes, 60)
    return time(hour=hours, minute=minutes)

def process_flat_df(df): 
    ''' 
    Calculate end times of activities
    Calculate real times from nb of time intervals
    Reorder the columns
    '''
    
    df['start'] = df['start'].apply(minutes_to_time)
    df['duration'] = df['duration'].apply(minutes_to_time)
    df['time'] = df['time'].apply(minutes_to_time)
    df['deviation_start'] = df['deviation_start'].apply(minutes_to_time)
    df['deviation_dur'] = df['deviation_dur'].apply(minutes_to_time)
    df['total_deviation_start'] = df['total_deviation_start'].apply(minutes_to_time)
    df['total_deviation_dur'] = df['total_deviation_dur'].apply(minutes_to_time)

    df['execution_time'] = round(df['execution_time'], 4)
    filtered_df = filter_and_sort_activities(df)
    filtered_df['end_time'] = filtered_df.apply(calculate_end_time, axis=1)
    schedule_postprocessed = reorder_columns(filtered_df)
    return schedule_postprocessed

def process_scenario_json(scenario):
    path_to_json_file = f"Data/3_Generated/{scenario}.json"
    results = json_to_flat_dataframe(path_to_json_file)
    results_clean = process_flat_df(results)
    return results_clean

def create_postprocess_files(LOCAL, time_interval, scenari, i):
    global TIME_INTERVAL  
    TIME_INTERVAL = time_interval
    
    ######################################################################################
    ## Population file ###################################################################

    vaud_pop_path = 'Data/1_Original/vaud_population.csv.gz'
    with gzip.open(vaud_pop_path, 'rt') as file:
        vaud_pop = pd.read_csv(file)
    pop_local_prepro = pd.read_csv(f"Data/2_PreProcessed/population_{LOCAL}.csv")[:i]
    pop_local = vaud_pop[vaud_pop['id'].isin(pop_local_prepro['id'])]
    pop_local.to_csv(f'Data/4_PostProcessed/population_{LOCAL}.csv', index=False) 

    ######################################################################################
    ## Activity files ####################################################################

    for scenario in scenari:
        activity = process_scenario_json(scenario)
        activity.to_csv(f'Data/4_PostProcessed/activities_{scenario}.csv', index=False) 