# Copyright 2018 He Li heli@bu.edu

import mysql.connector
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


username=input("Please input your mysql username: ")
password =input("Please input your mysql password: ")


def connect_to_mysql():
    mydb = mysql.connector.connect(
        host="localhost",
        user=username,
        passwd=password,
        database="twitterdb"
    )
    return mydb

def create_tables():
    sql_table_images = "CREATE TABLE images_data (image_id varchar(30) NOT NULL, twitter_user varchar(255) NOT NULL, image_url varchar(255) NOT NULL, image_name varchar(255) NOT NULL, PRIMARY KEY (image_id),  UNIQUE (image_id))"
    sql_table_tags = "CREATE TABLE tags_data (tag_id varchar(30) NOT NULL, tag_content varchar(30) NOT NULL, image_id varchar(30) NOT NULL, PRIMARY KEY (tag_id), FOREIGN KEY (image_id) REFERENCES images_data(image_id), UNIQUE (tag_id))"
    mydb = connect_to_mysql()
    mycursor = mydb.cursor(buffered=True)
    
    mycursor.execute("SHOW TABLES")
    myresult = mycursor.fetchall()
    for result in myresult:
        if result[0] == "images_data" or "tags_data":
            print("Tables already exist!")
            rebuild = input("Do you want to rebuild the tables? y/n ")
            if (rebuild == "y" or rebuild =="Y" or rebuild == "yes"):
                mycursor.execute("DROP TABLE tags_data")
                mycursor.execute("DROP TABLE images_data")
                break
            else:
                return
           

    mycursor.execute(sql_table_images)
    mycursor.execute(sql_table_tags)
    
    mycursor.execute("DESC images_data")
    myresult = mycursor.fetchall()
    print("image_data table structure:")
    for result in myresult:
        print(result)


    mycursor.execute("DESC tags_data")
    myresult = mycursor.fetchall()
    print("tags_data table structure:")
    for result in myresult:
        print(result)

def get_photo_tweets(screen_name):
    
    #Connect to Database
    mydb = connect_to_mysql()
    mycursor = mydb.cursor(buffered=True)
    
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
    sql_image = "INSERT INTO images_data (image_id, twitter_user, image_url, image_name) VALUES (%s, %s, %s, %s)"
    
    
    #download photo with urls in the photos list using wget module
    #to the photo_folder
    mypath = os.getcwd()
    mypath = mypath+"/photo_folder"
    if not os.path.isdir(mypath):
        os.makedirs(mypath)
    #try:
    mycursor.execute("SELECT * FROM images_data")
    image_id = mycursor.rowcount
    
        
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
        mycursor.execute(sql_image, (str(image_id), screen_name, photo, im))
    mydb.commit()
    #except:
    #    print("Image data have been recorded.")
    mydb.close()
    
    
    
def detect_labels():
    #Connect to Database
    mydb = connect_to_mysql()
    mycursor = mydb.cursor(buffered=True)
    
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
        sql_tags = "INSERT INTO tags_data (tag_id, tag_content, image_id) VALUES (%s, %s, %s)"
        
        #print(img)
        #sql = "SELECT image_id FROM images_data WHERE image_name = {}".format(img)
        #ima = str(img)
        #print(ima)
        #mycursor.execute(sql)
        
        mycursor.execute("SELECT image_id FROM images_data WHERE image_name = '"+img+"'")
        #print("****")
        myresult = mycursor.fetchall()
        image_ids = []
        for result in myresult:
            image_ids.append(int(result[0]))
        image_ids.sort()

        img_id = str(image_ids[-1])
        
        #mg_id = mycursor.fetchone()
        #print("*****"+img_id)
        mycursor.execute("SELECT * FROM tags_data")
        t_id = mycursor.rowcount
        if t_id < 0:
            t_id = 0
        for tag in description:
            t_id = t_id + 1
            ta_id = str(t_id)
            mycursor.execute(sql_tags, (ta_id, tag, img_id))
        mydb.commit()
        
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
    mydb.close()
    
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
        mydb = connect_to_mysql()
        mycursor = mydb.cursor(buffered=True)
        ## show images_data
        print("Data in images_data Table: "+"\n")
        mycursor.execute("SELECT * FROM images_data WHERE twitter_user= '"+twitter_name+"'")

        myresult = mycursor.fetchall()
        #print(myresult)
        for result in myresult:
            print(result)



        mycursor.execute("SELECT image_id FROM images_data WHERE twitter_user= '"+twitter_name+"'")

        myresult = mycursor.fetchall()
        #print(myresult)
        image_ids = []
        for result in myresult:
            image_ids.append(result[0])

        #print(image_ids)
        print("\n"+"Data in tags_data Table: "+"\n")
        for im_id in image_ids:
            mycursor.execute("SELECT * FROM tags_data WHERE image_id= '"+im_id+"'")
            print("image_id = "+ im_id+"\n")
            myresult = mycursor.fetchall()
            for result in myresult:
                print(result)
            print("\n")
    mydb.close()
    
def search_api():
    search = input("Do you want to search by tag or twitter_user? tag/user ")

    if search == "tag":
        tag_name = input("Please input the tag you want to find: ")
        mydb = connect_to_mysql()
        mycursor = mydb.cursor(buffered=True)
        ## show images_data

        mycursor.execute("SELECT image_id FROM tags_data WHERE tag_content= '"+tag_name+"'")

        myresult = mycursor.fetchall()
        if len(myresult) == 0:
            print("No image with this tag found.")
        else:
            print("\n"+"Images with this tag: "+"\n")
            image_ids = []
            for result in myresult:
                image_ids.append(result[0])
            for image in image_ids:
                mycursor.execute("SELECT * FROM images_data WHERE image_id= '"+image+"'")
                print("image_id = "+ image+"\n")
                myresult = mycursor.fetchall()
                for result in myresult:
                    print(result)
                print("\n")
    elif search == "user" or "twitter_user" or "User":
        user_name = input("Please input the twitter_user you want to find: ")
        mydb = connect_to_mysql()
        mycursor = mydb.cursor(buffered=True)
        ## show images_data

        mycursor.execute("SELECT * FROM images_data WHERE twitter_user= '"+user_name+"'")


        myresult = mycursor.fetchall()
        if len(myresult) == 0:
            print("No image of this user found.")
        else:
            print("\n"+"Images of this user: "+"\n")
            for result in myresult:
                print(result)
    mydb.close()
    
def show_database_info():
    mydb = connect_to_mysql()
    mycursor = mydb.cursor(buffered=True)
    ### For images_data Table:
    #### 1. Number of all images
    mycursor.execute("SELECT * FROM images_data")
    image_number = mycursor.rowcount
    print(str(image_number)+" images in the images_data Table."+"\n")    

    #### 2. Number of images of every twitter_user
    user_uni = set()
    mycursor.execute("SELECT twitter_user FROM images_data")

    myresult = mycursor.fetchall()

    for result in myresult:
        user_uni.add(result)

    for user_name in user_uni:
        mycursor.execute("SELECT * FROM images_data WHERE twitter_user= '"+user_name[0]+"'")
        image_number_user = mycursor.rowcount
        print(str(image_number_user)+" images in the images_data Table"+"from "+user_name[0]+".\n")  

    ### For tags_data Table:
    #### 1. Number of all tags
    mycursor.execute("SELECT tag_content FROM tags_data")
    tag_number = mycursor.rowcount
    print(str(tag_number)+" tags in the tags_data Table."+"\n")        

    #### 2. The most frequent tags

    max_frequent_tag = {}
    tags=mycursor.fetchall()

    for tag in tags:
        max_frequent_tag[tag[0]] = max_frequent_tag.get(tag[0], 0) + 1
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

        

