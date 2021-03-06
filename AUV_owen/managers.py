#此模块包含了CaptureManager类的实现， 此类中抽象窗口和键盘，按空格键可获取截图信息，按tab键可启动/停止截屏（录屏记录），按ESC可退出程序


import cv2
import numpy
import time
import process


class CaptureManager(object):

    def __init__(self,capture,previewWindowsManager = None,
                shouldMirrorPreview = False,shouldprocess = False,shouldshowFPS = False,process_mode = 'line'):

        self.previewWindowsManager =  previewWindowsManager
        self.shouldMirrorPreview = shouldMirrorPreview
        self.shouldprocess = shouldprocess
        self.shouldshowFPS = shouldshowFPS
        self.process_mode = process_mode
        self.resize_fx_fy = None
        self.data = None #储存回传的数据
        self._capture = capture
        self._channel = 0
        self._enteredFrame = False
        self._frame = None
        self._imageFilename = None
        self._videoFilename = None
        self._videoWriter = None
        self._startTime = None
        self._frameElapsed = int(0)
        self._fpsEstimate = None


    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self,value):
        if self._channel != value:
            self._channel = value
            self._frame = None


    @property
    def frame(self):
        if self._enteredFrame and self._frame is None:
            _,self._frame = self._capture.retrieve()
        return self._frame

    @property
    def isWritingImage(self):
        return self._imageFilename is not None

    @property
    def isWritingVideo(self):
        return self._videoFilename is not None

    def enterFrame(self):
        #Capture the next frame,if any.
        #But first,check that any previous frame was exited
        assert not self._enteredFrame,'previous enterFrame() had no matching exitFrame()'
        if self._capture is not None:
            self._enteredFrame = self._capture.grab()

    def exitFrame(self):
        #Draw to the window.Write to files.Release the frame.
        #Check whether any grabbed frame is retrievable.
        if self.frame is None:
            self._enteredFrame = False
            return
        
        #Update the FPS estimate and related variables.
        if self._frameElapsed == 0:
            self._startTime = time.time()
        else:
            timeElapsed = time.time() - self._startTime
            self._fpsEstimate = self._frameElapsed / timeElapsed
        
        self._frameElapsed += 1
    
        #Draw to the window,if any.
        if self.previewWindowsManager is not None:
            if self.shouldMirrorPreview:
                if self.resize_fx_fy != None:
                    self._frame = cv2.resize(self._frame,dsize=None,fx=self.resize_fx_fy[0],fy=self.resize_fx_fy[1])
                    

                if self.shouldprocess: #是否处理图像
                    print("img processed!")
                    if self.process_mode == 'line':
                        Processed = process.imgprocess_follow_line(self._frame)
                    if self.process_mode == 'box':
                        Processed = process.imgprocess_detect_box(self._frame)
                    if self.process_mode == 'adsorbate': #吸附物检测
                        Processed = process.imgprocess_detect_adsorbate(self._frame)

                    self._data = Processed.data
                    self._frame = Processed.processed
                    cv2.imshow('hsv',Processed.hsv_ranged)

                if self.shouldshowFPS and self._fpsEstimate: #是否显示FPS
                    cv2.putText(self._frame,str(round(self._fpsEstimate,2)),(10,40),cv2.FONT_HERSHEY_SIMPLEX,1,color = (0,0,255))


                mirroredFrame = numpy.fliplr(self._frame).copy()
                self.previewWindowsManager.show(mirroredFrame)
            else:
                if self.resize_fx_fy != None:
                    self._frame = cv2.resize(self._frame,dsize=None,fx=self.resize_fx_fy[0],fy=self.resize_fx_fy[1])
                    
                if self.shouldprocess:#是否处理图像
                    if self.process_mode == 'line':
                        Processed = process.imgprocess_follow_line(self._frame)
                        cv2.imshow('hsv',Processed.hsv_ranged)
                    elif self.process_mode == 'box':
                        Processed = process.imgprocess_detect_box(self._frame)
                        cv2.imshow('rgb',Processed.rgb_ranged)
                    elif self.process_mode == 'adsorbate': #吸附物检测
                        Processed  = process.imgprocess_detect_adsorbate(self._frame)
                        cv2.imshow('thr',Processed.RGB_thre)
                    self._data = Processed.data
                    self._frame = Processed.processed

                if self.shouldshowFPS and self._fpsEstimate: #是否显示FPS
                    cv2.putText(self._frame,str(round(self._fpsEstimate,2)),(10,40),cv2.FONT_HERSHEY_SIMPLEX,1,color = (0,0,255))



                self.previewWindowsManager.show(self._frame)

        #Write to the image file,if any.
        if self.isWritingImage:
            cv2.imwrite(self._imageFilename,self._frame)
            self._imageFilename = None
        self._writeVideoFrame()
        self._frame = None
        self._enteredFrame = False

    #Write to the video file,if any .
    def writeImage(self,filename):
        #write the next exited frame to an image file.
        self._imageFilename = filename

    def startWritingVideo(
        self,filename,
        encoding = cv2.VideoWriter_fourcc('I','4','2','0')):
        #start writing exited frames to a video file.
        self._videoFilename = filename
        self._videoEncoding = encoding
    
    def stopWritingVideo(self):
        #Stop writing exited frames to a video file.
        self._videoFilename = None
        self._videoEncoding = None
        self._videoWriter = None
    def _writeVideoFrame(self):
        if not self.isWritingVideo:
            return
        if self._videoWriter is None:
            fps = self._capture.get(cv2.CAP_PROP_FPS)
            if fps ==0.0:
                #The capture's FPS is unknow so use an estimate.
                if self._frameElapsed < 20:
                    #wait until more frames elapse so that the estimate is more stable
                    return
                else:
                    fps = self._fpsEstimate
            size = (int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))  #存在问题
            
            self._videoWriter = cv2.VideoWriter(
            self._videoFilename,
            self._videoEncoding,
            fps,
            (self._frame.shape[1],self._frame.shape[0]))  #此处存在问题
            self._videoWriter.write(self._frame)
class WindowManager(object):
    
    def __init__(self,windowName,keypressCallback = None):
        self.keypressCallback = keypressCallback

        self._windowName=windowName
        self._isWindowCreated = False

    @property
    def isWindowCreated(self):
        return self._isWindowCreated
    
    def createWindow(self):
        cv2.namedWindow(self._windowName)
        self._isWindowCreated = True
    
    def show(self,frame):
        if frame is not None:
            cv2.imshow(self._windowName,frame)
    
    def destroyWindow(self):
        cv2.destroyWindow(self._windowName)
        self._isWindowCreated = False
    def processEvents(self):
        keycode = cv2.waitKey(1)
        if self.keypressCallback is not None and keycode != -1:
            #Discard any non-ASCII info encoded by GTK
            keycode &= 0xFF
            self.keypressCallback(keycode)


