import wrds

return_cal_list=['simple','compound']

my_username='felicia_hec'
my_password='S19491001j!547154'

print("Connecting to WRDS...")
db = wrds.Connection(wrds_username=my_username, wrds_password=my_password)
print('WRDS connected!')

if __name__ == "__main__":

    sql_query = "SELECT permno, date, prc, ret, vol FROM crsp.dsf LIMIT 5"
    df = db.raw_sql(sql_query, date_cols=['date'])

    print("\n--- Downloaded Data ---")
    print(df)

    db.close()
