from config import db

test_ciks = [
    '0000773840',  # HON
    '0000318154',  # AMGN
    '0000012927',  # BA
    '0000769397',  # ADSK
    '0000732712'   # VZ
]

cik_str = ",".join([f"'{x}'" for x in test_ciks])

for table_name in ["forms", "_forms_", "dforms", "wrds_forms"]:
    print(f"\n=== {table_name} ===")
    sql_test = f"""
    select *
    from secsamp_all.{table_name}
    where cik in ({cik_str})
    limit 20
    """
    try:
        test_df = db.raw_sql(sql_test)
        print("columns:", test_df.columns.tolist())
        print(test_df.head(20))
        print("rows:", len(test_df))
    except Exception as e:
        print("Error:", e)