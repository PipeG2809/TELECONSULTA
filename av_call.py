# python -m pip install pyaudio
# pip install opencv-python
import socket, threading, pyaudio, cv2, pickle, struct

from PyQt5.QtGui import QPixmap
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel

# Audio config
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class av_server:
    def __init__(self, label:QLabel, display_width, display_height):
        self.audio_sock = socket.socket()
        self.video_sock = socket.socket()

        self.audio_sock.bind(('0.0.0.0', 5000))
        self.video_sock.bind(('0.0.0.0', 6000))
        self.label = label
        self.display_width = display_width
        self.display_height = display_height

        #threading.Event().wait()  # keep main thread alive

    def __audio_handler(self):
        p = pyaudio.PyAudio()
        input_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        output_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)

        def send_audio():
            while True:
                try:
                    data = input_stream.read(CHUNK)
                    self.conn_audio.sendall(data)
                except Exception as e:
                    print("Audio send error:", e)
                    break

        def recv_audio():
            while True:
                try:
                    data = self.conn_audio.recv(CHUNK)
                    if not data:
                        print("Audio connection closed.")
                        break
                    output_stream.write(data)
                except Exception as e:
                    print("Audio recv error:", e)
                    break

        threading.Thread(target=send_audio, daemon=True).start()
        threading.Thread(target=recv_audio, daemon=True).start()

    def __video_handler(self):
        cap = cv2.VideoCapture(0)

        def send_video():
            while True:
                try:
                    ret, frame = cap.read()
                    if not ret:
                        continue
                    _, buffer = cv2.imencode('.jpg', frame)
                    data = pickle.dumps(buffer)
                    message = struct.pack('!L', len(data)) + data
                    self.conn_video.sendall(message)
                except Exception as e:
                    print("Video send error:", e)
                    break

        def recv_video():
            data = b''
            payload_size = struct.calcsize("!L")
            while True:
                try:
                    while len(data) < payload_size:
                        packet = self.conn_video.recv(4096)
                        if not packet:
                            print("Video connection closed.")
                            return
                        data += packet

                    packed_size = data[:payload_size]
                    data = data[payload_size:]
                    frame_size = struct.unpack("!L", packed_size)[0]

                    while len(data) < frame_size:
                        packet = self.conn_video.recv(4096)
                        if not packet:
                            print("Video frame incomplete.")
                            return
                        data += packet

                    frame_data = data[:frame_size]
                    data = data[frame_size:]
                    frame = pickle.loads(frame_data)
                    frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                    if frame is not None:
                        qt_img = self.convert_cv_qt(frame)
                        self.label.setPixmap(qt_img)
                except Exception as e:
                    print("Video recv error:", e)
                    break

        threading.Thread(target=send_video, daemon=True).start()
        threading.Thread(target=recv_video, daemon=True).start()
    
    def start_server(self):
        def server_thread():
            self.audio_sock.listen(1)
            self.video_sock.listen(1)

            print("Waiting for audio connection...")
            self.conn_audio, _ = self.audio_sock.accept()
            print("Audio connected.")
            print("Waiting for video connection...")
            self.conn_video, _ = self.video_sock.accept()
            print("Video connected.")

            self.__audio_handler()
            self.__video_handler()
        threading.Thread(target=server_thread, daemon=True).start()
    

    def convert_cv_qt(self, cv_img):
        # Convert from an opencv image to QPixmap
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.display_width, self.display_height, Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)
        



class av_client:
    def __init__(self, server_ip,label:QLabel, display_width, display_height):

        self.audio_sock = socket.socket()
        self.video_sock = socket.socket()
        self.server_ip=server_ip
        self.label = label
        self.display_width = display_width
        self.display_height = display_height


        #threading.Event().wait()  # keep main thread alive
    
    def __audio_handler(self):
        p = pyaudio.PyAudio()
        input_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        output_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)

        def send_audio():
            while True:
                try:
                    data = input_stream.read(CHUNK)
                    self.audio_sock.sendall(data)
                except Exception as e:
                    print("Audio send error:", e)
                    break

        def recv_audio():
            while True:
                try:
                    data = self.audio_sock.recv(CHUNK)
                    if not data:
                        print("Audio connection closed.")
                        break
                    output_stream.write(data)
                except Exception as e:
                    print("Audio recv error:", e)
                    break

        threading.Thread(target=send_audio, daemon=True).start()
        threading.Thread(target=recv_audio, daemon=True).start()

    def __video_handler(self):
        cap = cv2.VideoCapture(0)

        def send_video():
            while True:
                try:
                    ret, frame = cap.read()
                    if not ret:
                        continue
                    _, buffer = cv2.imencode('.jpg', frame)
                    data = pickle.dumps(buffer)
                    message = struct.pack('!L', len(data)) + data
                    self.video_sock.sendall(message)
                except Exception as e:
                    print("Video send error:", e)
                    break

        def recv_video():
            data = b''
            payload_size = struct.calcsize("!L")
            while True:
                try:
                    while len(data) < payload_size:
                        packet = self.video_sock.recv(4096)
                        if not packet:
                            print("Video connection closed.")
                            return
                        data += packet

                    packed_size = data[:payload_size]
                    data = data[payload_size:]
                    frame_size = struct.unpack("!L", packed_size)[0]

                    while len(data) < frame_size:
                        packet = self.video_sock.recv(4096)
                        if not packet:
                            print("Video frame incomplete.")
                            return
                        data += packet

                    frame_data = data[:frame_size]
                    data = data[frame_size:]
                    frame = pickle.loads(frame_data)
                    frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                    if frame is not None:
                        qt_img = self.convert_cv_qt(frame)
                        self.label.setPixmap(qt_img)
                except Exception as e:
                    print("Video recv error:", e)
                    break

        threading.Thread(target=send_video, daemon=True).start()
        threading.Thread(target=recv_video, daemon=True).start()

    def connect(self):
        def connect_thread():
            try:
                self.audio_sock.connect((self.server_ip, 5000))
                self.video_sock.connect((self.server_ip, 6000))

                print("Connected to server.")

                self.__audio_handler()
                self.__video_handler()
            except:
                print("Couldn't connect to server")

        
        threading.Thread(target=connect_thread, daemon=True).start()

    def convert_cv_qt(self, cv_img):
        # Convert from an opencv image to QPixmap
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.display_width, self.display_height, Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)
