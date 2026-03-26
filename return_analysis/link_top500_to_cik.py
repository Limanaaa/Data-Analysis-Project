from config import db

sql_test = """
select *
from comp.security
where tic in ('AAPL', 'MSFT', 'AMZN', 'GOOG', 'GOOGL')
limit 20
"""

security = db.raw_sql(sql_test)
print(security.columns.tolist())
print(security.head(20))