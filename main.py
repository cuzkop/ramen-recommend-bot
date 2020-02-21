import os
import sys
import json
# import requests
# import redis
# import pandas as pd
# import numpy as np
# from scipy import spatial
# from gensim.models import word2vec
# import pickle
# import MeCab

from flask import Flask, request, abort
from flask_api import status
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

app = Flask(__name__)

# CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]
# CHANNEL_ACCESS_TOKEN = os.environ['CHANNEL_ACCESS_TOKEN']
CHANNEL_SECRET = 'e49acc837b36e6028b221ea279be561b'
CHANNEL_ACCESS_TOKEN = 'FlXui90ppr7sbp6qsvXaqxYxgjAbzUiQzb8U/At5997vBgd+h1Eju7toVfvv6wfkPGkCV8Y/yYe+e9lKSTHC9mgVtVGALSy5Ae3GTwXsdU2W75DaZfbVFXdNK7rdagvV00FHhFbARUvqYbEWgNS9XgdB04t89/1O/w1cDnyilFU='

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.route("/")
def hello_world():
    return "hello world!",status.HTTP_200_OK

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK',status.HTTP_200_OK

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", port=port)