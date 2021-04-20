import json
import os
import random
import pymongo
from settings import *


async def get_yo_momma_jokes():
    with open(os.path.join(DATA_DIR, 'jokes.json'),"r",encoding='utf-8') as joke_file:
        jokes = json.load(joke_file)
    random_category = random.choice(list(jokes.keys()))
    random_insult = random.choice(list(jokes[random_category]))

    return random_insult

async def save_data(name, playlistname, tracks):
    myclient = pymongo.MongoClient(MONGO_URI)

    mydb = myclient["dot-bot"]
    mycol = mydb["playlists"]
    
    if mycol.find({ 'Author_id': name}).count() > 0:
        cursor = mycol.find({ 'Author_id': name })
        mycol.update({ 'Author_id': name }, {"$set": { playlistname: tracks }})        
    else:
        mycol.insert_one({ "Author_id": name, playlistname: tracks })

    
async def savedPlaylists(name):
    myclient = pymongo.MongoClient(MONGO_URI)

    mydb = myclient["dot-bot"]
    mycol = mydb["playlists"]
    
    if mycol.find({ 'Author_id': name}).count() > 0:
        cursor = mycol.find({ 'Author_id': name }, {"_id": 0, 'Author_id': 0})
        return list(cursor[0].keys())      
    else:
        return []


async def loadPlaylists(name, playlistname):
    myclient = pymongo.MongoClient(MONGO_URI)

    mydb = myclient["dot-bot"]
    mycol = mydb["playlists"]

    if mycol.find({ 'Author_id': name}).count() > 0:
        cursor = mycol.find({ 'Author_id': name }, {"_id": 0, 'Author_id': 0}) 
        if playlistname in cursor[0]:
            return list(cursor[0][playlistname])
        else:
            return []
    else:
        return []
    