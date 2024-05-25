import os
import shutil
import yaml


def request_settings(): 
    """
    Returns: 
    settings (dict)
    dir: path to directory where the output will be saved
    """
    dir = None
    #Creating a directory for the output 
    while True: 
        dir = input("Please enter a name for the output directory: ")
        #Checking path
        if not os.path.exists(dir): 
            os.makedirs(dir)
            os.makedirs(os.path.join(dir, 'html_files'))
            print(f'All data of this run saved under {os.path.abspath(dir)}\n')
            break
        else: 
            overwrite = input("Folder already exists, enter 'y' if you want to overwrite all content: ")
            if overwrite.strip() == 'y':
                shutil.rmtree(dir)
                os.makedirs(dir)#exist_ok=True
                os.makedirs(os.path.join(dir, 'html_files'))
                print(f'All data of this run saved under {os.path.abspath(dir)}\n')
                break

    #Loading settings
    shutil.copyfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings_template.yaml'), f'{os.path.abspath(dir)}/settings.yaml')
    while True:
        continue_check = input("A settings file was created in the directory, please modify it if you want to change the settings. \nEnter 'c' to continue: ")
        if continue_check.strip() == 'c': 
            break

    return dir

def read_settings_file(dir): 
    settings_path = os.path.join(dir, 'settings.yaml')
    with open(settings_path, 'r') as file:
        settings = yaml.safe_load(file)

    return settings

def request_starting_page(): 
    starting_page = input("Please enter a starting page: ")
    return starting_page