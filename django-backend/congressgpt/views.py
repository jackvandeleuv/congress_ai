from django.shortcuts import render
from django.http import JsonResponse
from api import *
from django.middleware.csrf import get_token
import json

def get_csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})

# Action for the /congress-gpt/ask-congressgpt route.
def ask_congressgpt(request):
    # Handle the incoming user message
    # if request.method == 'POST':
    data = json.loads(request.body)
    user_input = data.get('user_input')
    token = data.get('password')
    chat_id = data.get('chat_id')
    order_in_chat = data.get('order_in_chat')
    created_at = data.get('created_at')
    language_model = data.get('language_model')
    if not user_input:
        return JsonResponse({"error": "Input cannot be empty"}, status=400)
    if not token:
        return JsonResponse({"error": "token cannot be empty"}, status=400)

    # call a chatbot api
    bot_response = talk(user_input, token, created_at, str(chat_id), str(order_in_chat), language_model)

    # Check for errors in the bot response using is_error method
    if hasattr(bot_response, 'error') and bot_response.error:
        return JsonResponse({"error": bot_response.error}, status=400)
    response = {
        "chatId": bot_response.chat_id,
        "orderInChat": bot_response.pos,
        "content": bot_response.content,
        "role": bot_response.role,
        "searchRequest": bot_response.search_request,
        "searchResponse": bot_response.search_response
    }
    # Return the bot's response to the client
    return JsonResponse(response)

def search_congressgpt(request):
    data = json.loads(request.body)
    token = data.get('password')
    chat_id = data.get('chat_id')
    language_model = data.get('language_model')

    if not chat_id:
        return JsonResponse({"error": "Chat_id cannot be empty"}, status=400)
    if not token:
        return JsonResponse({"error": "Token cannot be empty"}, status=400)

    # call a chatbot api
    bot_response = search(str(token), str(chat_id), language_model)
    # Check for errors in the bot response using is_error method
    if hasattr(bot_response, 'error') and bot_response.error:
        return JsonResponse({"error": bot_response.error}, status=400)
    
    response = []
    for r in bot_response:
        data = {
            "chatId": r.chat_id,
            "orderInChat": r.pos,
            "content": r.content,
            "role": r.role,
            "searchRequest": r.search_request,
            "searchResponse": r.search_response,
        }
        response.append(data)
    json_data = {"response": response}   

    # Return the bot's response to the client
    return JsonResponse(json_data)    

def get_history_congressgpt(request):
    data = json.loads(request.body)
    token = data.get('token')
    chat_id = data.get('chat_id')

    if not chat_id:
        return JsonResponse({"error": "chat_id cannot be empty"}, status=400)
    if not token:
        return JsonResponse({"error": "token cannot be empty"}, status=400)
    # call a chatbot api
    bot_response = history(token, chat_id)
    response = []
    for r in bot_response:
        data = {
            "content": r.content,
            "orderInChat": r.pos,
            "role": r.role,
            "createdAt": r.createdAt,
            "rating": r.rating,
            "searchRequest": r.search_request,
            "searchResponse": r.search_response,
            "chatId": r.chat_id
        }
        response.append(data)
    json_data = {"history": response}
    # Return the bot's response to the client
    return JsonResponse(json_data)    

def get_historybar_congressgpt(request):
    data = json.loads(request.body)
    token = data.get('token')

    if not token:
        return JsonResponse({"error": "user_token cannot be empty"}, status=400)

    # call a chatbot api
    bot_response = titles(token) 
    response =[]
    for r in bot_response:
        data = {
            "title": r.title,
            "chatId": r.chat_id,
        }
        response.append(data)
        # Return the bot's response to the client
    json_data = {"chats": response}
    return JsonResponse(json_data)



    