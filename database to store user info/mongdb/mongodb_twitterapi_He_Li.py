# Copyright 2018 He Li heli@bu.edu
import pymongo
import pprint
import pprint
import tweepy 
import json
import wget
import os
import io
import shutil
import google.cloud
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageFont as ImageFont
from google.cloud import vision
from google.cloud.vision import types

#Twitter API credentials

consumer_key = "Enter your consumer key"
consumer_secret = "Enter your consumer secret"
access_key = "Enter your access_key"
access_secret = "Enter your access_secret"

def connect_to_mongodb():
    client = pymongo.MongoClient('mongodb://localhost:27017/')
    mydb = client.twittermongodb
    return mydb

def create_tables():
    mydb = connect_to_mongodb()
    collist = mydb.list_collection_names()
    if "images_data" or "tags_data" in collist:
        print("The collection exists.")
        rebuild = input("Do you want to rebuild the tables? y/n ")
        if (rebuild == "y" or rebuild =="Y" or rebuild == "yes"):
            myimage = mydb["images_data"]
            mytag = mydb["tags_data"]
            myimage.drop()
            mytag.drop()
            myimage = mydb["images_data"]
            mytag = mydb["tags_data"]
    
def get_photo_tweets(screen_name):
    
    #Connect to Database
    mydb = connect_to_mongodb()
    myimage = mydb["images_data"]
    
    #based on twitter api sample
    
    #Twitter only allows access to a users most recent 3240 tweets with this method
    #authorize twitter, initialize tweepy
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_key, access_secret)
    api = tweepy.API(auth)
    #initialize a list to hold all the tweepy Tweets
    alltweets = []    
    #make initial request for most recent tweets (200 is the maximum allowed count)
    
    
    new_tweets = api.user_timeline(screen_name = screen_name,count=30)
    #save most recent tweets
    alltweets.extend(new_tweets)
    #save the id of the oldest tweet less one
    oldest = alltweets[-1].id - 1
    
    #keep grabbing tweets until there are no tweets left to grab
    if len(new_tweets) == 0:
        return
    
    while len(new_tweets) > 0:
        #all subsiquent requests use the max_id param to prevent duplicates
        new_tweets = api.user_timeline(screen_name = screen_name,count=10,max_id=oldest)
        #save most recent tweets
        alltweets.extend(new_tweets)
        #update the id of the oldest tweet less one
        oldest = alltweets[-1].id - 1
        if(len(alltweets) > 15):
            break
    
    #save the photo tweets into photos list as url
    photos=[]
    
    #use twitter media object under tweet entities (media array), and the media_url parameter from the media array
    #Based on: https://developer.twitter.com/en/docs/tweets/data-dictionary/overview/entities-object.html#entitiesobject
    #append media_url to the photos list
    for tweet in alltweets:
        tmp = tweet.entities.get('media', [])
        if(len(tmp) > 0):
            photos.append(tmp[0]['media_url'])
    
    #print(photos)
    
    # sql format for images_data
    image_dict = {}
    
    #download photo with urls in the photos list using wget module
    #to the photo_folder
    mypath = os.getcwd()
    mypath = mypath+"/photo_folder"
    if not os.path.isdir(mypath):
        os.makedirs(mypath)
    
    myresult = myimage.find()
    image_id = myresult.count(True)
    
        
    if image_id < 0:
        image_id = 0
    
    images_file = {}
    for photo in photos:
        wget.download(photo, out=mypath)
        for file in os.listdir("photo_folder"):
            if file not in images_file:
                im = file
                images_file[file] = 1
        image_id = image_id + 1
        image_dict = {"_id": image_id, "twitter_user": screen_name, "image_url": photo,"image_name":im}
        myimage.insert_one(image_dict)

    #except:
    #    print("Image data have been recorded.")

    
    
def detect_labels():
    #Connect to Database
    mydb = connect_to_mongodb()
    myimage = mydb["images_data"]
    mytag = mydb["tags_data"]
    
    #load google credentials.json to os environment
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"]= "mystical-axiom-216914-4e58d00e5897.json"
    client = vision.ImageAnnotatorClient()

    
    mypath = os.getcwd()+"/photo_folder"
    imgs = os.listdir(mypath)
    count = 1
    for img in imgs:
        #based on google vision label use sample:
        #https://cloud.google.com/vision/docs/detecting-labels#vision-label-detection-python
        #open the img and add labels of the img
        file_name = os.path.join(mypath, img)
        #'img's path')
        with io.open(file_name, 'rb') as image_file:
            content = image_file.read()
        image = types.Image(content=content)
        response = client.label_detection(image=image)
        labels = response.label_annotations
        
        #add label.description for every label to a description list 
        #and convert to a string(ready to text on img)
        description =[]
        for label in labels:
            description.append(label.description)
        #sep = "\n", change line for every label
        
        
        ##find the last image_id in images_data table
        
        ###
        imagequery = { "image_name": img }

        mydoc = myimage.find(imagequery)
        max_id = 0
        for x in mydoc:
            if x['_id'] > max_id:
                max_id = x['_id']
        
        ###
        
        img_id = max_id
        
        ##tag_id
        
        ###
        myresult = mytag.find()
        t_id = myresult.count(True)
        
        ###
        if t_id < 0:
            t_id = 0
        for tag in description:
            t_id = t_id + 1
            
            tag_dict = {"_id": t_id, "tag_content": tag, "image_id": img_id}
            mytag.insert_one(tag_dict)

        
        string="\n".join(description)
        
        
        #Usign pillow module, draw text on imgs and save them with %d.jpg format
        #pillow sample from pillow draw module tutorial"https://pillow.readthedocs.io/en/3.0.x/reference/ImageDraw.html"
        #define font of the text
        font = ImageFont.truetype('arial.ttf', 50)
        #define position to start drawing text
        (x, y) = (0, 0)
        im = Image.open(file_name).convert('RGB')
        draw = ImageDraw.Draw(im)
        #draw string text on the img, with rgb color (255,255,0,0)
        draw.text((x, y), string, (255,255,0,0), font = font)
        im.save('photo_folder/'+str('%d'%count)+'.jpg', 'JPEG')
        count+=1

def img_to_video():
    
    os.system('ffmpeg -r 1/3 -f image2 -i photo_folder\%d.jpg -s 1200x900 photos.mp4')
    #ffmpeg parameters:
    #-r pics per sec, here is 1 pic per 3 secs
    #-f input format
    #-i input source
    #-s size 1200x900
    #output to a photos.mp4

def show_database(twitter_name, show_db=False):
    if show_db == True or "y" or "Y" or "Yes" or "yes" or "YES":
        mydb = connect_to_mongodb()
        myimage = mydb["images_data"]
        mytag = mydb["tags_data"]
        ## show images_data
        print("Data in images_data Table: "+"\n")
        
        imagequery = { "twitter_user": twitter_name}
        myresult = myimage.find(imagequery)
        image_ids = []
        for result in myresult:
            print(result)
            image_ids.append(result['_id'])

        
        #print(myresult)
        print(image_ids)
        print("Data in tags_data Table: "+"\n")
        for im_id in image_ids:
            
            tagquery = { "image_id": im_id }
            mytagresult = mytag.find(tagquery)
            print("image_id = "+ str(im_id)+"\n")
            for tagres in mytagresult:
                print(tagres)
            print("\n")
            
def search_api():
    search = input("Do you want to search by tag or twitter_user? tag/user ")
    mydb = connect_to_mongodb()
    myimage = mydb["images_data"]
    mytag = mydb["tags_data"]

    if search == "tag":
        tag_name = input("Please input the tag you want to find: ")
        
        ## show images_data

        tagquery = { "tag_content": tag_name }
        mytagresult = mytag.find(tagquery)
        length = mytagresult.count(True)
        if length == 0:
            print("No image with this tag found.")
        else:
            print("\n"+"Images with this tag: "+"\n")
            image_ids = []
            for tagres in mytagresult:
                image_ids.append(tagres['image_id'])
            for image in image_ids:
                imagequery = { "_id": image}
                myresult = myimage.find(imagequery)
                
                for result in myresult:
                    print(result)

    elif search == "user" or "twitter_user" or "User":
        user_name = input("Please input the twitter_user you want to find: ")
        user_name = "@"+user_name
        imagequery = { "twitter_user": user_name}
        myresult = myimage.find(imagequery)
        length =  myresult.count(True)
        if length == 0:
            print("No image of this user found.")
        else:
            print("\n"+"Images of this user: "+"\n")
            for result in myresult:
                print(result)

def show_database_info():
    mydb = connect_to_mongodb()
    myimage = mydb["images_data"]
    mytag = mydb["tags_data"]
    ### For images_data Table:
    #### 1. Number of all images
    myresult = myimage.find()
    image_number = myresult.count(True)
    print(str(image_number)+" images in the images_data Table."+"\n")    

    #### 2. Number of images of every twitter_user
    user_uni = set()
    myresult = myimage.find()

    for result in myresult:
        user_uni.add(result['twitter_user'])
    #print(user_uni)
    for user_name in user_uni:
        imagequery = { "twitter_user": user_name}
        myresult = myimage.find(imagequery)
        length =  myresult.count(True)
        print(str(length)+" images in the images_data Table"+" from "+user_name+".\n") 
    ### For tags_data Table:
    #### 1. Number of all tags
    myresult = mytag.find()
    tag_number = myresult.count(True)
    print(str(tag_number)+" tags in the tags_data Table."+"\n")    

    #### 2. The most frequent tags

    max_frequent_tag = {}

    for result in myresult:
        max_frequent_tag[result['tag_content']] = max_frequent_tag.get(result['tag_content'], 0) + 1
    #print(max_frequent_tag)
    tags_sorted=sorted(max_frequent_tag.items(), key=lambda x: x[1], reverse=True)
    print("The most frequent tag is: " + tags_sorted[0][0]+". It is on "+str(tags_sorted[0][1])+" images.")
            

if __name__ == '__main__':
    #get photos from twitter account with twitter api
    
    create_tables()
    twitter_name = input("Please input the twitter name: ")
    
    twitter_name = "@"+twitter_name
    try:
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_key, access_secret)
        api = tweepy.API(auth)
        api.get_user(screen_name=twitter_name)
        if "photo_folder" in os.listdir():
            shutil.rmtree("photo_folder")
        get_photo_tweets(twitter_name)
        try:

            detect_labels()
            if 'photos.mp4' in os.listdir():
                os.remove("photos.mp4")
            img_to_video()
            os.system('photos.mp4')
            print("\n")
            show_db=input("Do you want to show database of this twitter user? y/n ")
            show_database(twitter_name, show_db)
            search_api()
            show_database_info()
            
        except:
            print("No image tweets found or has error.")

    except:
        print("User Not Found or has error.")
    
    