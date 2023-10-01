

LOCAL = 'Lausanne'

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
vaud_activity_df = read_gzipped_csv(activity_file)
vaud_population_df = read_gzipped_csv(population_file)
vaud_trip_df = read_gzipped_csv(trip_file)

print("File opened and read \n")

merged_df = vaud_activity_df.merge(vaud_population_df, on='id').merge(vaud_trip_df, on='id')
print(merged_df.head())

# merge les 3 dataframe
# filtrer selon  les habitants qui sont dans la localite LOCAL
# obtenir df des facilities existantes avec leur localisation et leur type (filtrer les others)
# obtenir df de schedules (commebt les filtrer? les modifiers en home dawn and dusk ? )
# obtenir le df des individus, avec leur age, home_x and home_y et les lieux de 'work/studies' de chacun dans le df
# obtenir les df de trips (avec les informations du numero de liens, mode de transport, depart et arrivee) -> calculer nb de trips et leur duree, puis evaluer la duree moyenne des trajets 
# enregistrer en csv chacun des dataframe crees dans /data_preprocessed


