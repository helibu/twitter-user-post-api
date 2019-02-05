#!/usr/bin/env python3.6
# encoding: utf-8
#Copyright 2018 He Li heli@bu.edu


#Twitter API credentials
consumer_key = "Enter your consumer_key"
consumer_secret = "Enter your consumer_secret"
access_key = "Enter your access_key"
access_secret = "Enter your access_secret"


def get_photo_tweets(screen_name):
    
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
    
    
    
    #download photo with urls in the photos list using wget module
    #to the photo_folder
    mypath = os.getcwd()
    mypath = mypath+"/photo_folder"
    if not os.path.isdir(mypath):
       os.makedirs(mypath)
    for photo in photos:
        wget.download(photo, out=mypath)
        

    
def detect_labels():
    
    #load google credentials.json to os environment
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"]= "your_google_credentials.json"
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
        im.save(str('%d'%count)+'.jpg', 'JPEG')
        count+=1

def img_to_video():
    
    os.system('ffmpeg -r 1/3 -f image2 -i %d.jpg -s 1200x900 photos.mp4')
    #ffmpeg parameters:
    #-r pics per sec, here is 1 pic per 3 secs
    #-f input format
    #-i input source
    #-s size 1200x900
    #output to a photos.mp4


if __name__ == '__main__':
    #get photos from twitter account with twitter api
    get_photo_tweets("@LadyGaga")
    #detect labels from photos with google vision label detection
    detect_labels()
    #convert imgs with labels to a mp4 video
    img_to_video()



