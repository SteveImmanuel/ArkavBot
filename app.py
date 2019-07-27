import os
import time
import pytz
import pickle
import itertools
import json
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

# channel_access_token='Jj/jv56P7ZEREEIQ5zZ6SmSYksi14BFFLyFDSPjIBxjP4At1nGzaB6PAPxTux55BVVBGC8+SA1aHssHTVfVs3EgADnOIGqWwPuVWay01R/qP9XVv5wy60dmzKIEP3nrJYa4waIfzrHW+bddcYrfJxgdB04t89/1O/w1cDnyilFU='
# channel_secret='4d29fcb0bc85d329492c2fc90fe9986c'

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)
tz=pytz.timezone('Asia/Jakarta')
jsonObj = json.load(open('templateMessage.json','r'))

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

def generateTitle(title):
	return TextComponent(text=title,
						size=jsonObj['title'].get('size'),
						align=jsonObj['title'].get('align'),
						gravity=jsonObj['title'].get('gravity'),
						weight=jsonObj['title'].get('weight'),
						color=jsonObj['title'].get('color')                   
						)

def generateSummary(type,content):
	return TextComponent(text=content,
						flex=jsonObj[type].get('flex'),
						size=jsonObj[type].get('size'),
						margin=jsonObj[type].get('margin'),
						align=jsonObj[type].get('align'),
						gravity=jsonObj[type].get('gravity'),
						weight=jsonObj[type].get('weight'),
						color=jsonObj[type].get('color'),   
						wrap=jsonObj[type].get('wrap')                
						)

def generateDateTime(type,content):
	return TextComponent(text=content,
						size=jsonObj[type].get('size'),
						align=jsonObj[type].get('align'),
						color=jsonObj[type].get('color'),               
						)

def generateSeparator(type):
	return SeparatorComponent(margin=jsonObj[type].get('margin'),
							color=jsonObj[type].get('color')
							)

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
										maxResults=17, singleEvents=True,
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

def parseSummary(text):
	result = []
	endIdx = text.find(']')
	if endIdx==-1:
		result.append('[None]')
		result.append(text)
	else:
		result.append(text[:endIdx+1])
		result.append(text[endIdx+2:])
	return result

def showAllEvents(events):
	allContents = []

	if not events[0]:
		allContents.append(generateTitle('No Upcoming Events'))
	else:
		allContents.append(generateTitle('Upcoming Events'))
		i = 0
		for event in events[0]:
			start = parse(event['start'].get('dateTime', event['start'].get('date')))
			end = parse(event['end'].get('dateTime', event['end'].get('date')))
			summary = parseSummary(event['summary'])
			if(i!=0):
				allContents.append(generateSeparator('separator1'))
			summaryBox = BoxComponent(layout='horizontal', contents=[
										generateSummary('summaryTag1',summary[0]),
										generateSummary('summaryContent',summary[1])
										])
			dateTimeContent = [generateDateTime('date',start.strftime('%a, %-d %b'))]
			if 'dateTime' in event['start']:
				dateTimeContent.append(generateDateTime('time',start.strftime('%H:%M')+'-'+end.strftime('%H:%M')))
			dateTimeBox = BoxComponent(layout='horizontal', contents=dateTimeContent)
			allContents.append(summaryBox)
			allContents.append(dateTimeBox)
			i+=1
	
	allContents.append(generateSeparator('separator2'))

	if not events[1]:
		allContents.append(generateTitle('No Ongoing Events'))
	else:
		allContents.append(generateTitle('Ongoing Events'))
		i = 0
		for event in events[1]:
			start = parse(event['start'].get('dateTime', event['start'].get('date')))
			end = parse(event['end'].get('dateTime', event['end'].get('date')))
			summary = parseSummary(event['summary'])
			if(i!=0):
				allContents.append(generateSeparator('separator1'))
			summaryBox = BoxComponent(layout='horizontal', contents=[
										generateSummary('summaryTag2',summary[0]),
										generateSummary('summaryContent',summary[1])
										])
			dateTimeContent = [generateDateTime('date',end.strftime('%a, %-d %b'))]
			if 'dateTime' in event['end']:
				dateTimeContent.append(generateDateTime('time',end.strftime('%H:%M')))
			dateTimeBox = BoxComponent(layout='horizontal', contents=dateTimeContent)
			allContents.append(summaryBox)
			allContents.append(dateTimeBox)
			i+=1
	
	bubleMessage = BubbleContainer(direction='ltr',
									body=BoxComponent(layout='vertical',
													spacing='xs',
													contents=allContents))
	return FlexSendMessage(alt_text='All Events',contents=bubleMessage)	

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
	timeNow = datetime.now(tz).isoformat()
	calendarEvents = getEventsCalendar(timeNow)
	allEvents = showAllEvents(calendarEvents)
	
	line_bot_api.reply_message(event.reply_token, allEvents)

if __name__ == "__main__":
	app.run()
	

	
	
	
	
	
	
	
	
	
	
