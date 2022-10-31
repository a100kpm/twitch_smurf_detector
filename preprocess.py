import os
import requests
from PIL import Image
import numpy as np
import cv2
import matplotlib.pyplot as plt

# http://dotabase.dillerm.io/dota-vpk/panorama
def get_hero_path_from_dotabase():
    #get path to download hero image from dotabase
    req=requests.get("http://dotabase.dillerm.io/dota-vpk/?dir=panorama/images/heroes/")
    content=req._content.decode('utf-8')
    content=content.split('thumb">')
    lst_path=[]
    for x in content:
        if x[:14]=='npc_dota_hero_':
            val=x.split('</a>')[0]
            lst_path.append(val)
    return lst_path

def save_content(filename, data):
    #save image into filename
	file_dir = os.path.dirname(filename)
	if not os.path.exists(file_dir):
		os.makedirs(file_dir)
	with open(filename, "wb+") as f:
		f.write(data)
        
def save_hero_png(lst_path,save_directory):
    #download image of hero from dotabase
    base_path="http://dotabase.dillerm.io/dota-vpk/panorama/images/heroes/"
    for hero in lst_path:
        path=base_path+hero
        r=requests.get(path)
        local_file=save_directory+'\\'+hero[14:]
        save_content(local_file, r.content)
   
def get_template(save_directory,width=128):
    #load image in directory and process them into template
    f=os.listdir(save_directory)
    for file in f:
        height = round(0.5625 * width)
        image = Image.open(save_directory+'\\'+file).convert("RGB")
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        modifier = width / 128
# crop to not include the edges or the bottom section where dota plus icons show up
        image = image.crop((
   		round(8 * modifier),
   		round(8 * modifier),
   		image.size[0] - round(8 * modifier),
   		image.size[1] - round(32 * modifier)
           ))
        image=cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
        scale_percent = 50 # percent of original size
        w= int(image.shape[1] * scale_percent / 100)
        h = int(image.shape[0] * scale_percent / 100)
        dim = (w,h)
            
        image=cv2.resize(image,dim,interpolation = cv2.INTER_AREA)
        cv2.imwrite(save_directory+'_template\\'+file,image)
        
def create_name_dictionary(hero_image):
    #create a dictionary which link hero_image to the hero name
    name_dictionary=dict()
    for x in hero_image:
        name=x[:-8]
        if 'alt'==name.split('_')[-1][:3]:
            lenn=len(name.split('_')[-1])
            name=name[:-lenn-1]
        if 'persona'==name.split('_')[-1][:7]:
            lenn=len(name.split('_')[-1])
            name=name[:-lenn-1]
        name_dictionary[x]=name
    return name_dictionary

def save_dictionary(dictionary,path='name_dictionary.csv'):   
    #save a dictionary into a csv file
    with open(path, 'w') as f:
        for key in dictionary.keys():
            f.write("%s,%s\n" % (key,dictionary[key]))
            
def create_x_exit():
    #create the X_exit template image
    from scipy.ndimage import label
    lst_name=['test.png','test2.png','test3.png']#get your own image with a "x" on the top right
    lst_label=[]
    for name_img in lst_name:
    # name_img='test.png'
        image=cv2.imread(name_img,-1)
        im=image[:50,-50:,:]
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
        plt.imshow(labeled_array, cmap='gray')
        plt.show()
        lst_label.append(labeled_array)
    

    label1=lst_label[0]
    label2=lst_label[1]
    label3=lst_label[2]

    label = cv2.bitwise_and(label1,label2)
    label= cv2.bitwise_and(label,label3)
    plt.imshow(label,cmap='gray')
    cv2.imwrite('label.png',label)

def estimate_x_hero_positions(stack_img,lenn):
    #estimate the x hero_position to fill the x_hero_positions in variables
    #manual test !!!
    div=0
    x_hero_positions=[0,0,0,0,0,0,0,0,0,0]
    for i in range(lenn):
        img=cv2.imdecode(stack_img[i],-1)
        img=crop_image_and_cvarray(img)
    
        a,b,c=find_hero_in_image(img)
        print(a[-10:],c[-10:])
        cv2.imshow('img',img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        inputt=input()
        if inputt=='1':
            cc=[z[0] for z in c[-10:]]
            cc.sort()
            x_hero_positions=[x + y for x, y in zip(x_hero_positions, cc)]
            div+=1
        print(div)
    return x_hero_positions,div

def estimate_threshold_watch_play(stack_img):
    #estimate the threshold value between watched and played game
    #manual test !!!
    val_min=[148410,148410] #under that value might be play
    val_max=[4080,4080] #above that value might be watch
    #obtained value->120360/63240
    lenn=len(stack_img)
    for i in range(lenn):
        image=cv2.imdecode(stack_img[i],-1)
        img=image.copy()
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
        cv2.imshow('a',img[:500,:,:])
        cv2.imshow('b',opening)
        cv2.moveWindow('a', 200,0)
        cv2.moveWindow('b', 40,300)
        op_left=opening[:,:432]
        op_right=opening[:,432:]
        val1=np.sum(op_left)
        val2=np.sum(op_right)
        print(val1,val2,'i=',i)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        dd=input()
        if dd=='1':
            val_min[0]=min(val_min[0],min(val1,val2))#watch
            val_min[1]=min(val_min[1],max(val1,val2))
        elif dd=='2':
            val_max[0]=max(val_max[0],min(val1,val2))
            val_max[1]=max(val_max[1],max(val1,val2))#play
        #cut image in half and do the job from there
    return val_min,val_max




#bellow is for a bulk idea of how to proceed to improve detection quality;
#--> estimate position of each hero image on sceen by searching top bar color position
def get_ratio_color(im):
    #get ratio of color for each color bar of heroes
    a=im[:,:,0]/im[:,:,1]
    b=im[:,:,0]/im[:,:,2]
    c=im[:,:,1]/im[:,:,2]
    test=np.array([a,b,c],ndmin=3)
    ratio_1_min=np.min(test[0,1:3,:])
    ratio_1_max=np.max(test[0,1:3,:])
    ratio_2_min=np.min(test[1,1:3,:])
    ratio_2_max=np.max(test[1,1:3,:])
    ratio_3_min=np.min(test[2,1:3,:])
    ratio_3_max=np.max(test[2,1:3,:])
    return (ratio_1_min,ratio_1_max,ratio_2_min,ratio_2_max,ratio_3_min,ratio_3_max)

# r=get_ratio_color(im)

def change(image,r):
    #keep only the part of image in between ratio
    img=np.zeros([56,864,3])
    img[(
        ((image[:,:,0] >= image[:,:,1]*r[0]) & (image[:,:,0] <= image[:,:,1]*r[1]) ) &
        ((image[:,:,0] >= image[:,:,2]*r[2]) & (image[:,:,0] <= image[:,:,2]*r[3]) ) &
        ((image[:,:,1] >= image[:,:,2]*r[4]) & (image[:,:,1] <= image[:,:,2]*r[5]) )
                  )]=255
    return img

def alternate_estimate_x_hero_positions(stack_img):
    # try to get the alternate x hero positions for resolution way larger and way narrower than "normal" ones
    # not needed for big majority of cases
    # need completion
    dico_ratio_color=load_dictionary_ratio_color()
    lenn=len(stacl_img)
    for i in range(lenn):
        image=cv2.imdecode(stack_img[i],-1)
        testt=image.copy()
        val_crop=100
        testt=crop_image_and_cvarray(testt,y_crop_val=val_crop,black_n_white=False)
        list_x=[]
        list_y=[]
        game_image=crop_image_and_cvarray(image)
        name_hero_ordered,score_hero_ordered,position_hero_ordered=find_hero_in_image(game_image)
        name_choose,pos_choose,nbr_hero=choose_hero(x_hero_positions,y_hero_positions,name_dictionary,
                        name_hero_ordered,score_hero_ordered,position_hero_ordered,
                        )
        if nbr_hero<=6:
            continue
        for x in dico_ratio_color:
            if x!=3 and x!=9:
                aa=change(testt,dico_ratio_color[x])
                bb=aa[1:3,:,:]
                bb=bb[:,:,0]
                M = cv2.moments(bb)
                cX = M["m10"] / M["m00"]
                cY = M["m01"] / M["m00"]
                list_x.append(cX)
                list_y.append(cY)
            
    
        print(i,list_x)
        print(name_choose)
        cv2.imshow('a',testt)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        input()
    #to complete for rare case         
