import os
import sys
import numpy as np
import scipy.sparse as sp
from datetime import datetime, timedelta
import time
import ctypes
from multiprocessing import Process, Queue, Manager
from threading import Thread
import queue
import sounddevice as sd
from PySide2.QtCore import QTimer, QPoint, QRect, Qt, QThread, QMutex, QMutexLocker, Signal, Slot, QSize, QEvent
from PySide2.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap,  QCloseEvent
from PySide2.QtWidgets import (QApplication, QMainWindow, QComboBox, QHBoxLayout, QLabel, QScrollArea, QProgressBar,
                               QSlider, QCheckBox, QLineEdit,  QListWidget, QListWidgetItem, QMdiArea, QRadioButton,
                               QTabWidget, QMenu, QButtonGroup, QGraphicsView, QGraphicsScene, QTextEdit, QFrame,
                               QMessageBox, QPushButton, QVBoxLayout, QGridLayout, QWidget, QDialog, QFileDialog, QSpacerItem, QSizePolicy)
from tkinter import messagebox
from tkinter import filedialog
import tkinter as tk
import multiprocessing as mp
import configparser
import socket
from websocket_server import WebsocketServer

import speechMemToText as sptxt
import Voice
import azurekey
from websocket_server import WebsocketServer
import WebSocketCapf as cwebsock
import json
import base64
from screeninfo import get_monitors

#WebsocketPort = 9001


def setFontSize(widget, fontSize) :
    font = widget.font()
    font.setPixelSize(fontSize)
    widget.setFont(font)

def checkKey() :
    result = False
    
    try :
        #F13 => 0x7c
        if (ctypes.windll.user32.GetAsyncKeyState(0x7b) & 0x8000) != 0 :
            result = True
    except KeyboardInterrupt :
        pass

    return result

class DeviceSelectCombo(QWidget):
    def __init__(self, title, deviceList, defaultDeviceIdx, parent=None):
        super(DeviceSelectCombo, self).__init__(parent)
        self.deviceList = deviceList
        idx = [x[0] for x in self.deviceList].index(defaultDeviceIdx)
        layout = QHBoxLayout()
        self.label = QLabel(title, self)
        self.comboBox = QComboBox()
        self.comboBox.addItems([x[1] for x in deviceList])
        self.comboBox.setCurrentIndex(idx)

        layout.addWidget(self.label)
        layout.addWidget(self.comboBox)

        self.label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.comboBox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.setLayout(layout)

class VolumeLevelWidget(QWidget) :
    def __init__(self, label) :
        super(VolumeLevelWidget, self).__init__()
        layout = QGridLayout()
        
        self.thresholdVal = 0
        self.levelbar = QProgressBar(self)
        self.levelbar.setValue(0)
        self.levelbar.setMinimum(0)
        self.levelbar.setMaximum(100)
        self.levelbar.setMaximumHeight(10)
        self.levelbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.levelbar.setTextVisible(False)

        self.sliderLabel = QLabel(label)
        self.sliderLabel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.thSlider = QSlider(self)
        self.thSlider.setMinimum(0)
        self.thSlider.setMaximum(100)
        self.thSlider.setOrientation(Qt.Horizontal)
        self.thSlider.setValue(0)
        self.thSlider.setMaximumHeight(10)
        self.thSlider.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.thSlider.valueChanged.connect(self.sliderValueChangeCB)
        self.sliderValueChangedCBFunc = None

        layout.addWidget(self.levelbar, 0, 1)
        layout.addWidget(self.sliderLabel, 1, 0)
        layout.addWidget(self.thSlider, 1, 1)

        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.setLevelValue(0)

    def setSliderValueChangeCallback(self, func) :
        self.sliderValueChangedCBFunc = func

    def setLevelValue(self, val) :
        #print(self.thresholdVal)
        if self.thresholdVal > val / 100 :
            style = 'QProgressBar::chunk {background-color:red}'
        else :
            style = 'QProgressBar::chunk {background-color:lightgreen}'
        self.levelbar.setStyleSheet(style)

        self.levelbar.setValue(val)

    def setThreshold(self, val) :
        self.thSlider.setValue(val * 100)
        self.thresholdVal = val

    def sliderValueChangeCB(self, val) :
        if not self.sliderValueChangedCBFunc is None :
            self.sliderValueChangedCBFunc(val / 100)   

def goodGeom(x, y, width, height) :
    # Rectの四隅のいずれかが画面内なら有効とみなす
    ps = [ (x,y), (x+width,y), (x+width, y+height), (x, y+width) ]
    result = False
    for p in ps :
        for m in get_monitors() :
            p1 = (m.x, m.y)
            p2 = (m.x + m.width, m.y + m.height)

            if p[0] > p1[0] and p[0] < p2[0] and p[1] > p1[1] and p[1] < p2[1] :
                result = True
                break
        if result : break

    return result


class mainWindow(QMainWindow) :
    sound_yes_male = './data/yes-m.wav'
    sound_yes_female = './data//yes-f.wav'

    def __init__(self, default_mic_thresh,
                 azureParam,
                 input_device, virtual_mic_device, output_device,
                 geom, 
                 selfID, opID, capfWebSocket, sotaIP, sotaPort, config, devices) :

        super(mainWindow, self).__init__()

        self.documentInit(default_mic_thresh,
                          azureParam,
                          input_device, virtual_mic_device, output_device,
                          geom,
                          selfID, opID, capfWebSocket, sotaIP, sotaPort, config, devices)
        self.viewInit()

        self.sendAutoReseponseMode(self.autoResponse)

        self.timer = QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.mainSession)
        self.timer.start()

    def documentInit(self, default_mic_thresh,
                     azureParam,
                     input_device, virtual_mic_device, output_device,
                     geom,
                     selfID, opID, capfWebSocket, sotaIP, sotaPort, config, devices) :
        #self.askGender()
        now = datetime.now()
        self.vtype = 1
        self.azureParam = azureParam
        self.mic_threshVal = default_mic_thresh
        self.geom = geom
        self.selfID = selfID
        self.opID = opID
        self.config = config
        self.devices = devices
        self.sotaIP = sotaIP
        self.sotaPort = sotaPort
        self.autoResponse = False

        manager = Manager()
        self.cevent = manager.Event()               # System Close Event
        self.micStopEvent = manager.Event()         # mic Thread stop Event
        self.vmicPlayStopEvent = manager.Event()    # playing to virtual mic device stop Event 
        self.outputPlayStopEvent = manager.Event()  # playing to output device stop Event  
    
        self.cevent.clear()
        self.micStopEvent.clear()
        self.vmicPlayStopEvent.clear()
        self.outputPlayStopEvent.clear()

        self.input_device = input_device
        self.virtual_mic_device = virtual_mic_device
        self.output_device = output_device

        self.micSpeech_queue = Queue()
        self.micThresh_queue = Queue()
        self.micLevel_queue = Queue()

        self.receivedFromWebSocketMessageList = []
        self.actionCmdList = [] 

        self.lastCheckKeyTime = now

        def actionMessageCB(message):
            cmd = message.strip()
            if len(cmd) > 0:
                self.receivedFromWebSocketMessageList.append(cmd)
        
        self.capfWebSocket = capfWebSocket
        self.capfWebSocket.setMessageCallback(actionMessageCB)
        # 自らへダミーメッセージを送信。最初の1回だけ通信が遅いことに対する対症療法 (原因は不明)
        sendmsg = json.dumps({'targets': [self.selfID], 'message': ''})
        self.capfWebSocket.send(sendmsg)

        self.tmpFolder = './tmp'
        self.mainMicThread = Process(target = sptxt.speechProcess,
                                    args = (self.azureParam, self.micStopEvent, 
                                            self.micSpeech_queue, self.micLevel_queue,
                                            default_mic_thresh, self.micThresh_queue,
                                            self.input_device, self.virtual_mic_device, self.tmpFolder))
        #self.mainMicThread.daemon = False
        self.mainMicThread.start()
        self.micThresh_queue.put(self.mic_threshVal)

        '''
        仮想Micや仮想SPEAKERにデータ音声出力するためのプロセス queueにVoiceデータをセットすると指定デバイスに出力される
         sptxt.voicePlayProc(device, queue, cevent)
          device 出力先デバイス
          queue  VoiceDataをセットするためのQueue
          cevent 終了時にsetされるEvent 子プロセス側ではこれがセットされていたら終了処理に入る
        '''
        self.playVoice_mic_queue = Queue()
        self.playVoice_spk_queue = Queue()
        self.playFile_spk_queue = Queue()

        self.micVoicePlayThread = Process(target=sptxt.voicePlayProc, args=(
            self.virtual_mic_device, self.playVoice_mic_queue, self.vmicPlayStopEvent))
        #self.micVoicePlayThread.daemon = True
        self.micVoicePlayThread.start()

        self.spkVoicePlayThread = Process(target=sptxt.voicePlayProc, args=(
            self.output_device, self.playVoice_spk_queue, self.outputPlayStopEvent))
        #self.spkVoicePlayThread.daemon = True
        self.spkVoicePlayThread.start()
        
        self.spkFilePlayThread = Process(target=sptxt.soundPlayProc,
                                       args=(self.output_device, self.playFile_spk_queue, self.outputPlayStopEvent))
        self.spkFilePlayThread.start()

    def viewInit(self) :
        style = 'QWidget{color: white; background-color : black}'
        self.setStyleSheet(style)

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        self.windowLayout = QVBoxLayout()
        self.centralWidget.setLayout(self.windowLayout)

        self.mainWidget = QWidget()

        self.windowLayout.addWidget(self.mainWidget)

        configLayout = QVBoxLayout()
        self.mainWidget.setLayout(configLayout)

        self.inputDeviceCombo = DeviceSelectCombo(
            '物理Micデバイス', self.devices[0], self.input_device)
        self.vMicDeviceCombo = DeviceSelectCombo(
            '仮想Micデバイス', self.devices[1], self.virtual_mic_device)
        self.outputDeviceCombo = DeviceSelectCombo(
            '物理Speakerデバイス', self.devices[1], self.output_device)
        self.inputDeviceCombo.comboBox.currentIndexChanged.connect(self.inputDeviceChanged)
        self.vMicDeviceCombo.comboBox.currentIndexChanged.connect(self.vMicDeviceChanged)
        self.outputDeviceCombo.comboBox.currentIndexChanged.connect(self.outputDeviceChanged)

        self.inputDeviceCombo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.vMicDeviceCombo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.outputDeviceCombo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.micLevelBar = VolumeLevelWidget('Mic')
        self.micLevelBar.setThreshold(self.mic_threshVal)
        self.micLevelBar.setSliderValueChangeCallback(self.micLevelThreshChangeCB)
        self.micLevelBar.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.autoResponseLabel = QLabel('')
        self.autoResponseLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.autoResponseLabel.setAlignment(Qt.AlignCenter)
        self.autoResponseLabelRefresh()

        self.talkText = QTextEdit()
        self.talkText.setReadOnly(True)

        configLayout.addWidget(self.inputDeviceCombo)
        configLayout.addWidget(self.vMicDeviceCombo)
        configLayout.addWidget(self.outputDeviceCombo)
        configLayout.addWidget(self.micLevelBar)
        configLayout.addWidget(self.autoResponseLabel)
        configLayout.addWidget(self.talkText)

        #spacerItem = QSpacerItem(0, 0, vData=QSizePolicy.Expanding)
        #configLayout.addSpacerItem(spacerItem)

    def autoResponseLabelRefresh(self) :
        if self.autoResponse :
            label = '自動応答モード'
        else :
            label = '対話モード'
        self.autoResponseLabel.setText(label)

    def micLevelThreshChangeCB(self, val) :
        self.mic_threshVal = val
        self.micThresh_queue.put(self.mic_threshVal)
        self.micLevelBar.setThreshold(val)

        if not self.config.has_section('input'):
            self.config.add_section('input')
        self.config.set('input', 'micThreshold', str(self.mic_threshVal))

    def outputconfig(self) :
        with open(iniFile, 'w', encoding='utf-8') as file:
            self.config.write(file)

    def joinAllSubProcess(self) :
        if self.mainMicThread:
            self.mainMicThread.join()
        if self.micVoicePlayThread :
            self.micVoicePlayThread.join()
        if self.spkVoicePlayThread:
            self.spkVoicePlayThread.join()

    def closeEvent(self, event) :
        self.cevent.set()
        self.micStopEvent.set()
        self.outputPlayStopEvent.set()
        self.vmicPlayStopEvent.set()
        self.outputconfig()
        self.joinAllSubProcess()

        if not event is None :
            event.accept()

    # デバイスを変更してプロセスを再起動
    def inputDeviceChanged(self, idx):
        self.input_device = self.inputDeviceCombo.deviceList[idx][0]
        self.config.set('device', 'input-device', str(self.input_device))
        self.micStopEvent.set()
        self.mainMicThread.join()
        self.micStopEvent.clear()
        self.mainMicThread = Process(target=sptxt.speechProcess,
                                      args=(self.azureParam, self.micStopEvent, self.micSpeech_queue, self.micLevel_queue, self.mic_threshVal, self.micThresh_queue, self.input_device, self.virtual_mic_device, self.tmpFolder))
        self.mainMicThread.start()

    def vMicDeviceChanged(self, idx):
        self.virtual_mic_device = self.vMicDeviceCombo.deviceList[idx][0]
        self.config.set('device', 'virtual-mic', str(self.virtual_mic_device))
        self.micStopEvent.set()
        self.mainMicThread.join()
        self.micStopEvent.clear()
        self.mainMicThread = Process(target=sptxt.speechProcess,
                                      args=(self.azureParam, self.micStopEvent, self.micSpeech_queue, self.micLevel_queue, self.mic_threshVal, self.micThresh_queue, self.input_device, self.virtual_mic_device, self.tmpFolder))
        self.mainMicThread.start()
        # vMicDeviceが変わったので　micVoicePlayProc も再起動しなくてはいけない
        self.vmicPlayStopEvent.set()
        self.micVoicePlayThread.join()
        self.vmicPlayStopEvent.clear()
        self.micVoicePlayThread = Process(target=sptxt.voicePlayProc,
                                        args=(self.virtual_mic_device, self.playVoice_mic_queue, self.vmicPlayStopEvent))
        self.micVoicePlayThread.start()

    def outputDeviceChanged(self, idx):
        self.output_device = self.outputDeviceCombo.deviceList[idx][0]
        self.config.set('device', 'output-device', str(self.output_device))
        #　outputDeviceが変わったので spkVoicePlayProc も再起動しなくてはいけない
        self.outputPlayStopEvent.set()
        self.spkVoicePlayThread.join()
        self.spkFilePlayThread.join()
        self.outputPlayStopEvent.clear()
        self.spkVoicePlayThread = Process(target=sptxt.voicePlayProc,
                                        args=(self.output_device, self.playVoice_spk_queue, self.outputPlayStopEvent))
        self.spkVoicePlayThread.start()
        self.spkFilePlayThread = Process(target=sptxt.soundPlayProc,
                                       args=(self.output_device, self.playFile_spk_queue, self.outputPlayStopEvent))
        self.spkFilePlayThread.start()

    def drawLevelBar(self) :
        while not self.cevent.is_set():
            try :
                val = self.micLevel_queue.get(False)
                self.micLevelBar.setLevelValue(val)
            except queue.Empty :
                break
    
    def sendCommandToRobot(self, msg, addr, port) :
        def sendMsg(msg, addr, port):
            if msg[-1] != '\n':
                msg = msg + '\n'
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(2.0)
            try:
                client.connect((addr, port))
                client.send(msg.encode('utf-8'))
            except socket.error as e:
                print(addr + ' との通信に失敗しました。', e)
            finally:
                client.close()
                client = None

        sendThread = Thread(target = sendMsg, args=(msg, addr, port))
        sendThread.start()

    
    def mainSession(self) :
        now = datetime.now()
        self.drawLevelBar()

        if not self.capfWebSocket.isactive() :
            if not self.capfWebSocket.connect():
                QMessageBox.information(
                    None, "Error", "WebSocket Connect Error : " + self.capfWebSocket.websockurl, QMessageBox.Ok)
                return
        if self.cevent.is_set() :
            self.closeEvent(None)
            exit(0)
        data = None
        try :
            data = self.micSpeech_queue.get(False)
        except queue.Empty :
            data = None
        if data :
            text, voice, talkStartTime, talkEndTime = data
            self.talk(text)
        
        while len(self.receivedFromWebSocketMessageList) > 0 :
            msg = self.receivedFromWebSocketMessageList.pop(0)
            self.doCapfMessage(msg)
        self.doActionList(now)

        if now - self.lastCheckKeyTime > timedelta(seconds = 1.0) : # チャタリング防止
            if checkKey() :
                self.CallOperator()
            self.lastCheckKeyTime = now

    def sendAutoReseponseMode(self, mode) :
        jsonparam = {'id' : self.selfID, 'mode' : mode}
        jsoncmd = {'cmd' : 'responsemode', 'param' : json.dumps(jsonparam)}
        jsonmsg = {'targets' : [self.opID], 'message' : json.dumps(jsoncmd)}

        self.capfWebSocket.send(json.dumps(jsonmsg))
        self.autoResponseLabelRefresh()

    def CallOperator(self) :      
        jsonparam = {'id' : self.selfID}
        jsoncmd = {'cmd' : 'bell', 'param' : json.dumps(jsonparam)}
        jsonmsg = {'targets' : [self.opID], 'message' : json.dumps(jsoncmd)}

        self.capfWebSocket.send(json.dumps(jsonmsg))

    def talk(self, text) :
        if not text : return

        self.addTalkText(text)
        jsonparam = {'id' : 'Guest', 'text' : text, 'sender' : self.selfID}
        jsoncmd = {'cmd' : 'talk', 'param' : json.dumps(jsonparam)}
        jsonmsg = {'targets' : [self.opID], 'message' : json.dumps(jsoncmd)}
        print(json.dumps(jsonmsg))
        self.capfWebSocket.send(json.dumps(jsonmsg))

    def paramCheck(self, params, keylist) :
        #print("params =",params)
        result = True
        for key in keylist :
            if not key in params.keys() :
                result = False
        return result

    def doCapfMessage(self, message) :
        jsoncmd = json.loads(message)

        #print(jsonmsg['cmd'])

        if self.paramCheck(jsoncmd, ['cmd', 'param']) :
            cmd = jsoncmd['cmd']
            param = json.loads(jsoncmd['param'])
            #print(param)
            if cmd == 'action' :
                if self.paramCheck(param, ['command']) :
                    actCommand = param['command']
                    if actCommand == 'auto_response' :
                        self.autoResponse = True
                        self.sendAutoReseponseMode(True)
                    elif actCommand == 'auto_response_cancel' :
                        self.autoResponse = False
                        self.sendAutoReseponseMode(False)
                    elif actCommand == 'request_status' :
                        self.sendAutoReseponseMode(self.autoResponse)
                    elif actCommand == 'sayyes1' :
                        self.playFile_spk_queue.put(self.sound_yes_male)
                    elif actCommand == 'sayyes2' :
                        self.playFile_spk_queue.put(self.sound_yes_female)
                    else :
                        if self.autoResponse :
                            self.autoResponse = False
                            self.sendAutoReseponseMode(False)
                        self.sendCommandToRobot(actCommand, self.sotaIP, self.sotaPort)
            elif cmd == 'voice' :
                if self.paramCheck(param, ['length', 'text', 'voicedata']) :
                    length = param['length']
                    text = param['text']
                    voicedata = base64.b64decode(param['voicedata'].encode('utf-8'))
                    voice = Voice.Voice(length, text, voicedata)
                    self.playVoice_spk_queue.put(voice)
    def doActionList(self, now) :
        for actions in self.actionCmdList :
            atime = actions[0]
            id = actions[1]
            actionmsg = actions[2]

            if atime < now :
                jsoncmd = {'targets' : [id], 'message' : actionmsg}
                self.capfWebSocket.send(json.dumps(jsoncmd))
                self.actionCmdList.remove(actions)           

    def getClientIndex(self, id) :
        if id in self.ids :
            return self.ids.index(id)
        else :
            return -1

    def addTalkText(self, text) :
        self.talkText.append(text)

def mkDeviceLists(device_list, mmedevices):
    indevices, outdevices = [], []
    for idx, device in enumerate(device_list):
        if not mmedevices is None:
            if not idx in mmedevices:
                continue
        devname = device['name']
        devMaxInput = device['max_input_channels']
        devMaxOutput = device['max_output_channels']
        if devMaxInput > 0:
            indevices.append([idx, devname])
        if devMaxOutput > 0:
            outdevices.append([idx, devname])

    return [indevices, outdevices]

if __name__ == '__main__':
    iniFile = 'mschatcl.ini'
    mp.freeze_support()
    root = tk.Tk()
    root.withdraw()  # ダミーのroot windowを作成してメッセージボックス表示のときにroot windowが作成されないようにする。
    app = QApplication(sys.argv)

    hostapi = sd.query_hostapis()
    mmeDevices = None
    for api in hostapi:
        if api['name'] == 'MME':
            mmeDevices = api['devices']
            break

    device_list = sd.query_devices()
    devices = mkDeviceLists(device_list, mmeDevices)
    idevices = [x[0] for x in devices[0]]
    odevices = [x[0] for x in devices[1]]

    if len(idevices) == 0:
        QMessageBox.information(
            None, "Error", "No input audio device.", QMessageBox.Ok)
        sys.exit(0)
    if len(odevices) == 0:
        QMessageBox.information(
            None, "Error", "No output audio device.", QMessageBox.Ok)
        sys.exit(0)
    input_device, output_device = sd.default.device
    default_input_device, default_output_device = sd.default.device

    if input_device < 0:
        QMessageBox.information(
            None, "Error", "No default input device", QMessageBox.Ok)
        sys.exit(0)
    if output_device < 0:
        QMessageBox.information(
            None, "Error", "No default output device", QMessageBox.Ok)
        sys.exit(0)

    virtual_mic_device = output_device
    default_thresh = 0.1

    azureKey = ''
    azureRegion = ''

    sotaIP = 'localhost'
    sotaPort = 5001

    config = configparser.ConfigParser()
    config.read(iniFile, encoding='utf-8')

    if config.has_section('device'):
        if config.has_option('device', 'virtual-mic'):
            dev = int(config.get('device', 'virtual-mic'))
            if device_list[dev]['max_output_channels'] > 0:
                virtual_mic_device = dev
        if config.has_option('device', 'input-device'):
            dev = int(config.get('device', 'input-device'))
            if device_list[dev]['max_input_channels'] > 0:
                input_device = dev
        if config.has_option('device', 'output-device'):
            dev = int(config.get('device', 'output-device'))
            if device_list[dev]['max_output_channels'] > 0:
                output_device = dev

    if config.has_section('input'):
        if config.has_option('input', 'micthreshold'):
            default_thresh = float(config.get('input', 'micthreshold'))
        '''
        if config.has_option('input', 'spkthreshold'):
            default_thresh2 = float(config.get('input', 'spkthreshold'))
        '''
    posx, posy = 0, 0
    mainWidth, mainHeight = 1200, 800
    if config.has_section('geom'):
        if config.has_option('geom', 'posx'):
            posx = int(config.get('geom', 'posx'))
        if config.has_option('geom', 'posy'):
            posy = int(config.get('geom', 'posy'))
        if config.has_option('geom', 'width'):
            mainWidth = int(config.get('geom', 'width'))
        if config.has_option('geom', 'height'):
            mainHeight = int(config.get('geom', 'height'))
    else:
        config.add_section('geom')

    if not goodGeom(posx, posy, mainWidth, mainHeight):
        posx, posy = 0, 0
        mainWidth = 1200
        mainHeight = 800

    config.set('geom', 'posx', str(posx))
    config.set('geom', 'posy', str(posy))
    config.set('geom', 'width', str(mainWidth))
    config.set('geom', 'height', str(mainHeight))

    geom = QRect(posx, posy, mainWidth, mainHeight)

    selfID = 'CA002'
    selfIDPasswd = ''
    opID = 'OP001SA'
    capfloginserver = 'https://atr-dev02.ca-platform.org/api/login'
    capfwebsockserver = 'wss: // atr-dev02-websocket.ca-platform.org'

    if config.has_section('CAplatform'):
        if config.has_option('CAplatform', 'id'):
            selfID = config.get('CAplatform', 'id')
        if config.has_option('CAplatform', 'idpasswd'):
            selfIDPasswd = config.get('CAplatform', 'idpasswd')
        if config.has_option('CAplatform', 'webid'):
            webID = config.get('CAplatform', 'webid')
        if config.has_option('CAplatform', 'websocketloginserver'):
            capfloginserver = config.get('CAplatform', 'websocketloginserver')
        if config.has_option('CAplatform', 'websocketserver'):
            capfwebsockserver = config.get('CAplatform', 'websocketserver')
    else:
        config.add_section('CAplatform')
    config.set('CAplatform', 'id', selfID)
    config.set('CAplatform', 'idpasswd', selfIDPasswd)
    config.set('CAplatform', 'opid', opID)
    config.set('CAplatform', 'websocketloginserver', capfloginserver)
    config.set('CAplatform', 'websocketserver', capfwebsockserver)

    if not input_device in idevices:
        if default_input_device >= 0:
            input_device = default_input_device
        else:
            input_device = idevices[0]
    if not output_device in odevices:
        if default_output_device >= 0:
            output_device = default_output_device
        else:
            output_device = odevices[0]

    if not virtual_mic_device in odevices:
        virtual_mic_device = odevices[0]

    input_device_name = device_list[input_device]['name']
    virtual_mic_device_name = device_list[virtual_mic_device]['name']
    output_device_name = device_list[output_device]['name']
    if not config.has_section('device'):
        config.add_section('device')
    config.set('device', 'virtual-mic', str(virtual_mic_device))
    config.set('device', 'input-device', str(input_device))
    config.set('device', 'output-device', str(output_device))

    if not config.has_section('input'):
        config.add_section('input')
    config.set('input', 'micthreshold', str(default_thresh))

    if config.has_section('control'):
        if config.has_option('control', 'robotIP'):
            sotaIP = config.get('control', 'robotIP')
        if config.has_option('control', 'robotPort'):
            sotaPort = int(config.get('control', 'robotPort'))
    else:
        config.add_section('control')
    config.set('control', 'robotIP', sotaIP)
    config.set('control', 'robotPort', str(sotaPort))


    r, azure = azurekey.getKeys()
    if not r:
        QMessageBox.information(
            None, "Error", "Get Azure Key Failed", QMessageBox.Ok)
        sys.exit(0)

    azureRegion, azureKey = azure

    with open(iniFile, 'w', encoding='utf-8') as file:
        config.write(file)

    azureParam = [azureKey, azureRegion]

    websocket = cwebsock.WebSocketCapf(capfloginserver, selfID, selfIDPasswd, capfwebsockserver)
    if not websocket.connect():
        QMessageBox.information(
            None, "Error", "WebSocket Connect Error : " + capfwebsockserver, QMessageBox.Ok)
        sys.exit()

    dialogWindow = mainWindow(default_thresh,
                                    azureParam,
                                    input_device, virtual_mic_device, output_device,
                                    geom,
                                    selfID, opID, websocket,
                                    sotaIP, sotaPort,
                                    config, devices)
    dialogWindow.show()

    sys.exit(app.exec_())
