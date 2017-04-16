#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys, os, threading

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import phonon

from UI_Editor import UI_Editor, UI_Editor_Auto
from Dialog_Tags import Dialog_Tags

from Slicer import Slicer
from Analyzer import Analyzer
from Matcher import Matcher
from Remixer import Remixer

try:
    _fromUtf8 = QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s
try:
    _encoding = QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig)

#多继承VideoWidget和QWidget
class myVideoWidget(phonon.Phonon.VideoWidget,QWidget):
    def __init__(self,x):
        super(myVideoWidget,self).__init__()
        #self.videoPlayer = phonon.Phonon.VideoWidget(x)  # 声明VideoWidget控件

class SmartBGM(QWidget):

    def __init__(self):
        super(SmartBGM, self).__init__()
        self.initUI()
        self.UI=UI_Editor()     #实例化主界面
        self.UI.setupUi(self)   #执行部署designer绘制的ui界面

        #用以下两个量来标记是否已经打开了文件
        self.displayTime=None
        self.audioTime=None
        self.audiooutTime = None  #修改自章睿

        #初始化合并视频关键的三个参数
        self.cutinTime=None
        self.cutoutTime=None
        self.audio_stat_time=None

        #音频列表
        self.audiolist = {}

        #初始化文件路径
        self.videofile=None
        self.audiofile=None

        self.setWindowTitle(u'SmartBGM')#窗口标题
        self.setWindowIcon(QIcon(r'\icon\SmartBGM.icon'))#设置窗口图标
        self.mediaObjectVideo = phonon.Phonon.MediaObject(self)#声明视频对象
        self.mediaObjectVideo.stateChanged.connect(self.stateChanged) # 对象改变时，应该是注册事件，响应按钮
        self.mediaObjectVideo.tick.connect(self.videotick) #连接到时间

        self.mediaObjectAudio = phonon.Phonon.MediaObject(self)#声明音频对象
        self.mediaObjectAudio.stateChanged.connect(self.stateChanged_audio) # 对象改变时，应该是注册事件，响应按钮
        self.mediaObjectAudio.tick.connect(self.audiotick) #连接到时间

        self.setupUi()#执行部署本类新建的控件效果


        # 绑定播放控件的右键事件
        self.connect(self.UI.videoPlayer, SIGNAL('customContextMenuRequested (const QPoint&)'), self.openright)
        # 绑定视频切入切出的按钮
        self.connect(self.UI.btn_cutin,SIGNAL('clicked()'),self.audiocutin)
        self.connect(self.UI.btn_cutout, SIGNAL('clicked()'), self.audiocutout)
        # 绑定标签打开的按钮
        self.connect(self.UI.btn_tag,SIGNAL('clicked()'),self.tag_click)
        # 绑定加入用于确定音频开始点的按钮和对应的处理事件audio_start_clk
        self.connect(self.UI.btn_audio_start, SIGNAL('clicked()'), self.audio_start_clk)
        # 绑定音视频合并按钮和相应事件
        self.connect(self.UI.btn_merge,SIGNAL('clicked()'),self.video_merge)
        #绑定combobox下拉选中条目的事件
        # self.UI.comboBox.connect(self.UI.comboBox,SIGNAL("currentIndexChanged"),self.comboBoxItemClick)
        self.UI.comboBox.activated.connect(self.comboBoxItemClick)
        # 绑定同时播放按钮
        self.connect(self.UI.btn_play_together,SIGNAL('clicked()'),self.play_together_click)
        # 绑定合并音视频并保存按钮
        self.connect(self.UI.btn_save,SIGNAL('clicked()'),self.saveVideoAudio)

        #self.comboBoxTest()
        self.subUI = mySubUI(self)

    def setupUi(self):
        #声明视频控制端行为  包含：播放，暂停，重新开始
        self.playActionVideo = QAction(self.style().standardIcon(QStyle.SP_MediaPlay),"Play",
                                             self,shortcut="Ctrl+P",enabled=False,triggered=self.mediaObjectVideo.play)
        self.pauseActionVideo = QAction(self.style().standardIcon(QStyle.SP_MediaPause),"Pause",
                                              self,shortcut="Ctrl+A",enabled=False,triggered=self.mediaObjectVideo.pause)
        self.stopActionVideo = QAction(self.style().standardIcon(QStyle.SP_MediaStop),"Stop",self,
                                             shortcut="Ctrl+S",enabled=False,triggered=self.mediaObjectVideo.stop)

        # 添加视频控制端   包含 播放， 暂停， 重新开始
        videobar = QToolBar()
        videobar.addAction(self.playActionVideo)
        videobar.addAction(self.pauseActionVideo)
        videobar.addAction(self.stopActionVideo)
        # horizontalLayout_control_video是之前预留的布局，用于后续代码添加控件
        self.UI.horizontalLayout_control_video.addWidget(videobar)

        #声明音频控制端行为  包含：播放，暂停，重新开始
        self.playActionAudio = QAction(self.style().standardIcon(QStyle.SP_MediaPlay),"Play",self,
                                             shortcut="Ctrl+Alt+P",enabled=False,triggered=self.mediaObjectAudio.play)
        self.pauseActionAudio = QAction(self.style().standardIcon(QStyle.SP_MediaPause),"Pause",self,
                                             shortcut="Ctrl+Alt+A",enabled=False,triggered=self.mediaObjectAudio.pause)
        self.stopActionAudio = QAction(self.style().standardIcon(QStyle.SP_MediaStop),"Stop",self,
                                             shortcut="Ctrl+Alt+S",enabled=False,triggered=self.mediaObjectAudio.stop)


        # 添加音频控制端   包含 播放， 暂停， 重新开始
        audiobar = QToolBar()
        audiobar.addAction(self.playActionAudio)
        audiobar.addAction(self.pauseActionAudio)
        audiobar.addAction(self.stopActionAudio)
        # horizontalLayout_control_video是之前预留的布局，用于后续代码添加控件
        self.UI.horizontalLayout_control_audio.addWidget(audiobar)

        #  显示视频LED时间
        palette_videolcd = QPalette()#声明调色板
        palette_videolcd.setBrush(QPalette.Light,Qt.darkGray)#设置刷子颜色
        self.timeLcd_video = self.UI.lcdNumber_video#将lcd数字灯赋给新的对象名
        self.timeLcd_video.setPalette(palette_videolcd)#设置配色方案
        self.timeLcd_video.display('00:00:00')#设置显示格式

        #  显示音频LED时间
        palette_audiolcd = QPalette()#声明调色板
        palette_audiolcd.setBrush(QPalette.Light,Qt.darkBlue)#设置刷子颜色
        self.timeLcd_audio = self.UI.lcdNumber_audio#将lcd数字灯赋给新的对象名
        self.timeLcd_audio.setPalette(palette_audiolcd)#设置配色方案
        self.timeLcd_audio.display('00:00')#设置显示格式

        self.setWindowFlags(Qt.WindowMinimizeButtonHint) #停用窗口最大化按钮
        self.setFixedSize(self.width(),self.height()) #禁止改变窗口的大小
        #  添加播放控件
        self.UI.videoPlayer = myVideoWidget(self)  # 声明VideoWidget控件
        self.UI.horizontalLayout_videoplayer.addWidget(self.UI.videoPlayer)  # 将videoPlayer加入到预留的布局里面
        # 设置播放控件能右键产生菜单的属性
        self.UI.videoPlayer.setContextMenuPolicy(Qt.CustomContextMenu)

    # 合并音视频并保存按钮的响应事件
    def saveVideoAudio(self):
        Afile = self.audiofile.toUtf8()
        temp1 = os.path.split(Afile)
        Vfile = self.videofile.toUtf8()
        temp2 = os.path.split(Vfile)
        t1 = str(temp1[1])
        t2 = str(temp2[1])
        self.thread2 = combineThread(videoName=t2, audioName=t1, object=self.handler, finalname='resultFile.mp4')
        # self.connect(self.myThread, SIGNAL('setStatus'), self.st, Qt.QueuedConnection)
        self.thread2.start()
        # print('hello world')

    #一起播放按钮
    def play_together_click(self):
        if self.videofile == None:
            self.alert(1)
            return
        if self.audiofile == None:
            self.alert(5)
            return

        self.mediaObjectAudio.play()
        self.playActionAudio.setEnabled(False)
        self.pauseActionAudio.setEnabled(True)
        self.stopActionAudio.setEnabled(True)

        self.mediaObjectVideo.play()
        self.playActionVideo.setEnabled(False)
        self.pauseActionVideo.setEnabled(True)
        self.stopActionVideo.setEnabled(True)

    #comboBox下拉点击响应函数
    def comboBoxItemClick(self):
        # print isinstance(self.UI.comboBox.currentText(), QString)
        tmp = unicode(self.UI.comboBox.currentText().toUtf8(), 'utf8', 'ignore')
        # tmp = self.UI.comboBox.currentText()
        # tmp = unicode(tmp, 'gb2312', 'ignore')
        print tmp
        tmp = str(tmp).encode('utf8')
        # tmp = tmp.decode('utf8')
        # print '>>>tmp\'type is:',type(tmp),' ',tmp
        # tmp = self.UI.comboBox.currentText().encoding('utf-8')
        # tmp = self.UI.comboBox.currentText().toUtf8()

        # file = self.audiolist[tmp.decode('utf8')].decode('utf8')
        # file = self.audiolist[Temp].encode('utf8')
        print tmp
        file = self.audiolist[tmp]
        # file = QString(os.path.abspath('.')+'\\Videos\\'+u'告别.mp3')
        file = QString(file)
        print unicode(file)
        self.audiofile = file       # still OK?

        self.mediaObjectAudio.setCurrentSource(phonon.Phonon.MediaSource(file))
        # 初始化音频的输出按钮
        self.audioOutput_audio = phonon.Phonon.AudioOutput(phonon.Phonon.VideoCategory, self)
        phonon.Phonon.createPath(self.mediaObjectAudio, self.audioOutput_audio)
        # 连接到音量
        # self.UI.volumeSlider.setAudioOutput(self.audioOutput_audio)
        # 连接到进度条
        self.UI.seekSlider_audio.setMediaObject(self.mediaObjectAudio)
        self.mediaObjectAudio.play()

    #comboBox测试函数
    def comboBoxTest(self):
        self.UI.comboBox.clear()
        self.audiolist.clear()


        audiodir = os.path.abspath('.') + r'\audio'
        print audiodir

        for root, dirs, files in os.walk(audiodir):
            for name in files:
                if name.endswith(".mp3") or name.endswith(".wav"):
                    # print '>>>name\'s type is:', type(name), name
                    # unicodeName = os.path.split(name)[1].decode('gbk')
                    unicodeName = name.decode('gbk')
                    #print '>>>unicodeName\'s type is:', type(unicodeName),unicodeName
                    self.UI.comboBox.addItem(unicodeName)
                    utf8Name=unicodeName.encode('utf8')
                    #print '>>>key\'s type is:',type(utf8Name)
                    self.audiolist[utf8Name]=audiodir+'\\'+name.decode('gbk')
                    #print '>>>value\'s type is:',type(self.audiolist[utf8Name])

        a=unicode(self.UI.comboBox.currentText())
        # a = self.UI.comboBox.currentText()
        file = QString(self.audiolist[a])
        print '[=>]'+file
        self.videofile = file

        self.mediaObjectAudio.setCurrentSource(phonon.Phonon.MediaSource(file))
        # 初始化音频的输出按钮
        self.audioOutput_audio = phonon.Phonon.AudioOutput(phonon.Phonon.VideoCategory, self)
        phonon.Phonon.createPath(self.mediaObjectAudio, self.audioOutput_audio)
        # 连接到音量
        # self.UI.volumeSlider.setAudioOutput(self.audioOutput_audio)
        # 连接到进度条
        self.UI.seekSlider_audio.setMediaObject(self.mediaObjectAudio)
        self.mediaObjectAudio.play()

    # 2017-03-06 zr
    # 规则：
    # 音频时间设为T0到end,end-T0=t1,视频时间总时间设为0到t2,视频两个点之间的时间设为T1到T2，T2-T1=t3.
    # 1.if t1>t3，对音频进行操作，从T0到t3+T0的音频,和长度为t3的视频合成，然后t3+T0到end的音频丢弃
    # 2.if t1=t3,直接合成
    # 3.if t1<t3,不妨设t3=n*t1+m(n,m均为整数)，则将歌曲循环n遍，只循环T0到end部分，剩余的m时间，重复步骤1
    # 合并音视频按钮
    def video_merge(self):
        if self.videofile == None or \
                        self.cutinTime == None or \
                        self.cutoutTime == None or \
                        self.audiofile == None or \
                        self.audioTime == None:
            self.alert(6)
            return
        # 单独开一个线程，去执行操作
        temp1=self.audiofile  #BUG
        self.buildOperations()
        self.thread1 = myThread(audiofile=self.audiofile, audioTime=self.audioTime, cutinTime=self.cutinTime,
                                cutoutTime=self.cutoutTime, object=self.handler)
        # self.connect(self.myThread, SIGNAL('setStatus'), self.st, Qt.QueuedConnection)
        self.thread1.start()

        # thread1 = threading.Thread(target=self.threadF1())
        # thread1.setDaemon(True)
        # thread1.start()
        # self.handler=operations(audioName=self.audiofile, videoName=self.videofile)
        # self.handler.video_merge(cutinTime=self.cutinTime,cutoutTime=self.cutoutTime,\
        #                          audiofile=self.audiofile,audioTime=self.audioTime)

    def buildOperations(self):
        Afile = self.audiofile.toUtf8()
        temp1 = os.path.split(Afile)
        Vfile = self.videofile.toUtf8()
        temp2 = os.path.split(Vfile)
        t1 = str(temp1[1])
        t2 = str(temp2[1])
        self.handler = operations(audioName=t1, videoName=t2)

    # 加入的音乐起点按钮响应事件
    def audio_start_clk(self):
        if self.audioTime == None:
            self.alert(5)
            return

        self.UI.lbl_audio_start.setText(_translate("Form", self.audioTime.toString('mm:ss'), None))
        # print type(_translate("Form", self.audioTime.toString('mm:ss'),None))
        # print (_translate("Form", self.audioTime.toString('mm:ss'),None))
        self.audio_stat_time = self.audioTime

    # 配乐类型选择按钮
    def tag_click(self):
        dialog = Dialog_Tags(self)
        if dialog.exec_():
            pass
        dialog.destroy()

    # 音频嵌入的视频段开始点
    def audiocutin(self):
        if self.displayTime == None:
            self.alert(5)
            return
        # displayTime由mediaobject对象通过回调函数传入给lcdnumber，由此可将该数据赋给全局变量self.displaytime
        self.UI.lbl_cutin.setText(_translate("Form", self.displayTime.toString('hh:mm:ss'), None))
        self.cutinTime = self.displayTime
        #print self.cutinTime

    # 音频嵌入的视频段结束点
    def audiocutout(self):
        if self.displayTime == None:
            self.alert(1)
            return
        if self.cutinTime == None:
            self.alert(2)
            return
        if self.cutinTime > self.displayTime:
            self.alert(3)
            return

        #以下声明代码用于简化之后的代码表示
        Ta = self.cutinTime    #视频切入点的时间
        Tb = self.displayTime  #当前视频的时间
        Sta = Ta.hour()*3600+Ta.minute()*60+Ta.second()
        Stb = Tb.hour()*3600+Tb.minute()*60+Tb.second()-10

        #print Ta.hour() , Ta.minute() , Ta.second() , Tb.hour() , Tb.minute() , Tb.second() 输出时间

        if Sta > Stb:
            self.alert(4)
            return

        # displayTime由mediaobject对象通过回调函数传入给lcdnumber，由此可将该数据赋给全局变量self.displaytime
        self.UI.lbl_cutout.setText(_translate("Form", self.displayTime.toString('hh:mm:ss'), None))
        self.cutoutTime = self.displayTime
        #print self.cutoutTime


    # video screen 右键菜单
    def openright(self):
        popMenu = QMenu()#弹出菜单控件
        #添加弹出菜单项，自定义图标，并且绑定事件，分别为加载音频和加载视频
        popMenu.addAction(QAction(QIcon(r'.\icon\video.ico'),u'打开视频文件',self,enabled = True, triggered=self.openvideo))
        popMenu.addAction(QAction(QIcon(r'.\icon\audio.ico'),u'音频文件',self,enabled = True, triggered=self.openaudio))
        popMenu.exec_(QCursor.pos())

    # 响应combobox的改变
    def videoList_change(self):
        #file =
        self.mediaObjectAudio.setCurrentSource(phonon.Phonon.MediaSource(file))
        # 初始化音频的输出按钮
        self.audioOutput_audio = phonon.Phonon.AudioOutput(phonon.Phonon.VideoCategory, self)
        phonon.Phonon.createPath(self.mediaObjectAudio, self.audioOutput_audio)
        # 连接到音量
        # self.UI.volumeSlider.setAudioOutput(self.audioOutput_audio)
        # 连接到进度条
        self.UI.seekSlider_audio.setMediaObject(self.mediaObjectAudio)
        self.mediaObjectAudio.play()

    # 选择打开音频
    def openaudio(self):
        Qfile = self.addFiles('audio')
        if not Qfile:
            return

        self.audiolist.clear()# 当前的音频清单
        self.UI.comboBox.clear()

        self.audiofile=Qfile
        file = unicode(Qfile)

        fpath, fname = os.path.split(file)
        # print fpath,fname
        self.audiolist[fname] = file
        # print self.audiolist[fname]
        self.UI.comboBox.addItem(fname)

        self.mediaObjectAudio.setCurrentSource(phonon.Phonon.MediaSource(Qfile))
        #初始化音频的输出按钮
        self.audioOutput_audio = phonon.Phonon.AudioOutput(phonon.Phonon.VideoCategory,self)
        phonon.Phonon.createPath(self.mediaObjectAudio, self.audioOutput_audio)
        #连接到音量
        #self.UI.volumeSlider.setAudioOutput(self.audioOutput_audio)
        #连接到进度条
        self.UI.seekSlider_audio.setMediaObject(self.mediaObjectAudio)
        self.mediaObjectAudio.play()


    # 选择打开视频文件
    def openvideo(self):
        file = self.addFiles('video')
        if not file:
            return
        self.videofile=file
        self.mediaObjectVideo.setCurrentSource(phonon.Phonon.MediaSource(file))  #加载当前的源文件
        phonon.Phonon.createPath(self.mediaObjectVideo, self.UI.videoPlayer)     #将视频对象和播放控件关联起来
        #初始化视频输出
        self.UI.videoPlayer.setAspectRatio(phonon.Phonon.VideoWidget.AspectRatioAuto)
        #初始化音频的输出按钮
        self.audioOutput_video = phonon.Phonon.AudioOutput(phonon.Phonon.VideoCategory,self)
        phonon.Phonon.createPath(self.mediaObjectVideo, self.audioOutput_video)
        #连接到音量按钮
        self.UI.volumeSlider.setAudioOutput(self.audioOutput_video)
        self.UI.seekSlider_video.setMediaObject(self.mediaObjectVideo)
        self.mediaObjectVideo.play()

    # 错误警告信息
    def alert(self,err_num):
        if   err_num == 1:
            QMessageBox.question(self,(u'提示'),(u'请先读取视频！'),QMessageBox.Ok)
        elif err_num == 2:
            QMessageBox.question(self, (u'提示'), (u'请先指定音频插入的视频段的起始时间！'),
                                       QMessageBox.Ok)
        elif err_num == 3:
            QMessageBox.question(self, (u'提示'), (u'当前时间小于指定的视频段起始时间，请重新指定！'),
                                       QMessageBox.Ok)
        elif err_num == 4:
            QMessageBox.question(self, (u'提示'), (u'视频段的时间间距太小，请重新指定！'),
                                       QMessageBox.Ok)
        elif err_num == 5:
            QMessageBox.question(self, (u'提示'), (u'请先指定需要的配乐类型！'), QMessageBox.Ok)
        elif err_num == 6:
            QMessageBox.question(self, (u'提示'), (u'请指定音视频文件和对应的时间！'), QMessageBox.Ok)

    #选择文件
    def addFiles(self,filetype='all'):
        if filetype=='audio':
            tips=u'选择音频文件'
            expand = 'Audio Files(*.mp3 *.wav)'
        elif filetype=='video':
            tips = u'选择视频文件'
            expand = 'Video Files(*.mp4 *.avi *.mkv *.rmvb *.flv)'
        else:
            tips=u'请选择播放文件'
            expand = 'Files(*)'
        # getOpenFileName 只能选择一个  getOpenFileNames  可多个选择
        # files = QFileDialog.getOpenFileName(self, tips, QDesktopServices.storageLocation(
        #     QDesktopServices.DesktopLocation), expand)
        currentPath = os.getcwd()+r'\Videos'
        #currentPath = QDesktopServices.storageLocation(tGui.QDesktopServices.DesktopLocation)
        files = QFileDialog.getOpenFileName(self, tips,currentPath,expand)
        print type(files)

        if not files:
            return ''
        return files

    #视频状态改变事件处理
    def stateChanged(self,newState):

        if newState == phonon.Phonon.ErrorState:#如果出现错误状态，即刻报告
            if self.mediaObjectVideo.errorType() == phonon.Phonon.FatalError:
                QMessageBox.warning(self,"Fatal Error",
                        self.mediaObjectVideo.errorString())
            else:
                QMessageBox.warning(self,"Error",
                        self.mediaObjectVideo.errorString())

        elif newState == phonon.Phonon.PlayingState:#当按下播放按键时候，改变相应状态
            self.playActionVideo.setEnabled(False)
            self.pauseActionVideo.setEnabled(True)
            self.stopActionVideo.setEnabled(True)

        elif newState == phonon.Phonon.StoppedState:#当按下停止按键时候，改变相应状态
            self.stopActionVideo.setEnabled(False)
            self.playActionVideo.setEnabled(True)
            self.pauseActionVideo.setEnabled(False)
            self.timeLcd_video.display("00:00:00")

        elif newState == phonon.Phonon.PausedState:#当按下暂停案件时候，改变相应状态
            self.stopActionVideo.setEnabled(True)
            self.playActionVideo.setEnabled(True)
            self.pauseActionVideo.setEnabled(False)

    #音频状态改变事件处理
    def stateChanged_audio(self,newState):

        if newState == phonon.Phonon.ErrorState:#如果出现错误状态，即刻报告
            if self.mediaObjectVideo.errorType() == phonon.Phonon.FatalError:
                QMessageBox.warning(self,"Fatal Error",
                        self.mediaObjectVideo.errorString())
            else:
                QMessageBox.warning(self,"Error",
                        self.mediaObjectVideo.errorString())

        elif newState == phonon.Phonon.PlayingState:#当按下播放按键时候，改变相应状态
            self.playActionAudio.setEnabled(False)
            self.pauseActionAudio.setEnabled(True)
            self.stopActionAudio.setEnabled(True)

        elif newState == phonon.Phonon.StoppedState:#当按下停止按键时候，改变相应状态
            self.stopActionAudio.setEnabled(False)
            self.playActionAudio.setEnabled(True)
            self.pauseActionAudio.setEnabled(False)
            self.timeLcd_audio.display("00:00")

        elif newState == phonon.Phonon.PausedState:#当按下暂停案件时候，改变相应状态
            self.stopActionAudio.setEnabled(False)
            self.playActionAudio.setEnabled(True)
            self.pauseActionAudio.setEnabled(False)

    # 时间绑定
    def videotick(self,time):
        #相关函数的时间度量是以ms为单位
        self.displayTime = QTime((time /3600000),(time /60000)%60,(time / 1000)%60)
        self.timeLcd_video.display(self.displayTime.toString('hh:mm:ss'))

    # 时间绑定
    def audiotick(self,time):
        #相关函数的时间度量是以ms为单位
        self.audioTime = QTime((time /3600000),(time /60000)%60,(time / 1000)%60)
        self.timeLcd_audio.display(self.audioTime.toString('mm:ss'))

    #响应esc退出画面
    def keyPressEvent(self,event):
        if event.key() == Qt.Key_Escape:
            self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    smartBGM = SmartBGM()
    smartBGM.show()
    sys.exit(app.exec_())

