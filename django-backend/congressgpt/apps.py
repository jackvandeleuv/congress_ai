from django.apps import AppConfig
from search_engine import SearchEngine
from decouple import config
from openai import OpenAI
import nltk


class CongressgptConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'congressgpt'
    search_engine = SearchEngine()
    openai_client = OpenAI(
        api_key=config("OPENAI_API_KEY")
    )
    nltk.download('punkt')
