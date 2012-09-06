from RICSMS.ric.models import *
from datetime import datetime
import rapidsms.apps
import time


class App(rapidsms.apps.base.AppBase):


	def handle (self, message):
	
		""" ****************** """
		""" CREATE PARTICIPANT """
		""" ****************** """	
		def createParticipant(self, message):
			""" New Participant. Get survey from text and make sure it exists. """ 			
			surveyCode = message.text.lower()
			surveyChk = Survey.objects.filter(responseCode=surveyCode)
			
			if (surveyChk):
				survey = surveyChk[0]
				""" For now set language statically """
				lang = Language.objects.filter(id=1)[0]

				# TODO - check if survey is not yet active or has expired 
				
				""" Display Welcome message if it exists """ 
				surveyLang = SurveyLang.objects.filter(survey=survey, lang=lang)[0]
				welcomeMsg = surveyLang.welcomeMsg
				if (welcomeMsg):
					message.respond(surveyLang.welcomeMsg)
					time.sleep(1)

				participant = Participant(
					mobileNumber=message.peer,
					survey=survey,
					lang=lang)
				participant.save()

				self.debug("New Participant. Creating new entry with surveyId: " + str(survey.id))

				""" Check if we need to send the survey selection question """
				availableLangs = SurveyAvailableLang.objects.filter(survey=survey)
				if (availableLangs):
					if(len(availableLangs) > 1):
						"""  User has to send back language selection """
						langStr = ""
						for lng in availableLangs:
							langStr += "(" + lng.responseCode + "): " + lng.lang.name + " "
						message.respond(langStr)

						"""  Record the outgoing message. Note we are expecting a response to the lang question """
						ParticipantRecord(
							participant=participant,
							survey=survey,
							sentTime=datetime.now(),
							langQuestion=True).save()
					else:
						""" Only one option for the language. Set the participant language and send the first question """
						participant.lang = availableLangs[0].lang
						participant.save()
						processAnswer(self, message, participant)

			else:
				""" If the survey doesn't exists then we return """
				self.debug("Participant not found. No valid survey passed")
				# TODO - send error message
				return True

			return True

		""" ************** """
		""" PROCESS ANSWER """
		""" ************** """
		def processAnswer(self, message, participant):
			participantRecordList = ParticipantRecord.objects.exclude(receivedTime__isnull=False).filter(participant=participant).order_by('-sentTime')
			if(not participantRecordList):
				sendQuestion(self, participant)
				return True
			else:
				participantRecord = participantRecordList[0]
				question = participantRecord.question
				survey = participantRecord.survey
				participant= participantRecord.participant
				
				""" Check if it's a Language Question """
				if (participantRecord.langQuestion):
					availableLangs = SurveyAvailableLang.objects.filter(survey=survey)
					if (availableLangs):
						matched = False
						for lng in availableLangs:
							if (lng.responseCode == message.text.strip()):
								matched = True
								participant.lang = lng.lang
								participant.save()
								participantRecord.receivedTime = datetime.now()
								participantRecord.text = message.text.strip()
								participantRecord.save()
								break
						
						""" If we matched the lang question then send the first question """
						if (matched):
							sendQuestion(self, participant)
							return True
						else:
							self.debug("Unable to match expected language response to valid language")
							#TODO update this to resolve the language automatically
							message.respond("Sorry, we do not understand your response. Please re-read the answer options in our previous text and try again.")
							return True	
					else:
						self.debug("Unable to locate any available language when expecting some")
				elif (question.questionType.openEnded):
					""" OEQ Question """
					participantRecord.receivedTime = datetime.now()
					participantRecord.text = message.text.strip()
					participantRecord.save()
					OEQAnswer(
						participant=participant,
						question=question,
						text = message.text.strip()).save()
					sendQuestion(self, participant, question)
					return True
				else:
					""" Multiple Choice Question """
					qOptions = QuestionOption.objects.filter(question=question)
					if (question.questionType.multiAnswer):
						self.debug("Multi-Answer Question")
						# TODO implement multi-answer
					else:
						msg = message.text.strip()
						matched = False
						for qo in qOptions:
							if (qo.responseCode.strip() == msg):
								matched = True
								participantRecord.receivedTime = datetime.now()
								participantRecord.text = message.text.strip()
								participantRecord.questionOption = qo
								participantRecord.save()
								Answer(
									participant=participant,
									question = question,
									questionOption = qo
									).save()
								break
						if (matched):
							sendQuestion(self, participant, question)
							return True
						else:
							self.debug("Response didn't match expected")
							#TODO update this to resolve the language automatically
							message.respond("Sorry, we do not understand your response. Please re-read the answer options in our previous text and try again.")
			return True
		
		
		def sendQuestion(self, participant, prevQuestion=None):
			survey = participant.survey
			
			""" Check if we have already sent a question """
			if (prevQuestion is None):
				self.debug("Getting the first page of the Survey")
				surveyPage = SurveyPage.objects.filter(survey=survey).order_by("pageOrder")[0]
				question = Question.objects.filter(surveyPage=surveyPage).order_by("questionOrder")[0]
			else:
				surveyPage = prevQuestion.surveyPage
				questionRec = Question.objects.filter(surveyPage=surveyPage, questionOrder__gt=prevQuestion.questionOrder).order_by("questionOrder")
				if (not questionRec):
					""" Move on to the next page, if it exists """
					self.debug("Moving on to next page")
					newPageRec = SurveyPage.objects.filter(survey=survey, pageOrder__gt=surveyPage.pageOrder).order_by("pageOrder")
					
					if (not newPageRec):
						""" We have reached the end of the survey """
						self.debug("End of survey reached")
						#TODO send closing message 
						participant.completed=True
						participant.save()
						transferResponses(self, participant)
						message.respond("Thank you for completing the survey. Please visit reliableinsight.com for more information.")
						return True
					else:
						newPage = newPageRec[0]
						question = Question.objects.filter(surveyPage=newPage).order_by("questionOrder")[0]
				else:
					question = questionRec[0]
			""" We now have the question that we wish to send. Get question options and send to participant """
			questionTextRec = QuestionLang.objects.filter(question=question, lang=participant.lang)
			questionText = questionTextRec[0].text
			questionOptions = QuestionOption.objects.filter(question=question)
			
			for qo in questionOptions:
				qol = QuestionOptionLang.objects.filter(questionOption=qo, lang=participant.lang)
				questionText += "\n" + qol[0].text + "  "
			
			message.respond(questionText)
			self.debug("Sending - TO: " + message.peer + " \n MESSAGE : " + questionText)
			"""  Record the outgoing message. """
			ParticipantRecord(
				participant=participant,
				survey=survey,
				question=question,
				sentTime=datetime.now(),
				langQuestion=False).save()
			return True
	
		def transferResponses(self, participant):
			pass
	
		
		""" ************************** """
		""" *** MAIN PROGRAM START *** """
		""" ************************** """
		
		
	
		""" Check if the participant already exists """
		mobileNumber = message.peer;
		participantChk = Participant.objects.filter(mobileNumber=mobileNumber)
		if participantChk: 
			""" Participant exists. If they are not already completed store their current answer and send the next question. """ 
			participant = participantChk[0]
			
			if (participant.completed):
				""" TODO remove this code when replacing repeat functionality """
				""" New Participant. Get survey from text and make sure it exists. """ 			
				surveyCode = message.text.lower()
				surveyChk = Survey.objects.filter(responseCode=surveyCode)
				
				if (surveyChk):
					survey = surveyChk[0]
					""" For now set language statically """
					lang = Language.objects.filter(id=1)[0]
	
					# TODO - check if survey is not yet active or has expired 
					
					""" Display Welcome message if it exists """ 
					surveyLang = SurveyLang.objects.filter(survey=survey, lang=lang)[0]
					welcomeMsg = surveyLang.welcomeMsg
					if (welcomeMsg):
						message.respond(surveyLang.welcomeMsg)
						time.sleep(1)
					participant.completed=False
					participant.save()
					sendQuestion(self, participant)
				else: 
					message.respond("Thank you for completing the survey. Please visit reliableinsight.com for more information.")
				return True
			
			self.debug("Participant " + mobileNumber + " exists. ID: " + str(participant.id))
			processAnswer(self, message, participant)
		else:
			""" Participant doesn't exist. Call createParticipant() """
			createParticipant(self, message)
			
		return True
		
	
	
	""" RapidSMS Function - NOT CURRENTLY USED """
	def start(self):
		#self.modem = pygsm.GsmModem(port="/dev/ttyUSB0", baudrate="115200")
		pass
    
	def parse (self):
		pass
    
	def cleanup (self, message):
		"""Perform any clean up after all handlers have run in the cleanup phase."""
		pass

	def outgoing (self, message):
		"""Handle outgoing message notifications."""
		pass

	def stop (self):
		"""Perform global app cleanup when the application is stopped."""
		pass
