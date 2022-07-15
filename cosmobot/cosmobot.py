#from utils import dynamodb
from loguru import logger
import os
import discord

# AWS Dynamo
#AWS_DYNAMO_SESSION = dynamodb.create_session()

# Discord vars
DISCORD_BOT_TOKEN = os.getenv('COSMOBOT_TOKEN')
DISCORD_INTENTS = discord.Intents.default()
DISCORD_INTENTS.members = True
DISCORD_CLIENT = discord.Client(intents=DISCORD_INTENTS)


def launch():
    print('here')
    #item = dynamodb.query_items(AWS_DYNAMO_SESSION, 'mm_test', 'date', '2022_6')
    #print(item)

    #INSTA_USER = os.getenv('INSTA_USER')
    #INSTA_PWD = os.getenv('INSTA_PWD')
    #INSTA_CLIENT = instagrapi.Client()
    #INSTA_CLIENT.login(INSTA_USER, INSTA_PWD)
    #user_id = INSTA_CLIENT.user_id_from_username('alturiano')
    #print(user_id)

@DISCORD_CLIENT.event
async def on_ready():
    logger.info(f'Logged in as {DISCORD_CLIENT.user.name}')
    
    await DISCORD_CLIENT.wait_until_ready()
    channel = DISCORD_CLIENT.get_channel(id=int(983498005321764926))

    a = None
    for i in range (0,4):
        a = await channel.send('test')
        if a:
            break

    print(a)

    guild = DISCORD_CLIENT.get_guild(569226427031879700)
    role = guild.get_role(984580475895021588)

    print(role.mention)
    a = await channel.send(role.mention)