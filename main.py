from tqdm import tqdm
import subprocess
import numpy as np
from ctypes import Structure, c_int, c_double, POINTER, CDLL
import pandas as pd
from collections import namedtuple
import time
import Post_processing
import warnings

warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)

LOCAL = 'Lausanne'
# LOCAL = 'Avenches'
SCHEDULING_VERSION = 6
TIME_INTERVAL = 5
HORIZON = round(24*60/TIME_INTERVAL) + 1
SPEED = 19*16.667                                                       # 1km/h = 16.667 m/min
TRAVEL_TIME_PENALTY = 0.1                                              # we will add dusk, home, dawn and work
H8 = round(8*60/TIME_INTERVAL) + 1                
H12 = round(12*60/TIME_INTERVAL) + 1  
H13 = round(13*60/TIME_INTERVAL) + 1  
H17 = round(17*60/TIME_INTERVAL) + 1  
H20 = round(20*60/TIME_INTERVAL) + 1  
FLEXIBLE = round(60/TIME_INTERVAL)
MIDDLE_FLEXIBLE = round(30/TIME_INTERVAL)
NOT_FLEXIBLE = round(10/TIME_INTERVAL)
group_to_type = {
    0: 'home',
    1: 'education',
    2: 'work',
    3: 'leisure',
    4: 'shop'
}
groups = ['home', 'education', 'work', 'leisure', 'shop']
# https://www.swisstopo.admin.ch/en/maps-data-online/calculation-services/navref.html # Check the facility location

############################################################################################################
##### START OF STRUCTURE ###################################################################################
############################################################################################################

class Group_mem(Structure):
    pass

Group_mem._fields_ = [
    ("g", c_int),
    ("previous", POINTER(Group_mem)),
    ("next", POINTER(Group_mem))
]

class Activity(Structure):
    pass

Activity._fields_ = [
    ("id", c_int),
    ("earliest_start", c_int),
    ("latest_start", c_int),
    ("min_duration", c_int),
    ("max_duration", c_int),
    ("x", c_int),
    ("y", c_int),
    ("group", c_int),
    ("memory", POINTER(Group_mem)),
    ("des_duration", c_int),
    ("des_start_time", c_int)
]

class Label(Structure):
    pass

Label._fields_ = [
    ("acity", c_int),
    ("time", c_int),
    ("start_time", c_int),
    ("duration", c_int),
    ("deviation_start", c_int),
    ("deviation_dur", c_int),
    ("utility", c_double),
    ("mem", POINTER(Group_mem)),
    ("previous", POINTER(Label)),
    ("act", POINTER(Activity))
]

class L_list(Structure):
    pass

L_list._fields_ = [
    ("element", POINTER(Label)),
    ("previous", POINTER(L_list)),
    ("next", POINTER(L_list))
]

##### END OF STRUCTURE #####################################################################################
############################################################################################################
##### START OF INITIALIZATION ##############################################################################

def initialize_and_personalize_activities(df, num_activities, individual):
    ''' Create and personalize an array of activities based on the given dataframe and individual data. '''
    activities_array = (Activity * num_activities)()

    # Initialize dawn and dusk activities with the individual's home coordinates
    activities_array[0].id = 0
    activities_array[0].x = individual['home_x']
    activities_array[0].y = individual['home_y']
    activities_array[0].earliest_start = 0  
    activities_array[0].latest_start = 0      
    activities_array[0].max_duration = HORIZON-2   
    activities_array[0].min_duration = 1
    activities_array[0].group = 0

    activities_array[num_activities-1].id = num_activities-1
    activities_array[num_activities-1].x = individual['home_x']
    activities_array[num_activities-1].y = individual['home_y']
    activities_array[num_activities-1].earliest_start = 0
    activities_array[num_activities-1].latest_start = HORIZON-2
    activities_array[num_activities-1].max_duration = HORIZON-2                       
    activities_array[num_activities-1].min_duration = 1 
    activities_array[num_activities-1].group = 0

    # home
    activities_array[num_activities-2].id = num_activities-2
    activities_array[num_activities-2].x = individual['home_x']
    activities_array[num_activities-2].y = individual['home_y']
    activities_array[num_activities-2].earliest_start = 0
    activities_array[num_activities-2].latest_start = HORIZON
    activities_array[num_activities-2].max_duration = HORIZON-2                       
    activities_array[num_activities-2].min_duration = 1 
    activities_array[num_activities-2].des_duration = 0 
    activities_array[num_activities-2].des_start_time = 0   
    activities_array[num_activities-2].group = 0

    # work
    activities_array[num_activities-3].id = num_activities-3
    activities_array[num_activities-3].x = individual['work_x']
    activities_array[num_activities-3].y = individual['work_y']
    activities_array[num_activities-3].earliest_start = round(5*60/TIME_INTERVAL) # 5h
    activities_array[num_activities-3].latest_start = round(23*60/TIME_INTERVAL) # 23h
    activities_array[num_activities-3].max_duration = round(12*60/TIME_INTERVAL) # 12h
    activities_array[num_activities-3].min_duration = round(10/TIME_INTERVAL) # 10m
    activities_array[num_activities-3].group = 2
    activities_array[num_activities-3].des_duration = individual['work_dur']
    activities_array[num_activities-3].des_start_time = individual['work_start']

    # Initialize the rest of the activities from the dataframe
    for index, row in df.iterrows():
        activity_index = index + 1  # leave index 0 for the dawn activity
        activities_array[activity_index].id = activity_index
        activities_array[activity_index].x = row['x']
        activities_array[activity_index].y = row['y']
        activities_array[activity_index].earliest_start = row['earliest_start']
        activities_array[activity_index].latest_start = row['latest_start']
        activities_array[activity_index].max_duration = row['max_duration']
        activities_array[activity_index].min_duration = row['min_duration']
        activities_array[activity_index].group = row['group']
        
        # Personalize the activity based on the individual's preferences
        group = activities_array[activity_index].group
        if group > 0:  # Assuming group 0 is 'home' and doesn't need personalization
            activity_type = group_to_type[group]
            activities_array[activity_index].des_duration = individual[f'{activity_type}_dur']
            activities_array[activity_index].des_start_time = individual[f'{activity_type}_start']

    return activities_array

def initialize_utility(): 
    ''' Initialise les parametres de la utility function'''
    UtilityParams = namedtuple('UtilityParams', 'asc early late long short')
    params = UtilityParams( 
        # order = [home, education, work, leisure, shop]
        asc=[0, 18.7, 13.1, 8.74, 10.5],
        early=[0, 1.35, 0.619, 0.0996, 1.01],
        late=[0, 1.63, 0.338, 0.239, 0.858],
        long=[0, 1.14, 1.22, 0.08, 0.683],
        short=[0, 1.75, 0.932, 0.101, 1.81]
    )
    return params

##### END OF INITIALIZATION ################################################################################
############################################################################################################
##### START OF FUNCTIONS ###################################################################################

def compile_code():
    ''' Compile le code C '''
    compile_command = ["gcc", "-m64", "-O3", "-shared", "-o", 
                   f"Optimizer/scheduling_v{SCHEDULING_VERSION}.dll", 
                   f"Optimizer/scheduling_v{SCHEDULING_VERSION}.c", "-lm"]
    subprocess.run(compile_command)

def extract_schedule_data(label_pointer, activity_df, individual, num_activities):
    """
    Extrait les données de planning à partir d'un pointeur de label, 
    en remontant à la racine et en stockant les données importantes.
    """
    path_to_root = []
    while label_pointer:
        path_to_root.append(label_pointer)
        label_pointer = label_pointer.contents.previous

    schedule_data_dict = {}
    for label_pointer in reversed(path_to_root):
        label = label_pointer.contents

        acity = label.acity
        if (acity > 0) and (acity < num_activities-3):              # general activity
            activity_row_from_csv = activity_df.iloc[acity-1]
            facility_id = activity_row_from_csv['facility']
            x = activity_row_from_csv['x']
            y = activity_row_from_csv['y']      
        elif (acity == num_activities-3):                           # work
            facility_id = individual['work_id']
            x = individual['work_x']
            y = individual['work_y']
        else:                                                       # home
            facility_id = individual['homeid']
            x = individual['home_x']
            y = individual['home_y']

        data = {
            "acity": label.acity,
            "facility": facility_id,
            "group": group_to_type[label.act.contents.group],
            "start": label.start_time,
            "duration": label.duration,
            "time": label.time,
            # "cum_utility": label.utility,
            # "deviation_start": label.deviation_start,
            # "deviation_dur": label.deviation_dur,
            "x": x,
            "y": y
        }

        unique_key = (data["acity"], data["start"])
        # Vérifier si la durée est plus grande que celle déjà stockée pour cette clé
        if unique_key not in schedule_data_dict or schedule_data_dict[unique_key]["duration"] < data["duration"]:
            schedule_data_dict[unique_key] = data

    schedule_data = list(schedule_data_dict.values())
    return schedule_data

def filter_closest(all_activities, individual, num_act_to_select, constraints, activities_locations):
    home = np.array((individual['home_x'], individual['home_y']))
    work = np.array((individual['work_x'], individual['work_y']))

    # Apply constraints
    mask = np.ones(len(all_activities), dtype=bool)  # Initialize mask to include all activities
    if constraints[0]:  # If leisure is closed
        mask &= (all_activities['group'] != 3)
    if constraints[1]:  # If shops are closed
        mask &= (all_activities['group'] != 4)
    if constraints[2]:  # If education is closed
        mask &= (all_activities['group'] != 1)

    # Apply the mask to both all_activities and activities_locations
    filtered_activities = all_activities[mask]
    filtered_locations = activities_locations[mask]

    # Calculate fraction of each facility type in the filtered DataFrame
    type_fractions = filtered_activities['type'].value_counts(normalize=True)

    # Calculate distances
    distances_home = np.linalg.norm(filtered_locations - home, axis=1)
    distances_work = np.linalg.norm(filtered_locations - work, axis=1)
    min_distances = np.minimum(distances_home, distances_work)

    # Add distances to DataFrame
    filtered_activities['distance'] = min_distances

    # Select closest facilities for each type based on the fraction
    selected_activities = pd.DataFrame()
    for facility_type, fraction in type_fractions.items():
        type_activities = filtered_activities[filtered_activities['type'] == facility_type]
        n_closest = int(num_act_to_select * fraction)
        selected_activities = pd.concat([selected_activities, type_activities.sort_values('distance').head(n_closest)])
    
    return selected_activities.reset_index(drop=True)

##### END OF FUNCTIONS #####################################################################################
############################################################################################################
##### START OF EXECUTION ###################################################################################

def compile_and_initialize(i): 
    
    compile_code()
    lib = CDLL(f"Optimizer/scheduling_v{SCHEDULING_VERSION}.dll")            # python is 64 bits and compiler too (check with gcc --version)

    activity_csv = pd.read_csv(f"Data/2_PreProcessed/activities_{LOCAL}.csv")
    population_csv = pd.read_csv(f"Data/2_PreProcessed/population_{LOCAL}.csv", nrows=i)
     
    lib.get_final_schedule.restype = POINTER(Label)
    lib.get_total_time.restype = c_double
    lib.get_count.restype = c_int
                                                    
    util_params = initialize_utility() 
    asc_array = (c_double * len(util_params.asc))(*util_params.asc)
    early_array = (c_double * len(util_params.early))(*util_params.early)
    late_array = (c_double * len(util_params.late))(*util_params.late)
    long_array = (c_double * len(util_params.long))(*util_params.long)
    short_array = (c_double * len(util_params.short))(*util_params.short) 

    lib.set_general_parameters(c_int(HORIZON), c_double(SPEED), c_double(TRAVEL_TIME_PENALTY), 
                               c_int(H8), c_int(H12), c_int(H13), c_int(H17), c_int(H20), c_int(TIME_INTERVAL),
                               asc_array, early_array, late_array, long_array, short_array,
                               c_int(FLEXIBLE), c_int(MIDDLE_FLEXIBLE), c_int(NOT_FLEXIBLE))

    return activity_csv, population_csv, lib

def call_to_optimizer(activity_csv, population_csv, scenario, constraints, num_act_to_select = 15):

    print(f"Running scenario: {scenario}")
    constraints_array = (c_int * len(constraints))(*constraints)
    lib.set_scenario_constraints(constraints_array)
    activities_locations = activity_csv[['x', 'y']].to_numpy()

    total_deviations_start = [] 
    total_deviations_dur = []
    # DSSR_iterations = []
    # execution_times = []
    final_utilities = []
    schedules = []
    ids=[]
    for i, individual in tqdm(population_csv.iterrows(), total=population_csv.shape[0]):
        
        closest_facilities = filter_closest(activity_csv, individual, num_act_to_select, constraints, activities_locations)
        # print(closest_facilities)
        # print(f"\nIndividual : {individual['id']} || home : ({individual['home_x']}, {individual['home_y']}) || home : ({individual['work_x']}, {individual['work_y']})")
        num_activities = len(closest_facilities)+4
        activities_array = initialize_and_personalize_activities(closest_facilities, num_activities, individual)
        lib.set_activities(activities_array, num_activities)
        # for activity in perso_activities_array:
        #     print(f"ID: {activity.id}, Group: {activity.group}, desired start: {activity.des_start_time}, desired duration: {activity.des_duration}")

        lib.main()

        # iter = lib.get_count()
        # time = lib.get_total_time()
        schedule_pointer = lib.get_final_schedule()   
        schedule_data = extract_schedule_data(schedule_pointer, activity_csv, individual, num_activities) # perso activities array

        # DSSR_iterations.append(iter)
        # execution_times.append(time)
        schedules.append(schedule_data) 
        ids.append(individual['id'])

        if schedule_pointer and schedule_pointer.contents:
            final_utilities.append(schedule_pointer.contents.utility)
            total_deviations_start.append(schedule_pointer.contents.deviation_start)
            total_deviations_dur.append(schedule_pointer.contents.deviation_dur)
        else:
            final_utilities.append(0)
            total_deviations_start.append(0)
            total_deviations_dur.append(0)

        lib.free_bucket() # doit etre ici pour extraire les infos avant
        # lib.free_activities() # deja fait par le garbage collector de python

        # Append results every 1000 iterations or at the end
        if i % 1000 == 0 or i == population_csv.shape[0] - 1:
            print(f"\n i={i}, saving intermediate results...")

            # Append to the existing file or create new if it doesn't exist
            mode = 'a' if i != 0 else 'w'
            results = pd.DataFrame({
                'id': ids, 
                'utility': final_utilities,
                'total_deviation_start' : total_deviations_start,
                'total_deviation_dur' : total_deviations_dur,
                'daily_schedule': schedules  
            })
            results.to_json(f"Data/3_Generated/{scenario}3.json", orient='records', lines=True, indent=4, mode=mode)

            # Reset lists to free memory
            ids.clear()
            final_utilities.clear()
            schedules.clear()
            total_deviations_start.clear()
            total_deviations_dur.clear()


if __name__ == "__main__":
        
    # scenari = ['Normal_life', 'Outings_limitation', 'Only_economy', 'Early_curfew', 
    #             'Early_curfew', 'Finding_balance', 'Impact_of_leisure']
    scenari = ['Impact_of_leisure']    
    i = 4000
    n = 15    
    activity_csv, population_csv, lib = compile_and_initialize(i)    

    # constraints = [
    #     leisure closure,
    #     shop closure,
    #     education closure,
    #     work closure,
    #     Outings limitation,
    #     Early curfew,
    #     Finding balance]
    constraints = {
        'Normal_life' :          [0, 0, 0, 0, 0, 0, 0], # 8m29
        'Outings_limitation' :   [1, 0, 0, 0, 1, 0, 0], 
        'Only_economy' :         [1, 1, 1, 0, 0, 0, 0],
        'Early_curfew' :         [0, 0, 0, 0, 0, 1, 0],
        'Essential_needs' :      [1, 0, 1, 0, 0, 0, 0],
        'Finding_balance' :      [0, 0, 0, 0, 0, 0, 1],
        'Impact_of_leisure' :    [1, 0, 0, 0, 0, 0, 0]
    }

    elapsed_times = []
    for scenario_name in scenari:
        start_time = time.time()
        call_to_optimizer(activity_csv, population_csv[:i], scenario_name, constraints[scenario_name], num_act_to_select=n)
        end_time = time.time()
        elapsed_time = end_time - start_time
        elapsed_times.append(round(elapsed_time, 2))
        print(f"For {len(population_csv) if i > 1000000 else i} individuals of {LOCAL} and {n} closest activities around their home/work, the execution time of scenario {scenario_name} is {elapsed_time:.1f} seconds\n")

    # print(elapsed_times)
    # print("Creating the Post-processed files...")
    # Post_processing.create_postprocess_files(LOCAL, TIME_INTERVAL, scenari, i)
