#%%

from sec_edgar_downloader import Downloader
import time
from tqdm import tqdm

def cik_downloader(cik_num:str, years_to_download:list[int], verbose:bool=False, company="Placeholder", company_mail="place.hold@er.com"):
    dl = Downloader(company, company_mail)
    pbar = tqdm(years_to_download)
    
    for year in pbar:
        pbar.set_description(f"Downloading 10-K for {cik_num} in {year}")
        
        after_date = f"{year}-01-01"
        before_date = f"{year}-12-31"
        
        try:
            dl.get("10-K", cik_num, after=after_date, before=before_date)
            time.sleep(0.15)  # SEC rate limit (10 requests per second max)
            
        except Exception as e:
            print(f"Could not download 10-K for {cik} in {year}: {e}")

    if verbose:
        print("Download complete!")

# Use example
if __name__ == "__main__":
    # Apple (320193), Microsoft (789019)
    top_500_ciks = ['0000320193', '0000789019'] 
    years_to_download = [2022, 2023, 2024]

    for cik in top_500_ciks:
        cik_downloader(cik, years_to_download, verbose=True)

# %%
