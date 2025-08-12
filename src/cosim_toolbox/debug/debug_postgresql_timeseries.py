from data_management.postgresql_timeseries import PostgreSQLTimeSeriesReader

with PostgreSQLTimeSeriesReader(
    host="penny.pnl.gov",
    port=5432,
    database="copper",
    user="worker",
    password="worker",
    schema_name="ny_dr_prototype",
) as reader:
    data = reader.read_data(data_type="hdt_double")
    print(data)