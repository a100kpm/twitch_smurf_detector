import os
import pandas as pd
import cv2
import csv

def find_function(name=None):
    '''
    Parameters
    ----------
    name : name of the function to search; if left as None, will search for all function in directory

    Returns
    -------
    output position of function in directory

    '''
    if name==None:
        for filename in os.listdir(os.getcwd()):
            if filename[-3:]=='.py':
                with open(os.path.join(os.getcwd(), filename), 'r') as f:
                    line_number=0
                    for line in f:
                        line_number+=1
                        if line[0:4]=='def ':
                            print(filename,'at line',line_number,' -->',line.split('(')[0][4:]+'()')

    else:
        for filename in os.listdir(os.getcwd()):
            if filename[-3:]=='.py':
                with open(os.path.join(os.getcwd(), filename), 'r') as f:
                    line_number=0
                    for line in f:
                        line_number+=1
                        if line[0:4]=='def ':
                            if name in line.split('(')[0][4:]:
                                print(f'function "{name}" is located in',filename,'at line',line_number,' -->',line[4:-2],'\n')
                                
    
def load_x_exit(path='label.png'):
    '''
    Parameters
    ----------
    path : path to the file containing the X_exit generated from create_x_exit()

    Returns
    -------
    x_exit : image of the x_exit

    '''
    x_exit=cv2.imread(path)
    x_exit=x_exit[:,:,0]
    return x_exit                            

def load_hero_id_dictionary(path='hero_id_dictionary.csv'):
    '''
    Parameters
    ----------
    path : path to the file hero_id_dictionary.csv

    Returns
    -------
    dico : dictionary containing the association name<->id for all heroes
    
    '''
    hero=pd.read_csv(path)
    dico=dict()
    for x in hero.iterrows():
        val=x[1]
        dico[val.hero_name]=val.hero_id
    return dico                                


def load_name_dictionary(path='name_dictionary.csv'):
    '''
    Parameters
    ----------
    path : path to the file name_hero_dictionary.csv
    
    Returns
    -------
    name_dictionary : dictionary containing the association image name<->name for all heroes

    '''
    with open(path, mode='r') as infile:
        reader = csv.reader(infile)
        name_dictionary = {rows[0]:rows[1] for rows in reader}
    return name_dictionary

hero_id_dictionary=load_hero_id_dictionary()
name_dictionary=load_name_dictionary()

def get_hero_id(game_hero,pos_hero,hero_id_dictionary=hero_id_dictionary):
    '''
    Parameters
    ----------
    game_hero : str containing up to 10 heroes name
    pos_hero : str containing the slot position of game_hero
    hero_id_dictionary : dictionary containing the association name<->id for all heroes

    Returns
    -------
    game_hero : list containing up to 10 heroes id
    pos_hero : list containing the slot position of game_hero

    '''
    if not type(game_hero)==list:
        game_hero=game_hero[1:-1].replace("'","").replace(" ","").split(',')
    if not type(pos_hero)==list:   
        pos_hero=list(map(int,pos_hero[1:-1].split(",")))
        
    game_hero=[hero_id_dictionary[x] for x in game_hero]
    return game_hero,pos_hero
