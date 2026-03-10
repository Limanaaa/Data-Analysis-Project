import wrds

# Credential variables
my_username = "felicia_hec"
my_password = "S19491001j!547154"

print("Connecting to WRDS...")
db = wrds.Connection(wrds_username=my_username, wrds_password=my_password)


print(db)

db.close()