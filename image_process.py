from variables import *
from utility import *

import numpy as np
from scipy.ndimage import label
from PIL import Image


# def find_hero_in_image(img,template_path=r'C:\Users\iannis\Desktop\twitch smurf detector\image_template',method=cv2.TM_CCOEFF_NORMED):
def find_hero_in_image(img,template_path=template_path,method=cv2.TM_CCOEFF_NORMED):    
    '''
    Parameters
    ----------
    img : image in gray scale preprocessed by crop_image_and_cvarray()
    template_path : path to the gray scale template of all heroes's image
    method : cv2 template method should be optimal

    Returns
    -------
    hero_image : ordered list of heroes in the image
    score_image : ordered score of heroes potentially being in the image
    position_image : ordered list of position for heroes in the image
    
    '''
    f=os.listdir(template_path)
    lst_hero=[]
    lst_score=[]
    lst_point=[]
    for file in f:
        template=cv2.imread(template_path+'\\'+file)
        template=template[:,:,0]
        lst_hero.append(file)
        result = cv2.matchTemplate(img, template, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            point = min_loc
            score = 0 - min_val
        else:
            point = max_loc
            score = max_val
            
        lst_score.append(score)
        lst_point.append(point)
        
    order=np.argsort(lst_score)
    hero_image=[lst_hero[i] for i in order]
    score_image=[lst_score[i] for i in order]
    position_image=[lst_point[i] for i in order]
    return hero_image,score_image,position_image


def crop_image_and_cvarray(img,x_crop_val=0.8,y_crop_val=84,black_n_white=True):
    '''
    #part of the code of this function is from the reddit dota bot
    Parameters
    ----------
    img : image to work on
    x_crop_val : float between 0-1: % of the image to remove
    y_crop_val : 
    black_n_white : return gray scale image if True

    Returns
    -------
    img : cropped img

    '''
    game_image=Image.fromarray(img)
    image_ratio = game_image.size[1] / 1920

    # yes, calculating this relative to the height
    herobar_width = x_crop_val * game_image.size[1]
    herobar_margin = (game_image.size[0] - herobar_width) // 2

    # added this logic because sometimes theres a black border at the top of the image
    top_margin = -1
    margin_samples = 20
    brightness_threshold = 30
    done_finding_margin = False
    max_remove=200
    while not done_finding_margin and max_remove>0:
        max_remove-=1
        top_margin += 1
        for i in range(margin_samples):
            pixel = game_image.getpixel((int(i * (game_image.width / margin_samples)), top_margin))
            brightness = pixel[0] + pixel[1] + pixel[2]
            if brightness > brightness_threshold:
                done_finding_margin = True
                break

    game_image = game_image.crop((herobar_margin, top_margin, game_image.size[0] - herobar_margin, top_margin + int(y_crop_val * image_ratio)))
    if black_n_white==True:
        img = cv2.cvtColor(np.asarray(game_image), cv2.COLOR_RGB2GRAY)
        return img
    return np.asarray(game_image)

def valid_pos(x_hero_positions,y_hero_positions,threshold_position_x,threshold_position_y,x,y):
    '''
    Parameters
    ----------
    x_hero_positions : list containing the 10 normal x position of heroes
    y_hero_positions : value of the normal y position of heroes
    threshold_position_x : threshold distance for acceptable distance from x_hero_positions
    threshold_position_y : threshold distance for acceptable distance from y_hero_positions
    x : x coordinate to compare to normal value
    y : y coordinate to compare to normal value

    Returns
    -------
    bool : True if coordinate are acceptable
    index_ : -1 if bool==False, index value between 0-9 depending on which slot of heroes 
    the x,y coordinate are closest to

    '''
    if y<y_hero_positions-threshold_position_y or y>y_hero_positions+threshold_position_y:
        return False,-1
    pos_index=[abs(pos-x) for pos in x_hero_positions]
    min_=min(pos_index)
    index_=pos_index.index(min_)
    pos=x_hero_positions[index_]
    if x<pos-threshold_position_x or x>pos+threshold_position_x:
        return False,-1
    return True,index_

def choose_hero(x_hero_positions,y_hero_positions,name_dictionary,
                name_hero_ordered,score_hero_ordered,position_hero_ordered,
                threshold_position_x=7,threshold_position_y=3,threshold_confidence=0.65
                ):
    '''
    Parameters
    ----------
    x_hero_positions : list containing the 10 normal x position of heroes
    y_hero_positions : value of the normal y position of heroes
    name_dictionary : dictionary containing the association image name<->name for all heroes
    name_hero_ordered : ordered list of heroes in the image
    score_hero_ordered : ordered score of heroes potentially being in the image
    position_hero_ordered : ordered list of position for heroes in the image
    threshold_position_x : threshold distance for acceptable distance from x_hero_positions
    threshold_position_y : threshold distance for acceptable distance from y_hero_positions
    threshold_confidence : threshold value for acceptable template match on image

    Returns
    -------
    list of acceptable detection of heroes ordered by position from left to right, str if nothing found
    list of index position ordered by position from left to right, str if nothing found
    lenn : number of positive detection

    '''
    name_choose=[]
    pos_choose=[]
    i=len(name_hero_ordered)
    while len(name_choose)<10 and i>0:
        i-=1
        confidence=score_hero_ordered[i]
        if confidence<threshold_confidence:
            break
        
        x,y=position_hero_ordered[i]
        valid,index_=valid_pos(x_hero_positions,y_hero_positions,threshold_position_x,threshold_position_y,x,y)
        if not valid:
            continue
        
        name=name_dictionary[name_hero_ordered[i]]
        if name in name_choose:
            continue
        
        if index_ in pos_choose:
            continue
        name_choose.append(name)
        pos_choose.append(index_)
        order=np.argsort(pos_choose)
    lenn=len(name_choose)
    if lenn>0:
        return [name_choose[i] for i in order],[pos_choose[i] for i in order],lenn
    return "nothing_found","nothing_found",lenn

def ignore_replay(image,threshold=threshold_play_watch):
    '''
    Parameters
    ----------
    image : image to work on
    threshold : threshold value to discriminate between watch or play

    Returns
    -------
    bool : True if watching, False if playing
    x_hero_positions : list containing the 10 x position of heroes
    
    '''
    global x_hero_positions
    val_crop=100
    image=cv2.filter2D(image,-1,np.array([[ -1, -1, -1], 
                       [ -1, 8, -1], 
                       [ -1, -1, -1]]))
    
    image=crop_image_and_cvarray(image,y_crop_val=val_crop)
    image=image[-15:,:]
    image[image>30]=255
    image[image<=128]=0
    kernel = np.ones((3,3),np.uint8)
    opening = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
    op_left=opening[:,:432]
    op_right=opening[:,432:]
    val1=np.sum(op_left)
    val2=np.sum(op_right)
    
    # use alternate_estimate_x_hero_positions() here if you want to catch more game
    # or x_hero_positions_alternate 1or2 if you preprocessed them
    # base value capture a vast majority of game already
    # to do get approximate pos for x_hero_pos abd y_hero_pos
    
    if val1 <threshold_play_watch or val2<threshold_play_watch:
        return False,x_hero_positions

    return True,x_hero_positions

def search_x_exit(img,x_exit,threshold=0.5,base_loc=(10,10),distance_threshold=13):
    '''
    Parameters
    ----------
    img : image to work on
    x_exit : image containing the X_exit
    threshold : threshold value to get an acceptable detection
    base_loc : normal position of the X to find
    distance_threshold : threshold distance value to the normal position

    Returns
    -------
    bool : True if watching (X present), False if playing

    '''
    x_exit=x_exit[10:-10,10:-10]
    val=0
    loc=(50,50)
    try:
        im=img[:50,-50:,:] #exit X might be at a slightly different place with weird resolution from streamer
        imgray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        
        ret, thresh = cv2.threshold(imgray, 127, 255, 0)
        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        imgray=cv2.drawContours(imgray, contours, -1, 255, 3)
        imgray[imgray<255]=0
        labeled_array, num_features = label(imgray)
        unique, counts = np.unique(labeled_array, return_counts=True)
        unique=unique[1:]
        counts=counts[1:]
        idx=np.argmax(counts)
        elem=unique[idx]
        labeled_array[labeled_array!=elem]=0
        labeled_array[labeled_array==elem]=1
        
        method=cv2.TM_CCOEFF_NORMED
        result = cv2.matchTemplate(imgray, x_exit, method)
        _, val, _, loc = cv2.minMaxLoc(result)
    except:
        pass
    if (( (loc[0] - base_loc[0])**2 + (loc[1] - base_loc[1])**2 )<=distance_threshold) and (val>threshold):
        return True

    return False
