from django.db import models

# Create your models here.

class Language(models.Model):
	name = models.CharField(max_length=255)
	langCode = models.CharField(max_length=5)

class Survey(models.Model):
	name = models.CharField(max_length=255)
	shortCode = models.CharField(max_length=50, null=True)
	refId = models.CharField(max_length=255, null=True)
	responseCode = models.CharField(max_length=50)
	startDate = models.DateTimeField()
	endDate = models.DateTimeField()

class SurveyLang(models.Model):
	survey = models.ForeignKey(Survey)
	name = models.CharField(max_length=255)
	description = models.CharField(max_length=255)
	lang = models.ForeignKey(Language)
	welcomeMsg = models.CharField(max_length=255, null=True)

class SurveyAvailableLang(models.Model):
	survey = models.ForeignKey(Survey)
	lang = models.ForeignKey(Language)
	responseCode = models.CharField(max_length=50)

class SurveyPage(models.Model):
	survey = models.ForeignKey(Survey)
	refId = models.CharField(max_length=255)
	branches = models.BooleanField()
	pageOrder = models.IntegerField()

class QuestionType(models.Model):
    name = models.CharField(max_length=100)
    refId = models.CharField(max_length=255)
    multiAnswer = models.BooleanField()
    openEnded = models.BooleanField()
    
class Question(models.Model):
	surveyPage = models.ForeignKey(SurveyPage)
	name = models.CharField(max_length=255)
	questionType = models.ForeignKey(QuestionType)
	responseCode = models.CharField(max_length=50)
	refId = models.CharField(max_length=255)
	questionOrder = models.IntegerField()

class QuestionLang(models.Model):
	question = models.ForeignKey(Question)
	lang = models.ForeignKey(Language)
	text = models.CharField(max_length=255)
	
class QuestionOption(models.Model):
	question = models.ForeignKey(Question)
	responseCode = models.CharField(max_length=50)
	refId = models.CharField(max_length=255)

class QuestionOptionLang(models.Model):
	questionOption = models.ForeignKey(QuestionOption)
	lang = models.ForeignKey(Language)
	text = models.CharField(max_length=255)

class Participant(models.Model):
	survey = models.ForeignKey(Survey)
	lang = models.ForeignKey(Language)
	mobileNumber = models.CharField(max_length=50)
	outNumber = models.CharField(max_length=25)
	refId = models.CharField(max_length=255)
	completed = models.BooleanField()

class ParticipantSurvey(models.Model):
	participant = models.ForeignKey(Participant)
	survey = models.ForeignKey(Survey)
	completed = models.BooleanField()
	startTime = models.DateTimeField()
	completedTime = models.DateTimeField()
	
class ParticipantRecord(models.Model):
	participant = models.ForeignKey(Participant)
	survey = models.ForeignKey(Survey)
	question = models.ForeignKey(Question, null=True)
	questionOption = models.ForeignKey(QuestionOption, null=True)
	text = models.CharField(max_length=1000, null=True)
	erased = models.BooleanField(default=False)
	sentTime = models.DateTimeField()
	receivedTime = models.DateTimeField(null=True)
	langQuestion = models.BooleanField(default=False)

class Answer(models.Model):
	participant = models.ForeignKey(Participant)
	question = models.ForeignKey(Question)
	questionOption = models.ForeignKey(QuestionOption)
	
class OEQAnswer(models.Model):
	participant = models.ForeignKey(Participant)
	question = models.ForeignKey(Question)
	text = models.CharField(max_length=3000)
