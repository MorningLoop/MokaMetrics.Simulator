

The MokaMetrics system uses 5 Kafka topics for production telemetry management:





4 topics for real-time machine telemetry



1 topic for lot completion recap

Kafka Broker: 165.227.168.240:29093



📊 Machine Telemetry Topics

1. mokametrics.telemetry.cnc

Description: Real-time telemetry data from CNC milling machines

Message format:

{
  "lot_code": "L-2024-0001",
  "cycle_time": 28.73,
  "cutting_depth": 4.76,
  "vibration": 735,
  
  "completed_pieces_from_last_maintenance": 42,
  "error": "None",
  "local_timestamp": "2024-12-20T11:21:41+01:00",
  "utc_timestamp": "2024-12-20T10:21:41Z",
  "site": "Italy",
  "machine_id": "cnc_Italy_1",
  "status": 1
}


Fields:





lot_code (string): Unique lot identifier



cycle_time (float): Processing time in minutes



cutting_depth (float): Cutting depth in mm



vibration (float): Vibration level (0-1000)



completed_pieces_from_last_maintenance (int): Counter of completed pieces since last maintenance



error (string): "None", "Tool breakage", "Worn tool"



local_timestamp (ISO 8601): Timestamp with local timezone



utc_timestamp (ISO 8601): UTC timestamp



site (string): "Italy", "Brazil", "Vietnam"



machine_id (string): Unique machine identifier



status (int): enum that decodes into machine status:

public enum MachineStatuses
{
    Operational = 1, // Machine is operational and running normally
    Maintenance = 2, // Machine is under maintenance
    Alarm = 3, // Machine is under alarm or has a critical issue
    Offline = 4, // Machine is shut down
    Idle = 5 // Machine is idle and not in production
}



2. mokametrics.telemetry.lathe

Description: Real-time telemetry data from automatic lathes

Message format:

{
  "lot_code": "L-2024-0001",
  "cycle_time": 
  "rotation_speed": 1500.5,
  "spindle_temperature": 65.3,

  "completed_pieces_from_last_maintenance": 42,
  "error" : "None",
  "local_timestamp": "2024-12-20T12:30:00+01:00",
  "utc_timestamp": "2024-12-20T11:30:00Z",
  "site": "Italy",
  "machine_id": "lathe_Italy_2"
  "status": 1
}

Fields:





lot_code (string): Unique lot identifier



cycle_time (float): Processing time in minutes



rotation_speed (float): Rotation speed in RPM



spindle_temperature (float): Spindle temperature in °C



completed_pieces_from_last_maintenance (int): Counter of completed pieces since last maintenance



error (string): "None", "Tool breakage", "Worn tool"



local_timestamp (ISO 8601): Timestamp with local timezone



utc_timestamp (ISO 8601): UTC timestamp



site (string): "Italy", "Brazil", "Vietnam"



machine_id (string): Unique machine identifier



status (int): See MachineStatuses enum above.



3. mokametrics.telemetry.assembly

Description: Real-time telemetry data from assembly lines

Message format:

{
  "lot_code": "L-2024-0001",
  "cycle_time": 75.5,
  "active_operators": 5,

  "completed_pieces_since_last_maintenance": 42,
  "error": "None",
  "local_timestamp": "2024-12-20T14:15:00+01:00",
  "utc_timestamp": "2024-12-20T13:15:00Z",
  "site": "Italy",
  "machine_id": "assembly_Italy_1",
  "status": 1
}

Fields:





lot_code (string): Unique lot identifier



cycle_time (float): Processing time in minutes



active_operators (int): Number of active operators on the line



completed_pieces_since_last_maintenance (int): Counter of completed pieces since last maintenance



error (string): "None", "Missing component", "Misalignment", "Excessive cycle time", "Insufficient quality"



local_timestamp (ISO 8601): Timestamp with local timezone



utc_timestamp (ISO 8601): UTC timestamp



site (string): "Italy", "Brazil", "Vietnam"



machine_id (string): Unique machine identifier



status (int): See MachineStatuses enum above.



4. mokametrics.telemetry.testing

Description: Real-time telemetry data from test lines

Message format:

{
  "lot_code": "L-2024-0001",
  "functional_test_results": {
    "pressure": true,
    "temperature": true,
    "flow_rate": true,
    "noise": false,
    "vibration": true
  },
  "boiler_pressure": 12.5,
  "boiler_temperature": 92.3,
  "energy_consumption": 2.8,
  "completed_pieces_since_last_maintenance": 42,
  "error": "None",
  "local_timestamp": "2024-12-20T15:45:00+01:00",
  "utc_timestamp": "2024-12-20T14:45:00Z",
  "site": "Italy",
  "machine_id": "testing_Italy_1",
  "status": 1
}

{
  "lot_code": "L-2024-0001",
  "cycle_time": 
  "rotation_speed": 1500.5,
  "spindle_temperature": 65.3,

  "completed_pieces_from_last_maintenance": 42,
  "error" : "None",
  "local_timestamp": "2024-12-20T12:30:00+01:00",
  "utc_timestamp": "2024-12-20T11:30:00Z",
  "site": "Italy",
  "machine_id": "lathe_Italy_2"
  "status": 1
}


Fields:





lot_code (string): Unique lot identifier



functional_test_results (object): Test results (true = passed, false = failed)





pressure (boolean)



temperature (boolean)



flow_rate (boolean)



noise (boolean)



vibration (boolean)



boiler_pressure (float): Boiler pressure in bar



boiler_temperature (float): Boiler temperature in °C



energy_consumption (float): Energy consumption in kWh



completed_pieces_since_last_maintenance (int): Counter of completed pieces since last maintenance



error (string): "None", "Pressure anomaly", "Temperature anomaly", "Flow rate anomaly", "Noise anomaly", "Vibration anomaly"



local_timestamp (ISO 8601): Timestamp with local timezone



utc_timestamp (ISO 8601): UTC timestamp



site (string): "Italy", "Brazil", "Vietnam"



machine_id (string): Unique machine identifier



status (int): See MachineStatuses enum above.



🏁 Production Completion Topic

5. mokametrics.production.lot_completion

Description: Recap message sent when a lot completes all 4 production phases

Message format:

{
  "lot_code": "L-2024-0001",
  "lot_total_quantity": 98,
  "lot_completed_pieces": 56,
  "total_duration_minutes": 345,
  "cnc_duration": 45,
  "lathe_duration": 35,
  "assembly_duration": 80,
  "test_duration": 25,
  "site": "Italy",
  "local_timestamp": "2024-12-20T16:45:00+01:00",
  "completion_timestamp": "2024-12-20T15:45:00Z",
  "result": "COMPLETED"
}


Fields:





lot_code (string): Unique lot identifier



customer (string): Customer name



quantity (int): Quantity of completed pieces



site (string): "Italy", "Brazil", "Vietnam"



local_timestamp (ISO 8601): Local completion timestamp with timezone



completion_timestamp (ISO 8601): UTC completion timestamp



total_duration_minutes (int): Total time from first to last processing



cnc_duration (int): Processing minutes in CNC milling



lathe_duration (int): Processing minutes in lathe



assembly_duration (int): Processing minutes in assembly



test_duration (int): Processing minutes in test



result (string): "COMPLETED" or "REJECTED"



🔧 Topic Configuration

Partitions and Retention

# Telemetry topics (high frequency)
- Partitions: 9 (3 per location)
- Retention: 3 days
- Compression: snappy

# Completion topic (low frequency, important data)
- Partitions: 3 (1 per location)
- Retention: 90 days
- Compression: gzip


Partitioning Keys





Telemetry topics: machine_id as key



Completion topic: lot_code as key



📍 Timezones by Location





Italy: Europe/Rome (UTC+1/+2)



Brazil: America/Sao_Paulo (UTC-3)



Vietnam: Asia/Ho_Chi_Minh (UTC+7)

All messages include both local_timestamp (with timezone) and utc_timestamp to facilitate aggregations and visualizations.