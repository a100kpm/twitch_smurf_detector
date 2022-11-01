from variables import *
from utility import *

import sqlalchemy
from sqlalchemy.pool import NullPool   
import datetime 
import time as time_
import requests
import json
import pandas as pd
import urllib3
urllib3.disable_warnings()

                         
def connection2(database_entry):
    '''
    Parameters
    ----------
    database_entry : information to connect to database

    Returns
    -------
    conn : connector to database
    engine : engine to database

    '''
    engine=sqlalchemy.create_engine(database_entry,poolclass=NullPool)
    conn=engine.connect()
    return conn,engine

def update_player(df_player):
    '''
    Parameters
    ----------
    df_player : dataframe to upsert into database-> table player

    Returns
    -------
    None.

    '''
    conn,engine=connection2(database_entry)
    df_player.to_sql('player_copy',conn,if_exists='replace',index=False)
                              
    conn.execute("""
                 INSERT INTO player
                 SELECT *
                 FROM player_copy
                 ON CONFLICT ON CONSTRAINT player_un 
                 DO UPDATE
                 SET possible_steam_id=EXCLUDED.possible_steam_id,
                 possible_smurf_id=EXCLUDED.possible_smurf_id,
                 possible_smurf_game_id=EXCLUDED.possible_smurf_game_id
                """)
    conn.close()
            
def update_stream(df):      
    '''
    Parameters
    ----------
    df : dataframe to upsert into database -> table stream

    Returns
    -------
    None.

    '''                           
    conn,engine=connection2(database_entry)                          
    df.to_sql('stream_copy', conn, if_exists='replace', index = False)  
                              
    conn.execute("""
                 INSERT INTO stream
                 SELECT *
                 FROM stream_copy
                 ON CONFLICT ON CONSTRAINT stream_un 
                 DO UPDATE
                 SET processed=EXCLUDED.processed,game_id=EXCLUDED.game_id,player_id=EXCLUDED.player_id
                """)
    conn.close()

def processed_cleaner(days=10):
    '''
    Parameters
    ----------
    days : how many day in the past we clean data to allow a new reprocessing
    
    Returns
    -------
    None.

    '''
    time=datetime.datetime.now()-datetime.timedelta(days=days)
    conn,engine=connection2(database_entry)
    df=pd.read_sql_query(f"select * from stream where play=True and processed=True and game_id='' and time>'{time}'",conn)
    if len(df)==0:
        conn.close()
        return
    df['game_id']='-1'
    df['player_id']='-1'
    df['processed']=False
    
    df.to_sql('stream_copy2', conn, if_exists='replace', index = False)
    
    conn.execute("""
                 INSERT INTO stream
                 SELECT *
                 FROM stream_copy2
                 ON CONFLICT ON CONSTRAINT stream_un 
                 DO UPDATE
                 SET processed=EXCLUDED.processed,game_id=EXCLUDED.game_id,player_id=EXCLUDED.player_id
                """)
    conn.close()
    
def combine_game_hero(game_hero1,pos_hero1,game_hero2,pos_hero2):
    '''
    Parameters
    ----------
    game_hero1 : list of up to 10 heroes id in slot order from left to right
    pos_hero1 : list of the up to 10 index position of the heroes
    game_hero2 : list of up to 10 heroes id in slot order from left to right
    pos_hero2 : list of the up to 10 index position of the heroes

    Returns
    -------
    game_hero: list of up to 10 heroes id in slot order from left to right, either game_hero1 if combine==False
    or combination of game_hero1&2 if combine=True
    pos_hero: list of the up to 10 index position of the heroes, either pos_hero1 if combine==False
    or combination of pos_hero1&2 if combine=True
    combine : if combination sucessful -> True else False

    '''
    combine=True
    dico1={y:x for x,y in zip(game_hero1,pos_hero1)}
    dico2={y:x for x,y in zip(game_hero2,pos_hero2)}
    game_hero=[-1]*10
    pos_hero=pos_hero1
    for x in sorted(set(pos_hero1+pos_hero2)):
        if x in dico1 and x in dico2:
            if dico1[x]==dico2[x]:
                game_hero[x]=dico1[x]
            else:
                combine=False
                return game_hero1,pos_hero1,combine
        elif x in dico1:
            game_hero[x]=dico1[x]
        elif x in dico2:
            game_hero[x]=dico2[x]
            pos_hero.append(x)
    pos_hero.sort()
    game_hero=[x for x in game_hero if x!=-1]
    return game_hero,pos_hero,combine
    
def compare_match(game_info,game_hero1,pos_hero1,time):
    game_time=datetime.datetime.fromtimestamp(game_info['start_time'])
    
    if abs(time-game_time)>datetime.timedelta(minutes=360):
        #6 hours margin to match rare duplicate game; long pause + long game should be way shorter than that
        return False
    game_hero=game_info['teama']+game_info['teamb']
    lenn=len(pos_hero1)
    for i in range(lenn):
        pos=pos_hero1[i]
        if game_hero[pos]!=game_hero1[i]:
            return False
        
    return True

def find_player_id(game_id,stratz_token,stratz_url):
    '''
    Parameters
    ----------
    game_id : game_id
    stratz_token : stratz token
    stratz_url : url to connect to stratz servers

    Returns
    -------
    set_player : set of player_id in the game

    '''
    headers = {"Authorization": f"Bearer {stratz_token}"}
    query=f"{{match(id:{game_id}){{players{{steamAccountId}}}}}}"
    req = requests.post(stratz_url, json={"query":query}, headers=headers)
    json_results=json.loads(req.content.decode('utf-8'))['data']['match']['players']
    set_player={int(x['steamAccountId']) for x in json_results}
    return set_player

def get_match(hero_list,pos_list,time_out=10):
    '''
    Parameters
    ----------
    hero_list : list of up to 10 heroes id in slot order from left to right
    pos_list : list of the up to 10 index position of the heroes
    time_out : seconds before timeout the connection

    Returns
    -------
    json_results : all matches info that match with that combination of heroes

    '''
    url='https://api.opendota.com/api/findMatches?'
    teama='&'.join(f'teamA={x}' for x,y in zip(hero_list,pos_list) if y<5)
    teamb='&'.join(f'teamB={x}' for x,y in zip(hero_list,pos_list) if y>=5)
    
    url+=teama+"&"+teamb
    http =urllib3.PoolManager()
    req=http.request('GET',url=url,timeout=time_out)
    json_results=json.loads(req.data.decode('utf-8'))
    return json_results

def process_data(df):
    '''
    Parameters
    ----------
    df : dataframe from database -> table player

    Returns
    -------
    df : dataframe processed

    '''
    lenn=len(df)
    i=0
    while True:
        while i<lenn:
            if df.iloc[i]['play']==True:
                break
            else:
                df.loc[[i],'processed']=True
                i+=1
                
        if i>=lenn:
            break
        lst_indice=[i]
        channel_name=df.iloc[i]['channel_name']
        time=df.iloc[i]['time']
        game_hero1,pos_hero1=get_hero_id(df.iloc[i].game_hero,df.iloc[i].pos_hero)
        combine=True
        i+=1
        while i<lenn:
            if df.iloc[i]['play']==False:
                indices_df=df.iloc[[i]].index
                df.loc[indices_df,'processed']=True
                break
            
            if df.iloc[i]['channel_name']!=channel_name:
                break
            
            time_temp=df.iloc[i]['time']
            if time_temp-time>datetime.timedelta(minutes=19):
                # 19->data taken in windows of 10 min (shorter to longer is 1 to 19 min)
                break   
            
            game_hero2,pos_hero2=get_hero_id(df.iloc[i].game_hero,df.iloc[i].pos_hero)
            game_hero1,pos_hero1,combine=combine_game_hero(game_hero1,pos_hero1,game_hero2,pos_hero2)
            if combine==False:
                break
            
            lst_indice.append(i)  
            time=time_temp
            i+=1
        set_possible_match=set()
        set_player_id=set()
        if len(lst_indice)<=1:
            indices_df=df.iloc[lst_indice].index
            df.loc[indices_df,'processed']=True
            continue#fail check need at least 2 detections in a row to consider the game
        try:
            time_.sleep(1)#needed without a payed key from opendota; else timeout
            game_info=get_match(game_hero1,pos_hero1,20)
            for x in game_info:
                match_match=compare_match(x,game_hero1,pos_hero1,time)
                if match_match==True:
                    set_possible_match.add(x['match_id'])
            for game_id in set_possible_match:
                    players=find_player_id(game_id,stratz_token,stratz_url)
                    set_player_id=set_player_id.union(players)
            game_id_val=':'.join(list(map(str,set_possible_match)))

            indices_df=df.iloc[lst_indice].index
            df.loc[indices_df,'game_id']=game_id_val            
            df.loc[indices_df,'player_id']=':'.join(list(map(str,set_player_id)))
            df.loc[indices_df,'processed']=True

        except:
            pass
    return df


def associate_player_id(database_entry=database_entry,df=False,hours=6):
    '''
    Parameters
    ----------
    database_entry : information to connect to database
    df : dataframe from database -> table stream, if False will look for it automatically
    hours : if df==False how many hours in the recent past are ignore to create df

    Returns
    -------
    None. -> will directly update the tables stream & player in the database

    '''
    
    if not type(df)==pd.core.frame.DataFrame:
        time=datetime.datetime.now()-datetime.timedelta(hours=hours)
        conn,engine=connection2(database_entry)
        df=pd.read_sql_query(f"select * from stream where processed=False and time<'{time}'",conn)
        conn.close()
    else:
        df['time']=pd.to_datetime(df['time'])
    df=df.sort_values(['channel_name','time'])
    df=df.reset_index(drop=True)
    
    df=process_data(df)
    #load table from database (can optimize by loading only channel id in df)
    conn,engine=connection2(database_entry)
    df_player=pd.read_sql_query("select * from player",conn)
    conn.close()
    lenn=len(df)
    for i in range(lenn):
        channel_name,game_id,player_id=df.iloc[i][['channel_name','game_id','player_id']]
        if player_id=='-1' or game_id=='':
            continue
        if not channel_name in df_player['channel_name'].values:
            df_player.loc[len(df_player.index)]=[channel_name,player_id,'','']
            continue

        pos=df_player.index[df_player['channel_name'] ==channel_name].tolist()
        
        set_player_id=set(df_player[df_player['channel_name']==channel_name]['possible_steam_id'].iloc[0].split(':'))
        if game_id in df_player['possible_smurf_game_id'][pos].iloc[0].split(':'):
            continue
        set_player_id_next_game=set(player_id.split(':'))
        set_player_id_temp=set_player_id.intersection(set_player_id_next_game)
        
        if len(set_player_id_temp)==0:
            df_player.loc[pos,'possible_smurf_game_id']+=game_id+':'
            df_player.loc[pos,'possible_smurf_id']+=player_id+':'
            
        else:
            df_player.loc[pos,'possible_steam_id']=':'.join(map(str,set_player_id_temp))
    
    update_stream(df)  
    update_player(df_player)                        
    #update the 2 tables of database
                  

def find_smurf_user(df=False):
    '''
    Returns
    -------
    df : dataframe contaning only twitch_channel with smurfing evidence

    '''
    if not type(df)==pd.core.frame.DataFrame:
        conn,engine=connection2(database_entry)
        df=pd.read_sql_query("select * from player where possible_smurf_id<>''",conn)
        conn.close()
    df['most_probable_smurf_id']=''
    lenn=len(df)
    for i in range(lenn):
        lst_name=df['possible_smurf_id'].iloc[i].split(':')[:-1]
        dico_name=dict()
        for x in lst_name:
            if x not in dico_name:
                dico_name[x]=1
            else:
                dico_name[x]+=1
        max_val=max(dico_name.values(),key=lambda x:int(x))    
        maxkeyarray = [key for key in dico_name if int(dico_name[key]) == max_val]
        if len(maxkeyarray)==1:
        
            df['most_probable_smurf_id'].iloc[i]=maxkeyarray[0]
    return df
    

