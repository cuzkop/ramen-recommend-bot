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

redis = redis.Redis(host=os.environ['REDIS_URL'], port=26739, db=0)

mecab = MeCab.Tagger ('-Owakati')

f = open("./pickle/skip_list.txt","rb")
skip_list = pickle.load(f)
f.close()

vector_size = 250

model = word2vec.Word2Vec.load('./models/skip_w2v.model')


df = pd.read_csv('./csv/review_wakati.csv')
df = df.drop(['store_id'],axis=1)
df = df.rename(columns={'Unnamed: 0':'store_id'}).set_index('store_id')

@app.route("/hello")
def hello_world():
    return "hello world!",status.HTTP_200_OK

@app.route('/', methods=['POST'])
def index():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return '',status.HTTP_200_OK

@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    uid = event.source.user_id
    h = redis.hgetall(uid)
    token = event.reply_token

    if h:
        lat, long = h['lat'.encode()].decode(), h['long'.encode()].decode()
    else:
        send_message(token, '位置情報を送信して下さい！')
        return

    stations = get_stations(lat, long)
    if  not stations:
        send_message(token, "エラーが発生しました。やり直して下さい。")
        return

    nouns = get_noun(event.message.text)
    vectors = avg_feature_vectors(nouns.split(' '), model)

    result = {}
    for i, row in df.iterrows():
        store_station = prepro_station(row.station)
        if store_station not in stations:
            continue

        score = sentence_similarity(vectors, skip_list[i])
        result[i] = score * row.score

    score_sorted = sorted(result.items(), key=lambda x:x[1], reverse=True)

    for t in score_sorted[:10]:
        row = df[df.index == t[0]]
        name, score, station = row.store_name.values[0], row.score.values[0], row.station.values[0]

        send_message(token, name)
        break
        print('店名:{}, 食べログスコア:{}, 独自スコア:{:.2f}, 最寄駅:{}'.format(name,score,t[1]*100,station))

@handler.add(MessageEvent, message=LocationMessage)
def message_location(event):
    lat = event.message.latitude
    long = event.message.longitude
    uid = event.source.user_id
    station = get_station(lat, long)
    token = event.reply_token

    if station:
        redis.hset(uid, 'lat', lat)
        redis.hset(uid, 'long', long)
        redis.expire(uid, 1800)
        message = '{}駅周辺のラーメン屋をお探しします！\nあなたの今の気分を教えて下さい\n（例）あっさりした醬油ラーメン'.format(station)
        send_message(token, message)
    else:
        send_message(token, "エラーが発生しました。やり直して下さい。")

def send_message(token, message):
    line_bot_api.reply_message(
        token,
        TextSendMessage(text=message)
    )


def get_station(lat, long):
    station = http_request(STATION_API_URL.format(long, lat))
    if station:
        return station['response']['station'][0]['name']
    else:
        return ''

def get_stations(lat, long):
    stations = http_request(STATION_API_URL.format(long, lat))
    if stations:
        return [
            stations['response']['station'][0]['name'],
            stations['response']['station'][0]['prev'],
            stations['response']['station'][0]['next']
            ]
    else:
        return ''

def http_request(url):
    res = requests.get(url)
    
    if res.status_code != status.HTTP_200_OK:
        return ''

    result_json = res.json()
    return result_json

def prepro_station(station):
    if '（東武・都営・メトロ）' in station:
        return station.strip('（東武・都営・メトロ）').strip('駅')

    if '（つくばＥＸＰ）' in station:
        return station.strip('（つくばＥＸＰ）').strip('駅')

    if '（メトロ）' in station:
        return station.strip('（メトロ）').strip('駅')

    return station

def sentence_similarity(vec1, vec2):
    return 1 - spatial.distance.cosine(vec1, vec2)

def avg_feature_vectors(words, model):
    feature_vec = np.zeros(vector_size, dtype='float32')
    for word in words:
        try:
            feature_vec = np.add(feature_vec, model[word])
        except KeyError:
            pass

    return feature_vec

def get_noun(text):
    mecab.parse('')
    node = mecab.parseToNode(text)
    result = []

    while node:
        word = node.surface
        pos,pos2 = node.feature.split(",")[0],node.feature.split(",")[1]
        if '0' in word or '1' in word or '2' in word or '3' in word or '4' in word or '5' in word or '6' in word or '7' in word or '8' in word or '9' in word:
            node = node.next
            continue

        if pos2 == '数':
            node = node.next
            continue
            
        if (pos == '名詞' and pos2 != '数') or (pos == '形容詞') or (pos == '副詞'):
            result.append(word)
        node = node.next

    return ' '.join(result)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", port=port)