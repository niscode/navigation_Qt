#!/usr/bin/env python3
# -*- config:utf-8 -*-

import sys
import os
from math import atan2, pi

from PySide2.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QGraphicsScene, QGraphicsView, QWidget, QLabel, QTextEdit, QTextBrowser, QLineEdit, QSpacerItem, QSizePolicy, QMessageBox, QSlider, QGridLayout, QProgressBar)
from PySide2.QtCore import (Qt, QPoint, QRectF, QPointF, QRect, QTimer)
from PySide2.QtGui import QPixmap, QImage, QPainter, QBrush, QFont, QTransform

import WebSocketCapf as cwebsock
import json
from datetime import datetime
import math

from playsound import playsound
# pip install playsound==1.2.2
chimefile = '/Users/shogo/chime.wav'    # ファイル名は絶対パスで書く

selfID = 'OP002SA'
#targetID = 'CA003'
targetID = 'CA004'

WAYPOINT_X = []
WAYPOINT_Y = []
SELF_X = SELF_Y = SELF_YAW = 0



class MapView(QGraphicsView):
    def __init__(self, parent=None):
        super(MapView, self).__init__(parent=parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.backgroundImage = None
        self.goalImage = 'goal.png'        # 'goal2.png'
        self.selfImage = 'selfpos.png'
        self.sendInputCB = None
        self.sendGoalCB = None
        self.markerPoint = [0, 0]

    def setImage(self, bgImage):
        self.backgroundImage = bgImage
        sz = self.backgroundImage.size()
        self.markerPoint = [sz.width() // 2, sz.height() // 2]

    # クリックした座標を取得
    def setSendInputCB(self, func):
        self.sendInputCB = func

    # クリックした座標がナビゲーションポイントだった場合、指令値を送る
    def setSendGoalCB(self, func):
        self.sendGoalCB = func

    # マウスによるクリックイベントを検知
    def mousePressEvent(self, event):
        qp = self.mapToScene(event.x(), event.y())
        tx, ty = qp.x(), qp.y()
        print(f"[地図上のクリックを検出]   {tx}, {ty}")
        self.setMarkerPoint(tx, ty)
        if not self.sendInputCB is None:
            self.sendInputCB(tx, ty)

        # 設置したマーカの座標周辺がクリックされた場合、ナビゲーションの指令を送る
        if len(WAYPOINT_X) != 0:
            print("目標位置周辺かどうかをチェック!")
            for i in range(len(WAYPOINT_X)):
                # print(WAYPOINT_X[i], WAYPOINT_Y[i])
                if (WAYPOINT_X[i]-50) < tx <= (WAYPOINT_X[i]+50) and (WAYPOINT_Y[i]-50) < ty <= (WAYPOINT_Y[i]+50) :
                    if not self.sendGoalCB is None:
                        self.sendGoalCB(i)
                        print("[Send params]   goal_num: " + str(i + 1))
                    break

    ## マーカーを描画
    def setMarkerPoint(self, x, y):
        self.markerPoint = [x, y]
        self.update()

    def paintEvent(self,event):
        super().paintEvent(event)
        self.repaint()

    # クリックした地点の描画
    def repaint(self):
        if self.backgroundImage:
            # print("   ... executing repaint ...   ")
            text = 'here'
            tmpimg = QImage(self.backgroundImage)
            painter = QPainter()
            painter.begin(tmpimg)
            painter.setPen(Qt.red)
            brush = QBrush(Qt.red, bs=Qt.SolidPattern)
            painter.setBrush(brush)
            painter.translate(self.markerPoint[0], self.markerPoint[1])
            painter.drawEllipse(-10, -10, 20, 20)
            self.mapLabel(painter, text)    # テキストを表示

            # waypointが取得された時
            if len(WAYPOINT_X) != 0:
                # print(WAYPOINT_X, WAYPOINT_Y)
                # self.putMarker(tmpimg)
                # ウェイポイントの画像
                goalimg = QPixmap.fromImage(self.goalImage)
                goalimg = goalimg.scaled(80, 80, Qt.KeepAspectRatio)
                # 画像とテキストを表示
                painter.setFont(QFont('Arial', 15))
                for i in range(len(WAYPOINT_X)):
                    text = "地点" + str(i+1)
                    # 画像の描画
                    painter.drawPixmap(WAYPOINT_X[i]-40-self.markerPoint[0], WAYPOINT_Y[i]-60-self.markerPoint[1], goalimg)
                    # 注釈文字の描画
                    painter.drawText(WAYPOINT_X[i]-38-self.markerPoint[0], WAYPOINT_Y[i]+8-self.markerPoint[1], 150, 60, Qt.AlignVCenter, text)

            # 自己位置が取得された時
            if SELF_X != 0:
                # self.selfPos(tmpimg)
                # 自己位置の画像
                selfimg = QPixmap.fromImage(self.selfImage)
                t = QTransform()
                t.rotateRadians(SELF_YAW)
                t.scale(0.15, 0.15)
                selfimg = selfimg.transformed(t)
                painter.drawPixmap(SELF_X-64-self.markerPoint[0], SELF_Y-64-self.markerPoint[1], selfimg)
            painter.end()
            painter = None

            pixmap = QPixmap.fromImage(tmpimg)
            tmpimg = None
            self.scene.clear()
            self.scene.addPixmap(pixmap)
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    # waypointsのマーカを設置する
    def putMarker(self, bg):
        # ゴール地点の画像
        goalimg = QPixmap.fromImage(self.goalImage)
        goalimg = goalimg.scaled(80, 80, Qt.KeepAspectRatio)

        # 画像とテキストを表示
        goal_painter = QPainter()
        goal_painter.begin(bg)
        goal_painter.setPen(Qt.red)
        goal_painter.setFont(QFont('Arial', 15))
        for i in range(len(WAYPOINT_X)):
            text = "地点" + str(i+1)
            # 画像の描画
            goal_painter.drawPixmap(WAYPOINT_X[i]-40, WAYPOINT_Y[i]-60, goalimg)
            # 注釈文字の描画
            goal_painter.drawText(WAYPOINT_X[i]-38, WAYPOINT_Y[i]+8, 150, 60, Qt.AlignVCenter, text)
            ## 円の描画
            # center = QPoint(WAYPOINT_X[i], WAYPOINT_Y[i])
            # goal_painter.drawEllipse(center, 50, 50)
            ### 矩形の描画
            # goal_painter.setBrush(Qt.NoBrush)
            # rectangle = QRectF(WAYPOINT_X[i]-50, WAYPOINT_Y[i]-50, 100, 100)
            # goal_painter.drawRect(rectangle)
        goal_painter.end()
        # goal_painter = None


    # 自己位置のマーカを設置する
    def selfPos(self, bg):
        # 自己位置の画像
        selfimg = QPixmap.fromImage(self.selfImage)
        # selfimg = selfimg.scaled(80, 80, Qt.KeepAspectRatio)

        t = QTransform()
        t.rotate(SELF_YAW)
        t.scale(0.15, 0.15)
        selfimg = selfimg.transformed(t)

        self_painter = QPainter()
        self_painter.begin(bg)
        self_painter.setPen(Qt.red)
        # 画像を描画
        # pos_center = QPoint(SELF_X-64, SELF_Y-64)
        # self_painter.drawPixmap(pos_center, selfimg)    # 位置を補正しラベルを表示
        # 画像の表示場所を指定

        # r = QRect(SELF_X-64, SELF_Y-64, 80, 5)
        self_painter.drawPixmap(SELF_X-64, SELF_Y-64, selfimg)

        # rectangle = QRectF(20, 10, 20, 20)
        # self_painter.drawRect(rectangle)

        # self_painter = self_painter.transformed()
        # self_painter.rotate(45)
        # self_painter.rotateRadius(0.785)

        self_painter.end()
        # self_painter = None
        # print("自己位置表示済み...　　")

    def mapLabel(self, painter, text):
        # text = 'ここにいる'
        painter.setFont(QFont('Arial', 15))
        painter.drawText(-32, 5, 150, 60, Qt.AlignVCenter, text)
        return self    # この返り値がないと動かない


class mainView(QMainWindow) :
    def __init__(self):
        super().__init__()
        self.setWindowTitle("水道橋Map")
        self.resize(1200, 720)
        self.font = QFont("Arial", 20)

        # 先にwebsocket周りを定義して別スレッドで回す
        self.messageBuffer = []     # 別スレッドで動作するwebsocketによるメッセージを溜めておくためのリスト

        self.loginurl = 'https://atr-dev02.ca-platform.org/api/login'
        self.websockurl = 'wss://atr-dev02-websocket.ca-platform.org'
        # self.loginurl = 'https://atr-dev01.ca-platform.org/api/login'
        # self.websockurl = 'wss://atr-dev01-websocket.ca-platform.org'
        self.accountid = selfID
        self.accountpswd = selfID
        self.capfWebSocket = cwebsock.WebSocketCapf(self.loginurl, self.accountid, self.accountpswd, self.websockurl)

        self.capfWebSocket.setMessageCallback(self.recvWebMessageCB)    # サーバ(CA)からROSの情報を取得
        if not self.capfWebSocket.connect():
            QMessageBox.information(
                None, "Error", "WebSocket Connect Error : " + self.websockurl, QMessageBox.Ok)
            self.close()
            sys.exit()

        # UI / バッテリー残量
        self.battery = QProgressBar()
        self.battery.setRange(10, 28)
        self.batteryImage = QPixmap("battery.png")
        self.battery_label = QLabel()
        self.batteryImage = self.batteryImage.scaled(30, 30, Qt.KeepAspectRatio)
        self.battery_label.setPixmap(self.batteryImage)
        self.battery_value = QLabel("20.0")
        self.battery_value.setFont(self.font)

        self._image_size = (1451, 668)
        self._origin = (-55.859167, -11.171094)
        self._map_resolution = 0.05

        # UI / シリンダー昇降ボタン
        self.cylinder_slider = QSlider(Qt.Vertical)
        self.cylinder_slider.setTickPosition(QSlider.TicksBelow)
        self.cylinder_slider.setTickInterval(20)
        self.cylinder_slider.setMinimum(2)
        self.cylinder_slider.setMaximum(292)
        self.cylinder_slider.valueChanged.connect(self.changedValue)

        self.cylinder_label = QLabel("100")
        self.cylinder_label.setText(str(2))
        self.cylinder_label.setFont(self.font)
        self.cylinder_label.setAlignment(Qt.AlignCenter | Qt.AlignBottom)

        self.cylinder_button = QPushButton("更新")
        self.cylinder_button.setFont(self.font)
        self.cylinder_button.clicked.connect(self.update_height)

        # UI / ログ表示ボックス
        self.log_box = QLabel("LOG here ...")
        self.label_style = """QLabel {
            font: Arial;
            color: #383838;                /* 文字色 */
            font-size: 20px;               /* 文字サイズ */
            background-color:#e6e4ca;
            border-radius:4px;
            align-center;
        }"""
        self.log_box.setStyleSheet(self.label_style)
        self.log_box.setAlignment(Qt.AlignTop)


        # UI / サーバからwaypointsを取得するためのボタン
        self.waypoint_button = QPushButton("waypointを取得")
        self.waypoint_button.setFont(self.font)
        self.waypoint_button.clicked.connect(self.waypointRequest)   # waypoints取得リクエストを送信

        self.mapImage = MapView()
        self.mapImage.setSendInputCB(self.sendInput)
        self.mapImage.setSendGoalCB(self.sendGoal)

        dummy_l = 0.0
        for _ in range(10):
            dummy_l = _
            self.sendRequest(dummy_l)    ## 何かを送りつけるテスト

        top = QHBoxLayout()
        top.addWidget(self.battery_label)
        top.addWidget(self.battery)
        top.addWidget(self.battery_value)

        side = QGridLayout()
        side.addWidget(self.cylinder_label, 1, 0)
        side.addWidget(self.cylinder_slider, 1, 1, 2, 1)
        side.addWidget(self.cylinder_button, 2, 0)
        side.addWidget(self.log_box, 3, 0, 5, 3)

        main = QVBoxLayout()
        main.addLayout(top)
        main.addWidget(self.mapImage)
        main.addWidget(self.waypoint_button)

        parentLayout = QHBoxLayout()   # 水平方向にUIを並べる
        parentLayout.addLayout(main)
        parentLayout.addLayout(side)

        mainWidget = QWidget()
        mainWidget.setLayout(parentLayout)
        self.setCentralWidget(mainWidget)
        self.show()

        # サーバ(CA)からROSの情報を取得して描画内容を更新するための処理
        self.timer = QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.messageSession)
        self.timer.start()

    ### サーバ(CA)からROSの情報を取得
    def recvWebMessageCB(self, message):
        self.messageBuffer.append(message)

    def messageSession(self) :
        # self.mapImage.update()
        self.mapImage.repaint()
        if len(self.messageBuffer) > 0 :
            message = self.messageBuffer.pop(0)
            self.doMessage(message)

    def doMessage(self, message) :
        global WAYPOINT_X, WAYPOINT_Y, SELF_X, SELF_Y, SELF_YAW
        jsoncmd = json.loads(message)

        # waypointのリストを取得
        if 'mpos_x' in jsoncmd.keys():
            print("[ROS][WAYPOINTS] x:   " + str(jsoncmd['mpos_x']))
            print("[ROS][WAYPOINTS] y:   " + str(jsoncmd['mpos_y']))
            print("[ROS][WAYPOINTS] yaw: " + str(jsoncmd['mori_z']))
            print("[ROS][WAYPOINTS] q:   " + str(jsoncmd['mori_w']))
            WAYPOINT_X = jsoncmd['mpos_x']
            WAYPOINT_Y = jsoncmd['mpos_y']
            self.xy_transform(WAYPOINT_X, WAYPOINT_Y)

        # telecoの状態を取得
        if 'voltage' in jsoncmd.keys():
            dt = datetime.now()
            tv = jsoncmd['voltage']
            tx = jsoncmd['pos_x']
            ty = jsoncmd['pos_y']
            rx = jsoncmd['ori_x']
            ry = jsoncmd['ori_y']
            rz = jsoncmd['ori_z']
            rw = jsoncmd['ori_w']
            log_info = ("[ROS][INFO]\n 【" + dt.strftime('%Y/%m/%d %H:%M:%S') + " 】\n [power]   " + str(round(tv, 4)) + ",\n [pos x]   " + str(round(tx, 4)) + ",\n [pos y]   " + str(round(ty, 4)) + ",\n [pos z]   " + str(round(jsoncmd['pos_z'], 4)) + ",\n [rot z]   " + str(round(rz, 4)) + ",\n [rot w]   " + str(round(rw, 4)))
            print(log_info)

            self.battery.setValue(tv)        # UIにバッテリー残量を表示
            self.battery_value.setText(str(round(tv, 1)))
            self.log_box.setText(log_info)   # UIにログを表示

            # 地図上に自己位置を描画するための座標変換
            origin_px: (int, int) = (int(self._origin[0] / self._map_resolution) * -1,
                                     self._image_size[1] + int(self._origin[1] / self._map_resolution))
            position_px_offset = self._coord_to_px_offset(self._image_size, origin_px, self._map_resolution, (tx, ty))
            SELF_X = origin_px[0] + position_px_offset[0]
            SELF_Y = origin_px[1] - position_px_offset[1]
            #SELF_YAW = round((tz * -2.8158 + 1.9479)*180/math.pi, 2)
            SELF_YAW = atan2(2.0 * (rw * rz + rx * ry), rw * rw + rx * rx - ry * ry - rz * rz)
            SELF_YAW = SELF_YAW if SELF_YAW > 0.0 else 2 * pi + SELF_YAW
            SELF_YAW = SELF_YAW if SELF_YAW <= 2 * pi else SELF_YAW - 2 * pi
            SELF_YAW = 2 * pi - SELF_YAW
            SELF_YAW += pi / 2

        if 'cylinder_move' in jsoncmd.keys():
            print("[ROS][CYLINDER] :   " + str(jsoncmd['cylinder_move']))

        if self.paramCheck(jsoncmd, ['cmd', 'param']):
            cmd = jsoncmd['cmd']
            param = json.loads(jsoncmd['param'])
            if cmd == 'bell':
                if self.paramCheck(param, ['id']):
                    print("[USB Button] - calling from " + str(param['id']))
                    playsound(chimefile)

    def setImage(self, img) :
        self.mapImage.setImage(img)
        self.mapImage.repaint()

    def sendInput(self, x, y) :
        jsonparam = {'x' : x, 'y' : y}
        jsoncmd = {'cmd' : 'position', 'param' : json.dumps(jsonparam)}
        jsonmsg = {'targets' : targetID, 'message' : json.dumps(jsoncmd)}
        self.capfWebSocket.send(json.dumps(jsonmsg))

    def sendGoal(self, num) :
        jsonparam = {'goal_num' : num}
        jsoncmd = {'cmd' : 'position', 'param' : json.dumps(jsonparam)}
        jsonmsg = {'targets' : targetID, 'message' : json.dumps(jsoncmd)}
        self.capfWebSocket.send(json.dumps(jsonmsg))

    def changedValue(self):
        size = self.cylinder_slider.value()
        self.cylinder_label.setText(str(size))

    def update_height(self):
        z = self.cylinder_slider.value()
        if not self.sendSlider is None:
            self.sendSlider(z)
            print("[Send params]   cylinder_pos: " + str(z))

    def sendSlider(self, z) :
        jsonparam = {'z' : z}
        jsoncmd = {'cmd' : 'position', 'param' : json.dumps(jsonparam)}
        jsonmsg = {'targets' : targetID, 'message' : json.dumps(jsoncmd)}
        self.capfWebSocket.send(json.dumps(jsonmsg))

    # waypointsの取得など
    def sendRequest(self, content) :
        jsonparam = {'msg' :content}
        jsoncmd = {'request' : 'other', 'param' : json.dumps(jsonparam)}
        jsonmsg = {'targets' : targetID, 'message' : json.dumps(jsoncmd)}
        self.capfWebSocket.send(json.dumps(jsonmsg))
        print("[Send request]   " + str(content))

    def waypointRequest(self):
        print("[*]   CAからwaypointsを取得します。")
        self.sendRequest('waypoint')

    # CA側の呼び出しボタン入力により音声を再生
    def paramCheck(self, params, keylist) :
        result = True
        for key in keylist :
            if not key in params.keys() :
                result = False
        return result

    def _coord_to_px_offset(self, image_shape, origin_px: (int, int), resolution: float, coord: (float, float)) -> (int, int):
        x = int((coord[0] / resolution))
        y = int((coord[1] / resolution))

        x = -origin_px[0] if origin_px[0] + x < 0 else x
        x = image_shape[0] - 1 - origin_px[0] if origin_px[0] + x >= image_shape[0] else x
        y = origin_px[1] if origin_px[1] - y < 0 else y
        y = -(image_shape[1] - 1 - origin_px[1]) if origin_px[1] + -y >= image_shape[1] else y

        return x, y
    ## 座標変換（xyのみ 配列に使用）
    def xy_transform(self, list_x, list_y):
        origin_px: (int, int) = (int(self._origin[0] / self._map_resolution) * -1,
                                 self._image_size[1] + int(self._origin[1] / self._map_resolution))
        for i in range(len(list_x)):
            position_px_offset = self._coord_to_px_offset(self._image_size, origin_px, self._map_resolution, (list_x[i], list_y[i]))
            list_x[i] = origin_px[0] + position_px_offset[0]
            list_y[i] = origin_px[1] - position_px_offset[1]
        return list_x, list_y


if __name__ == '__main__' :
    app = QApplication(sys.argv)
    image = QImage('overview_atr_1f_.png')
    window = mainView()
    window.setImage(image)
    app.exec_()
