import os
import sys
import json
import requests
import redis
import pandas as pd
import numpy as np
from scipy import spatial
from gensim.models import word2vec
import pickle
import MeCab

from flask import Flask, request, abort
from flask_api import status
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,LocationMessage,FlexSendMessage
)

app = Flask(__name__)

CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]
CHANNEL_ACCESS_TOKEN = os.environ['CHANNEL_ACCESS_TOKEN']
STATION_API_URL = 'http://express.heartrails.com/api/json?method=getStations&x={}&y={}'

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

redis = redis.Redis(host='localhost', port=6379, db=0)

@app.route("/hello")
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