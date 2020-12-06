import json
import os
import random
from settings import *


async def get_yo_momma_jokes():
    with open(os.path.join(DATA_DIR, 'jokes.json'),"r",encoding='utf-8') as joke_file:
        jokes = json.load(joke_file)
    random_category = random.choice(list(jokes.keys()))
    random_insult = random.choice(list(jokes[random_category]))

    return random_insult