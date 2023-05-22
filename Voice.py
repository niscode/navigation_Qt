# -*- config:utf-8 -*-

#import MySQLdb
import mysql.connector
#from mysql.connector import Error
import MySQLdb
import sys
import os
from re import X
import numpy as np
from datetime import datetime, timedelta
import pyaudio
import azurekey
import azure.cognitiveservices.speech as speechsdk
from datetime import datetime, timedelta
import numpy as np
import os
from pydub import AudioSegment

dbuser = 'capfdb'
dbpasswd = 'capf2021'
dbhost = 'mpc13'
dbport = 3306
dbname = 'recommdb'


class Voice() :
    def __init__(self, length, text, waveData) :
        
        self.rate = 16000
        self.channels = 1
        self.sampleWidth = 2

        self.length = length
        self.text = text
        self.data = waveData

    def setData(self, data) :
        self.data = data

    def speech(self, output_device_index = None) :
        p = pyaudio.PyAudio()
        if output_device_index is None :
            stream = p.open(format=p.get_format_from_width(self.sampleWidth),
                        channels=self.channels,
                        rate=self.rate,
                        output=True)
        else :
            stream = p.open(format=p.get_format_from_width(self.sampleWidth),
                        channels=self.channels,
                        rate=self.rate,
                        output_device_index = output_device_index,
                        output=True)

        stream.write(self.data)
        stream.close()
        p.terminate()

def makeVoices(talkTable, female = True) :
    def makeSsmlString(text, female=True) :
        if female:
            voice = 'ja-JP-NanamiNeural'
        else:
            voice = 'ja-JP-KeitaNeural'
        ssmlHeader = u'<speak version = "1.0" xmlns="https://www.w3.org/2001/10/synthesis" xml:lang="ja-JP">\n <voice name="' + \
        voice + '"> \n '
        ssmlTail = u'\n  </voice>\n</speak>'
       
        return (ssmlHeader + text + ssmlTail)

    resultVoices = []

    r, azure = azurekey.getKeys() #)self.dbhost, self.dbport)
    if r:
        speech_config = speechsdk.SpeechConfig(subscription=azure[1], region=azure[0])
        speech_config.speech_recognition_language = "ja-JP"
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

        pid = os.getpid()
        tmpfile = "./tmp%d.wav" % pid
        for text in talkTable :
            ssml_string = makeSsmlString(text.strip(), female)
            result = synthesizer.speak_ssml_async(ssml_string).get()
            stream = speechsdk.AudioDataStream(result)
            stream.save_to_wav_file(tmpfile)
            vdata = AudioSegment.from_wav(tmpfile)
            vdata = vdata.set_channels(1)
            vdata = vdata.set_frame_rate(16000)
            vdata = vdata.set_sample_width(2)
            v = vdata.raw_data
            length = len(vdata) / 1000.0
            voice = Voice(length, text, v)
            resultVoices.append(voice)
    
        if os.path.isfile(tmpfile) : os.remove(tmpfile)

    return r, resultVoices






        
