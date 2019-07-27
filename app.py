import os
import time
import pytz
import pickle
import itertools
from datetime import datetime, timedelta
from dateutil.parser import parse
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from flask import Flask, request, abort
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import *

channel_secret = os.getenv('CHANNEL_SECRET', None)
channel_access_token = os.getenv('CHANNEL_ACCESS', None)
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

def getEventsCalendar(timeNow): 
    #returns array of events, index 0 = upcoming events, 1 = ongoing events
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    creds = None
    if os.path.exists('static/token.pickle'):
        with open('static/token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'static/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open('static/token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    events_result = service.events().list(calendarId='std.stei.itb.ac.id_ei3au2vrl6ed3tj4rpvqa3sc10@group.calendar.google.com', 
                                        timeMin=timeNow,
                                        maxResults=25, singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])
    
    result = []
    default = []
    ongoing = []
    for event in events:
        start = parse(event['start'].get('dateTime', event['start'].get('date')))
        end = parse(event['end'].get('dateTime', event['end'].get('date')))
        start = start.replace(tzinfo=tz)
        end = end.replace(tzinfo=tz)
        if(end-start>timedelta(days=1) and start<=parse(timeNow)):
            ongoing.append(event)
        else:
            default.append(event)
    result.append(default)
    result.append(ongoing)
    return result	

def multipleAppend(*args):
    result = []
    for arg in args:
        result.append(arg)
    return result

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    timeNow = datetime.now(tz).isoformat()
    events = getEventsCalendar(timeNow)
    replyMessage = ''
    
    if not events[0]:
        replyMessage += ('No Upcoming Events')
    else:
        replyMessage += ('Upcoming Events\n')
        for event in events[0]:
            start = parse(event['start'].get('dateTime', event['start'].get('date')))
            end = parse(event['end'].get('dateTime', event['end'].get('date')))
            replyMessage += event['summary']+'\n'+start.strftime('%a, %-d %b')+'\n\n'
    
    if not events[0]:
        replyMessage += ('No Ongoing Events')
    else:
        replyMessage += ('Ongoing Events')
        for event in events[1]:
            start = parse(event['start'].get('dateTime', event['start'].get('date')))
            end = parse(event['end'].get('dateTime', event['end'].get('date')))
            replyMessage += event['summary']+'\n'+start.strftime('%a, %-d %b')+'\n\n'
    
    line_bot_api.reply_message(event.reply_token,TextSendMessage(text=replyMessage))

if __name__ == "__main__":
    app.run()
    

    
    
    
    
    
    
    
    
    
    
