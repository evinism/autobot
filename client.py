from dotenv import load_dotenv
load_dotenv()
import berserk
import os

session = berserk.TokenSession(os.environ['LICHESS_API_TOKEN'])
client = berserk.Client(session=session)
