from image_process import *
from process_data import *
# import urllib3
# urllib3.disable_warnings()


def get_twitch_data(game="Dota 2",request_string_log=twitch_autURL,ClientId=twitch_clientID,Secret=twitch_secret,
                                    Url=twitch_stream_url,nbr=100,viewer_count=1000):#keep viewer_count very high to take only 1 page
# twitch doesn't like that much the fetch of image later on; so it is "no ddos" friendly
#   viewer_count isn't a hard limit; if lowest viewer count from last batch is lower than viewer_count
#   then no more batch of stream will be searched
    '''
    Parameters
    ----------
    game : game name (only "Dota 2" is treated here, but we can manually input dota 2's game id for twitch instead)
    request_string_log : needed to make api request with twitch
    ClientId : needed to make api request with twitch
    Secret : needed to make api request with twitch
    Url : needed to make api request with twitch
    nbr : how many channel we gather at once
    viewer_count : if lowest value of viewer in data collected < viewer_count then stop collecting data

    Returns
    -------
    general information about all streamers on twitch with game = game

    '''
    if type(game)==str:
        if game=="Dota 2": #modify here to add new game
            global twitch_dota2_id
            game=twitch_dota2_id
              
    Url+='?game_id='+game+'&first='+str(nbr)
    http =urllib3.PoolManager()
    AutParams = {'client_id': ClientId, 'client_secret': Secret, 'grant_type': 'client_credentials'}
    
    req=http.request('POST',request_string_log,fields=AutParams)
    json_result=json.loads(req.data.decode('utf-8'))
    access_token = json_result['access_token']
    Headers = {'Client-ID': ClientId, 'Authorization': "Bearer " + access_token}    

    req = http.request('GET',url=Url, headers=Headers)
    json_results=json.loads(req.data.decode('utf-8'))
    
    size_temp=len(json_results['data'])
    viewer=json_results['data'][-1]['viewer_count']
    pagination=[]
    if viewer>viewer_count:
        try:
            pagination=json_results['pagination']['cursor']
        except:
            pass
    while pagination:
        Url+='?game_id='+game+'&first='+str(nbr)+'&after='+pagination        
        req=http.request('POST',request_string_log,fields=AutParams)
        
        req = http.request('GET',url=Url, headers=Headers)
        json_results2=json.loads(req.data.decode('utf-8'))
        json_results['data'].extend(json_results2['data'])
        pagination=[]
        viewer=json_results2['data'][-1]['viewer_count']
        if viewer>viewer_count:
            try:
                pagination=json_results2['pagination']['cursor']
            except:
                pass
            
    return json_results['data']

def get_url(width=1920,height=1080):
    '''
    Parameters
    ----------
    width : width of the image we want to get
    height : height of the image we want to get

    Returns
    -------
    stack_url : list of the url to the thumbnails of image of each streamers
    stack_name : list of channel name of each streamers

    '''
    stack_url=[];stack_name=[]
    twitch_data=get_twitch_data()
    for data in twitch_data:
        name=data['user_login']
        url=data['thumbnail_url'][:-20]+f"{width}x{height}.jpg"
        stack_url.append(url)
        stack_name.append(name)
    return stack_url,stack_name

def get_img_from_url(stack_url,delay=4):
    '''
    Parameters
    ----------
    stack_url : list of the url to the thumbnails of image of each streamers
    delay : second between 2 requests to twitch (avoid being thought as a ddos attempt by the server)

    Returns
    -------
    stack_img : list of all image from stack_url
    stack_time : list of the time at which each image has been captured

    '''
    stack_img=[];stack_time=[]
    for x in stack_url:
        time_.sleep(delay)#so twitch is happy and doesn't kick our connection
        url=x
        response = requests.get(url)
        arr=np.asarray(bytearray(response.content), dtype=np.uint8)
        stack_img.append(arr)
        stack_time.append(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    return stack_img,stack_time


def collect_data(threshold_nbr_hero=7,path_label=path_label): #lower threshold and cross validation later ?
    '''
    Parameters
    ----------
    threshold_nbr_hero : min number of heroes to be detected on image to consider it a valid detection
    path_label : path to x_exit template

    Returns
    -------
    None. -> will directly update the table stream in the database

    '''
    x_exit=load_x_exit(path=path_label)
    while True:
        
        time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M") #we can consider fixing a timezone for long run
        minute_=int(time[-2:])
        
        if minute_%10==0:
            print(time)
            df=pd.DataFrame(columns=['channel_name','game_hero','pos_hero','play','time','processed','game_id','player_id'])
            stack_url,stack_name=get_url()
            stack_img,stack_time=get_img_from_url(stack_url,delay=4)
            lenn=len(stack_img)
            for i in range(lenn):
                game_image=cv2.imdecode(stack_img[i],-1)
                img=game_image.copy()
                ignore,x_hero_position_temp=ignore_replay(img)
                img=game_image.copy()
                ignore2=search_x_exit(img,x_exit)

                if ignore or ignore2:
                    play=False
                else:
                    
                    play=True
                game_image=crop_image_and_cvarray(game_image)
                name_hero_ordered,score_hero_ordered,position_hero_ordered=find_hero_in_image(game_image)
                
                name_choose,pos_choose,nbr_hero=choose_hero(x_hero_positions,y_hero_positions,name_dictionary,
                                name_hero_ordered,score_hero_ordered,position_hero_ordered,
                                )
                if nbr_hero<threshold_nbr_hero:
                    continue
                df.loc[len(df)]=[stack_name[i],name_choose,pos_choose,play,stack_time[i],False,"-1","-1"]
            conn,engine=connection2(database_entry)
            df.to_sql('stream',conn,if_exists='append',index=False)
            conn.close()
            # send_data_to_database(df,data_base_name)
        else:
            for i in range(30):
                time_.sleep(1)
                




