import numpy as np
from typing import List, Dict, Optional, Dict, Any
import os
import time
import datetime
import json
from openai import OpenAI
import openai
import requests
import threading
from search_engine import SearchEngine
from dotenv import load_dotenv
from decouple import config
from django.apps import apps
from django.http import JsonResponse


# Default language model if none is specified.
DEFAULT_LANGUAGE_MODEL = 'gpt-4-1106-preview'

# Language model for generating titles.
TITLE_LANGUAGE_MODEL = 'gpt-3.5-turbo-1106'

app_config = apps.get_app_config('congressgpt')


def get_first_user_message(chat_id, access_token):
    """
    Gets the first message in a given chat.
    """
    key: str = config("VITE_SUPABASE_KEY")
    url = config("VITE_SUPABASE_URL")
    messages_endpoint = f"{url}/rest/v1/messages"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "apikey": key
    }

    params = {
        "chats_id": f"eq.{chat_id}",
        "role": "eq.user", 
        "order_in_chat": "eq.0",  
        "limit": "1"  
    }

    response = requests.get(messages_endpoint, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        if data:  
            return data[0].get('content')  
        else:
            return None
    else:
        return None
    
def post_chat_title(title: str, access_token: str, chat_id: int) -> None:
    """
    POST chat title to Supabase.
    """
    key: str = config("VITE_SUPABASE_KEY")
    url = config("VITE_SUPABASE_URL")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "apikey": key  
    }

    payload = {
        'chat_title': title
    }

    response = requests.patch(
        f"{url}/rest/v1/chats?id=eq.{chat_id}",
        headers=headers,
        json=payload
    )


def generate_chat_title(message, access_token, chat_id):
    """
    Create a title for a new chat using GPT.
    """
    # Setting up the conversation context for the chat model
    messages = [
        {"role": "system", "content": "You are an assistant capable of generating titles for messages."},
        {"role": "user", "content": f"Write a short title to describe this request: {message}"}
    ]

    # Chat completion
    openai_client = app_config.openai_client
    response = openai_client.chat.completions.create(
        model=TITLE_LANGUAGE_MODEL,  # Replace with your chosen model
        messages=messages,
        max_tokens=100  # Adjust as needed
    )

    # Extracting the title from the response
    title = response.choices[0].message.content.strip()

    # Add the new chat title to the database
    post_chat_title(title, access_token, chat_id)

def get_title_for_chats(chats_id, access_token):
    """
    Gets title for a chat.
    """
    chat_titles = []

    key: str = config("VITE_SUPABASE_KEY")
    url = config("VITE_SUPABASE_URL")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "apikey": key
    }

    for chat_id in chats_id:
        params = {
            "select": "chat_title",
            "id": f"eq.{chat_id}"  
        }

        response = requests.get(f"{url}/rest/v1/chats", headers=headers, params=params)

        if response.status_code == 200:
            chat_data = response.json()
            if chat_data:
                chat_title = chat_data[0].get('chat_title')
                chat_titles.append({"chat_id": chat_id, "title": chat_title})
            else:
                chat_titles.append({"chat_id": chat_id, "title": None})
        else:
            chat_titles.append({"chat_id": chat_id, "title": None})

    return chat_titles


def post_new_message(access_token, language_model, messages: List[Dict]):
    """
    Posts a list of messages to Supabase. 
        messages = [{
            "content": content,
            "order_in_chat": order_in_chat, 
            "role": role,
            "chats_id": chat_id,
            "search_request": search_request,
            "search_response": search_response,
            "created_at": created_at,
            "search_full_text_id": search_full_text_id,
            "function_invoked": function_invoked
        }]
    """
    key: str = config("VITE_SUPABASE_KEY")
    url = config("VITE_SUPABASE_URL")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "apikey": key  
    }

    for i in range(len(messages)):
        messages[i]['language_model'] = language_model
        if messages[i]['search_full_text_id'] is not None:
            messages[i]['search_full_text_id'] = int(messages[i]['search_full_text_id'])

    response = requests.post(
        f"{url}/rest/v1/messages",
        headers=headers,
        data=json.dumps(messages)  
    )

    # Check if the request was successful
    if response.status_code != 201:
        raise Exception("Failed to post chat message with status code:", response.status_code, response.text)
        

def get_prior_chat_messages(access_token, chat_id) -> List[Dict]:
    """
    Get all previous messages in the specified chat.
    """
    key: str = config("VITE_SUPABASE_KEY")
    url = config("VITE_SUPABASE_URL")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "apikey": key
    }
    params = {
        "chats_id": f"eq.{chat_id}",
        "select": "role,content,search_request,created_at,search_response,order_in_chat,function_invoked,search_full_text_id"
    }

    RETRIES = 5
    retries_left = RETRIES
    status_code = 200
    response_chat_size = 0
    while (retries_left and status_code == 200 and response_chat_size == 0):
        response = requests.get(
            f"{url}/rest/v1/messages",
            headers=headers,
            params=params
        )
        retries_left -= 1
        status_code = response.status_code
        response_chat_size = len(response.json())

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print("Failed to fetch data:", response.status_code, response.text)
        return []


def ask_gpt(chat: List[Dict], language_model: str, system_prompts=[]) -> Dict: 
    """
    Generate GPT's next message in an ongoing chat.
    """
    search_engine = app_config.search_engine

    # Ensure the chat is presented in chronological order
    chat = list(sorted(chat, key=lambda x: x['order_in_chat']))

    # Truncate chat if it is greater than 15 messages
    chat = chat[-15:]

    for i, message in enumerate(chat):
        message.pop('search_request', None)
        message.pop('created_at', None)
        message.pop('order_in_chat', None)
        message.pop('search_response', None)
        message.pop('function_invoked', None)
        message.pop('search_full_text_id', None)
        
        # Feed GPT prior chat history with stopwords removed if not most recent user message
        if i != len(chat) - 1:
            message['content'] = search_engine.remove_stopwords(message['content'])
    
    chat = chat + system_prompts

    summary_params = [
        'query'
    ]

    full_text_params = [
        'query', 'full_text_id'
    ]

    openai_client = app_config.openai_client
    completion = openai_client.chat.completions.create(
        model=language_model,
        messages=chat,
        functions=[
            {
                "name": "search_summaries",
                "description": "Search for U.S. Congress bills.",
                "parameters": {
                    "type": "object",
                    "properties": {
                    "query": {
                        "type": "string",
                        "description": "A search query that fits the user's request."
                    }
                    },
                    "required": summary_params
                }
            },
            {
                "name": "search_full_texts",
                "description": "Search for specific passages within one U.S. Congress bill.",
                "parameters": {
                    "type": "object",
                    "properties": {
                    "query": {
                        "type": "string",
                        "description": "A search query that fits the user's request."
                    },
                    "full_text_id": {
                        "type": "integer",
                        "description": "The id that identifies the requested bill."
                    }
                    },
                    "required": full_text_params
                }
            }
        ],
        timeout=60
    )

    if len(completion.choices) > 1:
        raise Exception('OpenAI unexpectedly returned >1 completion choice.')
        
    ft_id = None
    function_invoked = None

    # Add back the stop token if stop was triggered
    if completion.choices[0].finish_reason == 'function_call':
        function_invoked = completion.choices[0].message.function_call.name

        args = json.loads(completion.choices[0].message.function_call.arguments)
        chat_text = ', '.join([args[key] for key in summary_params if key in args])
        chat_text = chat_text.lower()
        search_request = True
        
        if 'full_text_id' in args:
            ft_id = args['full_text_id']

    else:
        chat_text = completion.choices[0].message.content
        search_request = False

    return {
        'role': completion.choices[0].message.role,
        'content': chat_text,
        'search_request': search_request,
        'search_response': False,
        'search_full_text_id': ft_id,
        'function_invoked': function_invoked
    }


def extract_token(request: requests.Response): 
    """
    Extract JWT token from request.

    Throws ValueError.
    """
    auth_header = request.headers.get('Authorization')
    if auth_header is not None:
        parts = auth_header.split()
        if parts[0].lower() != 'bearer':
            raise ValueError("Invalid token header. Must start with Bearer.")
        elif len(parts) == 1:
            raise ValueError("Invalid token header. Token missing.")
        elif len(parts) > 2:
            raise ValueError("Invalid token header. Token contains spaces.")
        return parts[1]  # Return access token
    else:
        raise ValueError("Authorization header is missing.")
    

def check_for_llm_loop(chat: List[Dict]) -> bool:
    """
    Checks whether GPT is repeatedly generating messages without asking for user input.
    """
    LOOKBACK = 6
    repeat_assistant_messages = 0
    for message in chat[:LOOKBACK][::-1]:
        if message['role'] == 'assistant':
            repeat_assistant_messages += 1
    return repeat_assistant_messages == LOOKBACK
    

def start_new_chat(access_token) -> int:
    """
    Create a new chat in Supabase. Returns the id for the new chat, which should be returned to the frontend.
    """
    key: str = config("VITE_SUPABASE_KEY")
    url = config("VITE_SUPABASE_URL")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "apikey": key  
    }
    
    data = {
        'created_at': str(datetime.datetime.fromtimestamp(time.time(), tz=datetime.timezone.utc))
    }

    response = requests.post(
        f"{url}/rest/v1/chats",
        headers=headers,
        data=json.dumps(data)  
    )

    params = {
        "select": "id",
        "order": "id.desc",
        "limit": "1"
    }

    if response.status_code == 201:
        select_response = requests.get(
            f"{url}/rest/v1/chats",
            headers=headers,
            params=params
        )
        new_chat_id = select_response.json()[0]['id']

        return new_chat_id
    else:
        raise Exception('Create new chat failed with status code:', response.status_code)


def prompt(data, access_token):
    """
    Returns the system's response to the user.
    """
    prompt = data.get('prompt')
    chat_id = data.get('chat_id', None)
    order_in_chat = int(data.get('order_in_chat', 0))
    language_model = data.get('language_model', DEFAULT_LANGUAGE_MODEL)

    chat = []

    if chat_id is None:
        chat_id = start_new_chat(access_token)

        # Generate chat title asynchronously
        threading.Thread(target=generate_chat_title, args=(prompt, access_token, chat_id)).start()
    else:  # Get the previous messages in the same chat
        chat = get_prior_chat_messages(access_token, chat_id)

    chat.append({
        'role': 'user', 
        'content': prompt,
        'search_request': False, 
        'search_response': False,
        'order_in_chat': order_in_chat,
        'created_at': str(datetime.datetime.fromtimestamp(time.time(), tz=datetime.timezone.utc))
    })

    # system_prompts = [{
    #     "role": "system", 
    #     "content": """
    #         If the user wants detailed information about U.S. Congress bills, make a function call to search_engine. Write three different versions of the search query.
    #     """
    # }]
    system_prompts=[]

    new_llm_message = ask_gpt(chat, language_model, system_prompts)

    messages_for_insert = [
        {
            'content': prompt, 
            'chats_id': chat_id, 
            'order_in_chat': order_in_chat, 
            'role': 'user', 
            'search_request': False,
            'search_response': False,
            'search_full_text_id': None,
            'function_invoked': None
        },
        {
            'content': new_llm_message['content'],
            'chats_id': chat_id,
            'order_in_chat': order_in_chat + 1,
            'role': new_llm_message['role'],
            'search_request': new_llm_message['search_request'],
            'search_response': new_llm_message['search_response'],
            'search_full_text_id': new_llm_message['search_full_text_id'],
            'function_invoked': new_llm_message['function_invoked']
        }
    ]

    # The frontend will immediately follow up on a search request, so this cannot be done asynchronously
    if messages_for_insert[-1]['search_request']:
        post_new_message(access_token, language_model, messages_for_insert)
    else:
        # Asynchronously POST the user's prompt and the LLM's response to the database
        threading.Thread(target=post_new_message, args=(access_token, language_model, messages_for_insert)).start()

    return JsonResponse({
        'content': new_llm_message['content'],
        'chats_id': chat_id,
        'order_in_chat': order_in_chat + 1,
        'role': new_llm_message['role'],
        'search_request': new_llm_message['search_request'],
        'search_response': new_llm_message['search_response']
    })


def search_prompt(data, access_token, chat_id=None, language_model=DEFAULT_LANGUAGE_MODEL):    
    """
    Returns search engine results and associated GPT summarization. Throws an error if the most recent message in the chat
    was not flagged as a search request. 
    """
    number_to_return = data.get('number_to_return', 5)
    date_range = data.get('date_range', {
        'start_year': 1970, 'start_month': 1, 'start_day': 1, 
        'end_year': 2050, 'end_month': 12, 'end_day': 31
    })
    get_sponsors = data.get('get_sponsors', False)
    chamber = data.get('chamber', 'any')
    legislative_types = data.get('legislative_types', 'any')
    require_bipartisan = data.get('require_bipartisan', False)
    
    if chat_id is None:
        return JsonResponse({'error': 'chat_id required for search_engine endpoint'}, 400)
    
    chat = []
    # Get the previous messages in the same chat
    chat = get_prior_chat_messages(access_token, chat_id)


    chat = list(sorted(chat, key=lambda x: x['order_in_chat']))

    if not chat[-1]['search_request']:
        return JsonResponse({'error', 'Last message in this chat was not flagged as a search request.'}, 400)
    search_query = chat[-1]['content']
    last_order_in_chat = chat[-1]['order_in_chat']

    # Get search engine response
    params = {
        'number_to_return': number_to_return,
        'date_range': date_range,
        'get_sponsors': get_sponsors,
        'chamber': chamber,  
        'legislative_types': legislative_types,
        'require_bipartisan': require_bipartisan,
        'query': search_query
    }

    search_engine = app_config.search_engine
    if chat[-1]['function_invoked'] == 'search_summaries':
        results = search_engine.retrieve_summary(params)
    elif chat[-1]['function_invoked'] == 'search_full_texts':
        results = search_engine.retrieve_full_text_chunks(params, chat[-1]['search_full_text_id'])
    else:
        raise ValueError('Unrecognized search function invoked.')

    chat.append({
        'role': 'assistant', 
        'content': str(results), 
        'search_request': False, 
        'search_response': True, 
        'order_in_chat': last_order_in_chat + 1,
        'created_at': str(datetime.datetime.fromtimestamp(time.time(), tz=datetime.timezone.utc))
    })

    system_prompts = [{
        "role": "system", 
        "content": """
            Summarize the search results for the user. If the search results are not relevant, tell the user. Suggest ways to improve the search query, and ask the user if they want you to do another search.
        """
    }]

    if check_for_llm_loop(chat):
        return JsonResponse({'error', 'GPT repeated itself too many times.'}, 400)
    
    new_llm_message = ask_gpt(chat, language_model, system_prompts)

    messages_for_insert = [
        {
            'content': str(results), 
            'chats_id': chat_id, 
            'order_in_chat': last_order_in_chat + 1, 
            'role': 'assistant', 
            'search_request': False,
            'search_response': True,
            'search_full_text_id': None,
            'function_invoked': None
        },
        {
            'content': new_llm_message['content'],
            'chats_id': chat_id,
            'order_in_chat': last_order_in_chat + 2,
            'role': new_llm_message['role'],
            'search_request': new_llm_message['search_request'],
            'search_response': new_llm_message['search_response'],
            'search_full_text_id': new_llm_message['search_full_text_id'],
            'function_invoked': new_llm_message['function_invoked']
        }
    ]

    # Register the user's prompt and the LLM's response in the database
    threading.Thread(target=post_new_message, args=(access_token, language_model, messages_for_insert)).start()

    return [{
        'content': str(results), 
        'chats_id': chat_id, 
        'order_in_chat': last_order_in_chat + 1, 
        'role': 'assistant', 
        'search_request': False,
        'search_response': True
    },
    {
        'content': new_llm_message['content'],
        'chats_id': chat_id,
        'order_in_chat': last_order_in_chat + 2,
        'role': new_llm_message['role'],
        'search_request': new_llm_message['search_request'],
        'search_response': new_llm_message['search_response']
    }]


# Make a request to the Supabase API to fetch chat ids associated with the authenticated user
def get_chats_for_user(access_token):
    """
    Gets ids of all user chats.
    """
    key: str = config("VITE_SUPABASE_KEY")
    url = config("VITE_SUPABASE_URL")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "apikey": key
    }

    params = {
        "select": "id"
    }

    response = requests.get(f"{url}/rest/v1/chats", headers=headers, params=params)

    if response.status_code == 200:
        chats = response.json()
        chat_ids = [chat['id'] for chat in chats]  
        return chat_ids
    else:
        raise Exception(f"Failed to fetch chats: {response.status_code}, {response.text}")

# @app.route('/user_chats', methods=['GET'])
# def user_chats():
#     try:
#         access_token = extract_token(request)
#     except ValueError as error:
#         return jsonify({'message': str(error), 'status_code': 401}), 401

#     try:
#         user_chat_ids = get_chats_for_user(access_token)
#         chat_ids_titles = get_title_for_chats(user_chat_ids, access_token)
#         return jsonify({'chats': chat_ids_titles, 'status_code': 200}), 200
#     except Exception as e:
#         return jsonify({'message': str(e), 'status_code': 500}), 500

# @app.route('/chat_<int:chat_id>', methods=['GET'])
# def chat_history(chat_id):
#     app.logger.info(f"Received request for chat history with chat_id: {chat_id}")  # Log statement

#     try:
#         access_token = extract_token(request)
#     except ValueError as error:
#         return jsonify({'message': str(error), 'status_code': 401}), 401

#     try:
#         chat_history = get_prior_chat_messages(access_token, chat_id)
#         return jsonify({'chat_history': chat_history, 'status_code': 200}), 200
#     except Exception as e:
#         return jsonify({'message': str(e), 'status_code': 500}), 500

