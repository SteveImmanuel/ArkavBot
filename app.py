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

def generateTextComponent(textContent,dictionary,source=None,postData=None):
	postAction = None
	if(source=='user'):
		postAction = PostbackAction(label='detail',data=postData)
	return TextComponent(text=textContent,**dictionary,action=postAction)

def generateSeparator(dictionary):
	return SeparatorComponent(**dictionary)

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
										maxResults=15, singleEvents=True,
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

def showAllEvents(events, sourceType):
	allContents = []

	if not events[0]:
		allContents.append(generateTextComponent('No Upcoming Events',jsonObj['title']))
	else:
		allContents.append(generateTextComponent('Upcoming Events',jsonObj['title']))
		i = 0
		for event in events[0]:
			start = parse(event['start'].get('dateTime', event['start'].get('date')))
			end = parse(event['end'].get('dateTime', event['end'].get('date')))
			summary = parseSummary(event['summary'])
			if(i!=0):
				allContents.append(generateSeparator(jsonObj['separator1']))
			summaryBox = BoxComponent(layout='horizontal', contents=[
										generateTextComponent(summary[0],jsonObj['summaryTag1']),
										generateTextComponent(summary[1],jsonObj['summaryContent'],source=sourceType,postData='0 '+str(i))
										])
			dateTimeContent = [generateTextComponent(start.strftime('%a, %-d %b'),jsonObj['date'])]
			if 'dateTime' in event['start']:
				dateTimeContent.append(generateTextComponent(start.strftime('%H:%M')+'-'+end.strftime('%H:%M'),jsonObj['time']))
			dateTimeBox = BoxComponent(layout='horizontal', contents=dateTimeContent)
			allContents.append(summaryBox)
			allContents.append(dateTimeBox)
			i+=1
	
	allContents.append(generateSeparator(jsonObj['separator2']))

	if not events[1]:
		allContents.append(generateTextComponent('No Ongoing Events',jsonObj['title']))
	else:
		allContents.append(generateTextComponent('Ongoing Events',jsonObj['title']))
		i = 0
		for event in events[1]:
			start = parse(event['start'].get('dateTime', event['start'].get('date')))
			end = parse(event['end'].get('dateTime', event['end'].get('date')))
			summary = parseSummary(event['summary'])
			if(i!=0):
				allContents.append(generateSeparator(jsonObj['separator1']))
			summaryBox = BoxComponent(layout='horizontal', contents=[
										generateTextComponent(summary[0],jsonObj['summaryTag2']),
										generateTextComponent(summary[1],jsonObj['summaryContent'],source=sourceType,postData='1 '+str(i))
										])
			dateTimeContent = [generateTextComponent(end.strftime('%a, %-d %b'),jsonObj['date'])]
			if 'dateTime' in event['end']:
				dateTimeContent.append(generateTextComponent(end.strftime('%H:%M'),jsonObj['time']))
			dateTimeBox = BoxComponent(layout='horizontal', contents=dateTimeContent)
			allContents.append(summaryBox)
			allContents.append(dateTimeBox)
			i+=1
	
	bubbleMessage = BubbleContainer(direction='ltr',
									body=BoxComponent(layout='vertical',
													spacing='xs',
													contents=allContents))
	return FlexSendMessage(alt_text='All Events',contents=bubbleMessage)

def showEventDetail(event,type):
	detailContents = []
	summary = parseSummary(event['summary'])
	start = parse(event['start'].get('dateTime', event['start'].get('date')))
	end = parse(event['end'].get('dateTime', event['end'].get('date')))

	key = 'detailTag'+str(type)
	detailContents.append(generateTextComponent(summary[0],jsonObj[key]))
	detailContents.append(generateTextComponent(summary[1],jsonObj['detailTitle']))
	detailContents.append(generateSeparator(jsonObj['separator3']))
	
	detailContents.append(generateTextComponent('Start Time:',jsonObj['detailText']))
	startDateContent = [generateTextComponent(start.strftime('%a, %-d %b'),jsonObj['detailDate'])]
	if 'dateTime' in event['start']:
		startDateContent.append(generateTextComponent(start.strftime('%H:%M'),jsonObj['detailTime']))
	startDateBox = BoxComponent(layout='horizontal',contents=startDateContent)
	detailContents.append(startDateBox)

	detailContents.append(generateTextComponent('End Time:',jsonObj['detailText']))
	endDateContent = [generateTextComponent(start.strftime('%a, %-d %b'),jsonObj['detailDate'])]
	if 'dateTime' in event['end']:
		endDateContent.append(generateTextComponent(end.strftime('%H:%M'),jsonObj['detailTime']))
	endDateBox = BoxComponent(layout='horizontal',contents=endDateContent)
	detailContents.append(endDateBox)

	detailContents.append(generateTextComponent(event.get('description','-'),jsonObj['detailContent']))
	bubbleMessage = BubbleContainer(direction='ltr',body=BoxComponent(layout='vertical',
													spacing='xs',
													contents=detailContents))
	return FlexSendMessage(alt_text='Detail Event',contents=bubbleMessage)													

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
	timeNow = datetime.now(tz).isoformat()
	calendarEvents = getEventsCalendar(timeNow)
	if event.message.text == '/calendar':
		allEvents = showAllEvents(calendarEvents,event.source.type)
		line_bot_api.reply_message(event.reply_token, allEvents)

@handler.add(PostbackEvent)
def handle_postback(event):
	timeNow = datetime.now(tz).isoformat()
	calendarEvents = getEventsCalendar(timeNow)
	data = event.postback.data.split()
	data = list(map(int, data))
	print(str(data))
	if len(data)==2:
		detailEvent = showEventDetail(calendarEvents[data[0]][data[1]],data[0])
		line_bot_api.reply_message(event.reply_token, detailEvent)
	else:
		print('Error: Invalid Postback Data')

if __name__ == "__main__":
	app.run()
	

	
	
	
	
	
	
	
	
	
	
