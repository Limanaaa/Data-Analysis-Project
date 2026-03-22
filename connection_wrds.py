#%%

import wrds

# Credential variables
my_username = "alexandre_v"
my_password = "nojvub-tyxfif-batgY8"

print("Connecting to WRDS...")
db = wrds.Connection(wrds_username=my_username, wrds_password=my_password)

sql_query = "SELECT permno, date, prc, ret, vol FROM crsp.dsf LIMIT 5"
df = db.raw_sql(sql_query, date_cols=['date'])

print("\n--- Downloaded Data ---")
print(df)

db.close()

# %%
