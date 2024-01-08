# myapp/views/api.py
import requests
from requests import JSONDecodeError
import os
from decouple import config
from django.apps import apps
from congress_gpt import prompt, search_prompt
from supabase import create_client
import json

key: str = config("VITE_SUPABASE_KEY")
url = config("VITE_SUPABASE_URL")

# talk_url = 'http://localhost:3000/prompt'
# search_url = 'http://localhost:3000/search_engine'
# history_url = 'http://localhost:3000/chat_'
# titles_url = 'http://localhost:3000/user_chats'

# Get titles directly from supabase
titles_url = f"{url}/rest/v1/chats"

# Get history directly from supabase
history_url = f"{url}/rest/v1/messages"


class ApiResponse:
    def __init__(
        self, 
        chat_id=None, 
        title=None, 
        pos=None, 
        search_response=None, 
        content=None, 
        role=None, 
        createdAt=None, 
        rating=None, 
        error=None,
        search_request=None
    ):
        self.success = True
        self.chat_id = chat_id
        self.title = title
        self.pos = pos
        self.search_response = search_response
        self.search_request = search_request
        self.content = content
        self.role = role
        self.createdAt = createdAt
        self.rating = rating

        if error is not None:
            self._error(error[0], error[1])

    def _error(self, status, reason=None):
        self.success = False
        self.status = status
        self.reason = reason


def parse_chat_id(num: str = None):
    """
    This function parses the chat_id from string to int.
    It raises an error if the string is not convertible
    or if the value is not positive.
    """
    if num is None:
        return None
    if isinstance(num, int):
        if num > 0:
            return num
        raise ValueError('The chat_id input should not be negative.')
    if not isinstance(num, str):
        raise ValueError('The chat_id input should be a string.')
    if num.strip() == '':
        return None
    try:
        chat_id = int(num)
    except ValueError:
        raise ValueError('The chat_id input is not a valid integer.')

    if chat_id <= 0:
        raise ValueError('The chat_id input is smaller than zero.')

    return chat_id


def parse_pos(num: str = None):
    """
    This function parses the position from string to int.
    It raises an error if the string is not convertible
    or if the value is not positive.
    """
    if num is None:
        return 0
    if isinstance(num, int):
        if num > 0:
            return num
        raise ValueError('The pos input should not be negative.')
    if not isinstance(num, str):
        raise ValueError('The pos input should be a string.')
    if num.strip() == '':
        return 0
    try:
        pos = int(num)
    except ValueError:
        raise ValueError('The pos input is not a valid integer.')

    if pos < 0:
        raise ValueError('The pos input is smaller than zero.')

    return pos


def talk(chat_prompt: str, token: str, created_at: str, chat_id: str = None, pos: str = None, language_model: str = None):
    """
    This function sends a chat request to the server.
    It always returns an ApiResponse, regardless of error.
    If chat_id is None, this function starts a new chat.
    """

    data = {
        'prompt': chat_prompt,
        # 'chat_id': parse_chat_id(chat_id),
        'created_at': created_at,
        'order_in_chat': parse_pos(pos),
        'language_model': language_model
    }

    if chat_id is not None and chat_id != 'None':
        data['chat_id'] = parse_chat_id(chat_id)

    response = prompt(data, token)
    response = response.content
    response = json.loads(response.decode('utf-8'))

    _chat_id = response['chats_id']
    _pos = response['order_in_chat']
    _content = response['content']
    _role = response['role']
    _search_request = response['search_request']
    _search_response = response['search_response']
    return ApiResponse(
        chat_id=_chat_id, 
        pos=_pos, 
        content=_content, 
        role=_role,
        search_request=_search_request,
        search_response=_search_response
    )



def search(token: str, chat_id: str, language_model: str):
    """
    This function sends a search request to the server.
    It should be called whenever the result from the server
    by calling talk() has a search=True
    It always returns a list, regardless of error.
    """
    data = {
        'chat_id': parse_chat_id(chat_id),
        'language_model': language_model
    }

    response = search_prompt(data, token, chat_id, language_model)

    return [
        ApiResponse(
            chat_id=res['chats_id'],
            content=res['content'],
            pos=res['order_in_chat'],
            role=res['role'],
            search_request=res['search_request'],
            search_response=res['search_response']
        ) for res in response]



def titles(token: str):
    """
    This function retrieves all titles for the current user
    It always returns a list, regardless of error.
    """
    headers = {
        'Authorization': f'Bearer {token}',
        "Content-Type": "application/json",
        "apikey": key
    }

    params = {
        'select': 'chat_title,id',
    }

    response = requests.get(titles_url, headers=headers, params=params)
    status = response.status_code

    if status != 200:
        return list()

    # try:
    #     response = response.json()
    # except JSONDecodeError as e:
    #     print(e)
    #     return list()

    try:
        # chats = response['chats_id']
        # response_list = [ApiResponse(title=chat['title'], chat_id=chat['chat_id']) for chat in chats]

        # Change format to Supabase column names
        response_list = [
            ApiResponse(title=chat['chat_title'], chat_id=chat['id']) 
            if chat['chat_title'] is not None
            else ApiResponse(title='New Chat', chat_id=chat['id']) 
            for chat in response.json()
        ]
    except KeyError as e:
        print(e)
        return list()
    
    return sorted(response_list, key=lambda x: x.chat_id, reverse=True)


def history(token: str, chat_id: str):
    """
    This function retrieves all previous chats given an id
    It always returns a list, regardless of error.
    """
    headers = {
        'Authorization': f'Bearer {token}',
        "Content-Type": "application/json",
        "apikey": key
    }

    params = {
        'select': 'id,order_in_chat,content,role,created_at,rating,search_request,search_response',
        'chats_id': f'eq.{chat_id}'
    }

    try:
        chat_id = parse_chat_id(chat_id)
    except ValueError:
        return list()

    response = requests.get(history_url, headers=headers, params=params)
    status = response.status_code

    if status != 200:
        print('history() failed with status code:', status)
        return list()

    try:
        response = response.json()
    except JSONDecodeError as e:
        print('JSONDecodeError:', str(e))
        return list()

    try:
        response_list = [
            ApiResponse(
                content=speech['content'],
                pos=speech['order_in_chat'],
                role=speech['role'],
                createdAt=speech['created_at'],
                rating=speech['rating'],
                search_request=speech['search_request'],
                search_response=speech['search_response'],
                chat_id=speech['id']
            )
            for speech in response]
    except KeyError as e:
        print('KeyError:', str(e))
        return list()

    return sorted(response_list, key=lambda x: x.createdAt, reverse=True)


if __name__ == '__main__':
    supabase_url = ''
    supabase_key = ''
    supabase = create_client(supabase_url, supabase_key)

    data = supabase.auth.sign_in_with_password({
        'email': '',
        'password': '',
    })

    response = titles(data.session.access_token)

    # response = talk('Give me 3 bills on climate change',
    #                 data.session.access_token,
    #                 chat_id='',
    #                 pos=None)
    # print('chat_id=', response.chat_id, 'pos=', response.pos)
    # print(response.content, response.search, '\n')
    #
    # chat_id = response.chat_id
    #
    # if response.search:
    #     response = search(data.session.access_token, chat_id)
    #     for res in response:
    #         print(res.role, res.content, res.pos, res.content)
    #     print()
    #
    # history = history(data.session.access_token, chat_id)
    # for res in history:
    #     print(res.role, res.content)

