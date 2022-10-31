# # stratz
stratz_url = "https://api.stratz.com/graphql" # note the url is 'graphql' and not 'graphiql'
stratz_token = "e***************" #get your own key at https://stratz.com/api

# # twitch
twitch_url = "https://api.twitch.tv/helix/streams"
twitch_autURL ="https://id.twitch.tv/oauth2/token"
twitch_clientID = "c******************************" #get your own credidential at https://dev.twitch.tv/docs/api/
twitch_secret = "b********************************" # get your own credidential at https://dev.twitch.tv/docs/api/
twitch_stream_url = "https://api.twitch.tv/helix/streams"
twitch_dota2_id ='29595'

# # database
# database_entry='postgresql://database_username:password@localhost/database_name'
database_entry='postgresql://database_username:password@192.168.1.72/database_name'
import psycopg2#used when not @localhost for database
'''
the database contain two table, stream and player (+2 temp table that will get created automatically for upsert)
stream ->"channel_name":text,"game_hero":text,"pos_hero":text,"play":bool,"time":timestamp,"processed":bool,"game_id":text,"player_id":text
player ->"channel_name":text,"possible_steam_id":text,"possible_smurf_id":text,"possible_smurf_game_id":text
'''

# # working directory
save_directory=r"C:\Users\username\Desktop\twitch smurf detector\image" 
template_path=r'C:\Users\username\Desktop\twitch smurf detector\image_template' 
#choose where ever you want to, but for minimal effort, dumb all .py file in twitch smurf detector
# and make those two having the same ending as here

# # image detection value
width=1920
height=1080
x_hero_positions=[20.62,82.67,144.12,205.36,268.81,538.69,600.86,662.98,724.93,787.0]
# x_hero_positions_alternate1=[] #just make custom value for the 2 very rare cases of larger or narrower resolution
# x_hero_positions_alternate2=[] # or complete estimate_x_hero_positions to automatize it
#                               # and add it inside ignore_replay
y_hero_positions=8
val_min=[37740, 120360]#under that value might be play; obtained with estimate_threshold_watch_play()
val_max=[22185, 124185]#above that value might be watch; obtained with estimate_threshold_watch_play()
threshold_play_watch=val_min[0] #risk to get too many "watch" detection, but at least no/lot less "play" false detection
path_label=r'C:\Users\username\Desktop\twitch smurf detector\label.png'











