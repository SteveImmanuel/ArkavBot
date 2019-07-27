import os
import time
import pytz
from datetime import datetime,timedelta
from dateutil.parser import parse
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from flask import Flask, request, abort
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import *

channel_secret = '4d29fcb0bc85d329492c2fc90fe9986c'
channel_access_token = 'Jj/jv56P7ZEREEIQ5zZ6SmSYksi14BFFLyFDSPjIBxjP4At1nGzaB6PAPxTux55BVVBGC8+SA1aHssHTVfVs3EgADnOIGqWwPuVWay01R/qP9XVv5wy60dmzKIEP3nrJYa4waIfzrHW+bddcYrfJxgdB04t89/1O/w1cDnyilFU='
line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)
tz=pytz.timezone('Asia/Jakarta')

app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
	now = datetime.now(tz).isoformat()
	print(now,event.source.type)
	line_bot_api.reply_message(event.reply_token,TextSendMessage(text=str(now)))

if __name__ == "__main__":
    print(channel_access_token)
    print(channel_secret)
	app.run()
	

	
	
	
	
	
	
	
	
	
	
