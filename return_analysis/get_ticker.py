import wrds
db = wrds.Connection(wrds_username='joe')
db.raw_sql('SELECT date, dji FROM djones.djdaily')

