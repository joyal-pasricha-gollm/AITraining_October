import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
# files: urban_mobility.csv, equipment_events.json, and coastal_monitoring_log.txt.
# A1. Load urban_mobility.csv into a Pandas DataFrame and display the first five rows.
df = pd.read_csv("urban_mobility.csv")
print("A1. First five rows are: ")
print(df.head())

# A2. Create a new column Energy_Per_Km = Energy_Used_kWh / Distance_Km.
df["Energy_Per_Km"] = df["Energy_Used_kWh"] / df["Distance_Km"]
print("A2.", df)

# A3. Display only Electric Van records where Maintenance_Flag is Yes.
electric_vans_maintenance = df[(df["Vehicle_Type"] == "Electric Van") & (df["Maintenance_Flag"] == "Yes")]
print("A3", electric_vans_maintenance)


# A4. Group by Vehicle_Type and display average Distance_Km and total Trips_Count.
vehicle_summary = (df.groupby("Vehicle_Type").agg(Average_Distance_Km=("Distance_Km", "mean"),Total_Trips_Count=("Trips_Count", "sum")))
print("A4. Vehicle summary", vehicle_summary )


# A5. Use NumPy to calculate the mean, maximum and minimum of Energy_Used_kWh.
energy = df["Energy_Used_kWh"].to_numpy()
mean_energy = np.mean(energy)
max_energy = np.max(energy)
min_energy = np.min(energy)
print("A5. Energy summary")
print("mean:", mean_energy)
print("max:", max_energy)
print("min:", min_energy)

# A6. Create one bar chart showing average Energy_Used_kWh by Vehicle_Type using Matplotlib or Seaborn.
average_energy = df.groupby("Vehicle_Type")["Energy_Used_kWh"].mean()
plt.bar(average_energy.index, average_energy.values)
plt.xlabel("Vehicle Type")
plt.ylabel("Energy Used (kWh)")
plt.title("bar chart showing average Energy_Used_kWh by Vehicle_Type")
plt.show()

# A7. Load equipment_events.json and print event_id, asset type, site and severity for every event.
with open("equipment_events.json", "r") as file:
    events = json.load(file)
print("A7")
for event in events:
    asset = event.get("asset", {})
    print("Event ID:" , event.get("event_id"), " Asset type:", asset.get("type"), "Site:", asset.get("site"), "severity:", event.get("severity"))

# A8. Display JSON records with temperature above 70. If actions is missing, display 'No actions recorded'.
for event in events:
    temperature = event.get("temperature", 0)
    if temperature > 70 :
        actions = event.get("actions")
        if not actions:
            actions_output = "no actions recorded"
        else:
            actions_output = ", ".join(actions)
        print("Event ID:" , event.get("event_id"), " temperature:", asset.get("temperature"), "actions:", actions_output)
# A9. Read coastal_monitoring_log.txt and count total words and the number of times the word 'inspection' appears.
with (open("coastal_monitoring_log.txt", "r") as file):
    text = file.read()
clean_text = text.lower()
for ch in ".,!?;:'|()-""":
    clean_text = clean_text.replace(ch, " ")
words = clean_text.split()
total_words = len(words)
inspection_count = words.count("inspection")
print("total words:", total_words)
print("inspection count:", inspection_count)


# A10. Print only the lines containing either 'boardwalk', 'maintenance', or 'wind'.
keywords = ['boardwalk', 'maintenance', 'wind']
print("A10")
for line in text.splitlines():
    if any(keyword.lower() in line.lower() for keyword in keywords):
        print(line)


# Short concept: State which of the three supplied files is structured, semi-structured and unstructured, and give one reason for each.
print("Short concept qestion: State which of the three supplied files is structured, semi-structured and unstructured, and give one reason for each.")
print("urban_mobility.csv is structrured data as it follows a fixed tabular schema of rows and columns")
print("equipment_events.json is semi structured as it uses keys and nested objects but fields may or may not vary")
print("coastal_monitoring_log.txt is unstructured as it contains natural language text without fixed schema")






