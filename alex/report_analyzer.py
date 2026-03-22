#%%

def find_string_in_file(file_path, target_string):
    """
    Searches for a specific string in a text file and returns the matching lines.
    """
    matched_lines = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, start=1):
                if target_string in line:
                    # Strip removes the trailing newline character for cleaner output
                    matched_lines.append((line_num, line.strip()))
                    
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return []

    return matched_lines

def text_between(file_path, start_string, end_string):
    lines_list = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line_num, line in enumerate(file):
            if line_num > end_string :
                break
            elif line_num >= start_string:
                lines_list.append(line)
    return lines_list



if __name__ == "__main__":
    path_test = "/Users/alexandreviolleau/Documents/Code/Data-Analysis-Project/alex/sec-edgar-filings/0000789019/10-K/0000950170-23-035122/full-submission.txt"
    target_string_1 = "Discussion and Analysis of Financial Condition and Results of Operations"
    target_string_2 = "Economic Conditions, Challenges, and Risks"
    results_1 = find_string_in_file(path_test, target_string_1)
    results_2 = find_string_in_file(path_test, target_string_2)

    obtained = text_between(path_test, results_1[-1][0], results_2[-1][0])
    
# %%
