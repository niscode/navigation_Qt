# -*- config:utf-8 -*-

import time
from threading import Thread
import websocket
from datetime import datetime, timedelta

class LocalWebSocketClient():
    def __init__(self, port) :
        self.websockurl = 'ws://localhost:%d' % port
        self.ws = None
        self.wsThread = None
        self.messageCallback = None
        self.connected = False
        self.closed = False

    def isactive(self):
        return self.connected

    def getUrl(self):
        return self.websockurl

    def close(self) :
        self.connected = False
        self.closed = True
        if not self.ws is None :
            self.ws.close()
        if not self.wsThread is None :
            self.wsThread.join()
        self.ws = None
        self.wsThread = None

    def setMessageCallback(self, func):
        self.messageCallback = func

    def on_messageCB(self, message):
        if message == 'something':
            return
        if not self.messageCallback is None:
            self.messageCallback(message)

    def on_errorCB(self, err):
        pass
        #print("Error :", err)

    def on_openCB(self):
        self.connected = True
        #print("opening")

    def on_closeCB(self):
        self.closed = True
        self.connected = False
        #print("close")

    def send(self, message):
        #print("SEND :", message)
        #print(self.wss.sock.connected)
        self.ws.send(message)

    def connect(self):
        def on_message(ws, message):
            self.on_messageCB(message)

        def on_error(ws, error):
            self.on_errorCB(error)

        def on_open(ws):
            self.on_openCB()

        def on_close(ws, status_code, close_msg):
            #print(status_code, close_msg)
            self.on_closeCB()

        self.closed = False

        self.ws = websocket.WebSocketApp(self.websockurl,
                                        on_message=on_message,
                                        on_error=on_error,
                                        on_open=on_open,
                                        on_close=on_close)

        self.wsThread = Thread(target=self.ws.run_forever)
        self.wsThread.daemon = True
        self.wsThread.start()

        waitstart = datetime.now()
        self.closed = False
        while not self.connected and datetime.now() - waitstart < timedelta(seconds = 30.0):
            time.sleep(0.01)
            if self.closed :
                break
        result = self.connected
        if not self.connected :
            self.close()
        #print(datetime.now() - waitstart)

        return result

'''
# test
if __name__ == '__main__':
    def cb(message):
        print('sutekina ', message)

    #websocket.enableTrace(True)
    wssock = WebSocketCapf('https://atr-dev02.ca-platform.org/api/login',
                           'CA001', 'CA001', 'wss://atr-dev02-websocket.ca-platform.org')
    wssock.setMessageCallback(cb)
    if not wssock.connect():
        print('cannot connect websocket')
        sys.exit(0)
    #wssock.send('test'.encode())

    while True:
        time.sleep(1)
'''
