#%%

import pickle as pkl

path_good = '/Users/alexandreviolleau/Library/CloudStorage/GoogleDrive-zouglagalex@gmail.com/My Drive/Cours/HEC/Lessons/3_Third_quarter/Data_Analysis_For_Finance/Dropbox/Source_Data/Project2/words_dictionary/positive-words.txt'
path_bad = '/Users/alexandreviolleau/Library/CloudStorage/GoogleDrive-zouglagalex@gmail.com/My Drive/Cours/HEC/Lessons/3_Third_quarter/Data_Analysis_For_Finance/Dropbox/Source_Data/Project2/words_dictionary/negative-words.txt'

def load_lexicon_to_set(file_path):
    """
    Reads a lexicon file, skips the semicolon header, 
    and returns a set of the actual words.
    """
    words_set = set()
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            # Clean up the line by removing whitespace and newline characters
            cleaned_line = line.strip()
            
            # Skip lines that are empty or start with the comment character ';'
            if not cleaned_line or cleaned_line.startswith(';'):
                continue
                
            # If it passes the checks above, it's a valid word. Add it to our set.
            words_set.add(cleaned_line)
            
    return words_set

if __name__ == "__main__":
        
    good_words = load_lexicon_to_set(path_good)
    bad_words = load_lexicon_to_set(path_bad)

    folder_store = "/Users/alexandreviolleau/Documents/Code/Data-Analysis-Project/data_words"

    file_good = f"{folder_store}/good_words.pkl"
    file_bad = f"{folder_store}/bad_words.pkl"

    with open(file_good, "wb") as file:
            pkl.dump(good_words, file)

    with open(file_bad, "wb") as file:
            pkl.dump(bad_words, file)
