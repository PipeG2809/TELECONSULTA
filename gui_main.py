import sys
import threading
import socket
import struct
import cv2
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QLabel, QMessageBox, QListWidget, QHBoxLayout, QComboBox, QDateEdit, QTimeEdit
)
from PyQt5.QtCore import Qt, QDate, QTime, QTimer
import users
import av_call

# Simple helper: start a TCP server to receive JPEG frames and display on a QLabel
class SimpleVideoReceiver(threading.Thread):
    def __init__(self, label, host='0.0.0.0', port=7000):
        super().__init__(daemon=True)
        self.label = label
        self.host = host
        self.port = port
        self.sock = None
        self.running = False

    def run(self):
        self.running = True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.listen(1)
            print(f"Patient video receiver listening on {self.host}:{self.port}")
            conn, addr = self.sock.accept()
            print(f"Patient connected from {addr}")
            data = b''
            payload_size = struct.calcsize('!I')
            while self.running:
                while len(data) < payload_size:
                    packet = conn.recv(4096)
                    if not packet:
                        self.running = False
                        break
                    data += packet
                if not self.running:
                    break
                packed_size = data[:payload_size]
                data = data[payload_size:]
                frame_size = struct.unpack('!I', packed_size)[0]
                while len(data) < frame_size:
                    packet = conn.recv(4096)
                    if not packet:
                        self.running = False
                        break
                    data += packet
                if not self.running:
                    break
                frame_data = data[:frame_size]
                data = data[frame_size:]
                # decode jpeg
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                self.last_frame = frame
        except Exception as e:
            print('Receiver error', e)
        finally:
            try:
                if self.sock:
                    self.sock.close()
            except Exception:
                pass

    def stop(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass

# Simple sender: captures local camera, encodes frames as JPEG and sends to doctor's receiver
class SimpleVideoSender(threading.Thread):
    def __init__(self, server_ip, port=7000, cam_index=0, fps=15):
        super().__init__(daemon=True)
        self.server_ip = server_ip
        self.port = port
        self.cam_index = cam_index
        self.fps = fps
        self.running = False

    def run(self):
        self.running = True
        try:
            cap = cv2.VideoCapture(self.cam_index)
            if not cap.isOpened():
                print('No se pudo abrir la cámara local')
                return
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.server_ip, self.port))
            print(f'Conectado al receiver en {self.server_ip}:{self.port}')
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break
                ret2, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if not ret2:
                    continue
                data = buf.tobytes()
                size = struct.pack('!I', len(data))
                sock.sendall(size + data)
                time.sleep(1.0 / self.fps)
        except Exception as e:
            print('Sender error', e)
        finally:
            try:
                cap.release()
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass

import numpy as np
from PyQt5.QtGui import QImage, QPixmap

class LoginRegisterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Login / Registro')
        self.setGeometry(200,200,420,360)
        layout = QVBoxLayout()
        form = QFormLayout()
        self.name_input = QLineEdit()
        self.id_input = QLineEdit()
        self.role_combo = QComboBox()
        self.role_combo.addItems(['paciente','medico'])
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form.addRow('Nombre:', self.name_input)
        form.addRow('ID:', self.id_input)
        form.addRow('Rol:', self.role_combo)
        form.addRow('Contraseña:', self.password_input)
        layout.addLayout(form)
        btn_register = QPushButton('Registrar')
        btn_register.clicked.connect(self.register_user)
        layout.addWidget(btn_register)
        layout.addWidget(QLabel('--- Iniciar sesión ---'))
        login_form = QFormLayout()
        self.login_id = QLineEdit()
        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.Password)
        login_form.addRow('ID:', self.login_id)
        login_form.addRow('Contraseña:', self.login_password)
        layout.addLayout(login_form)
        btn_login = QPushButton('Iniciar sesión')
        btn_login.clicked.connect(self.login_user)
        layout.addWidget(btn_login)
        self.setLayout(layout)

    def register_user(self):
        name = self.name_input.text().strip()
        uid = self.id_input.text().strip()
        role = self.role_combo.currentText()
        pwd = self.password_input.text()
        if not all([name, uid, role, pwd]):
            QMessageBox.warning(self,'Error','Complete todos los campos')
            return
        resp = users.registerUser(name,uid,role,pwd)
        if resp.get('status')=='ok':
            QMessageBox.information(self,'OK','Usuario registrado')
        else:
            QMessageBox.warning(self,'Error',str(resp))

    def login_user(self):
        uid = self.login_id.text().strip()
        pwd = self.login_password.text().strip()
        if not uid or not pwd:
            QMessageBox.warning(self,'Error','Ingrese ID y contraseña')
            return
        resp = users.openSession(uid,pwd,'127.0.0.1')
        if resp.get('status')=='ok':
            role = resp.get('role')
            if role=='paciente':
                self.next_window = PatientWindow(uid)
            else:
                self.next_window = DoctorWindow(uid)
            self.next_window.show()
            self.close()
        else:
            QMessageBox.warning(self,'Error','Credenciales incorrectas')

class PatientWindow(QWidget):
    def __init__(self, patient_id):
        super().__init__()
        self.patient_id = patient_id
        self.setWindowTitle(f'Paciente: {patient_id}')
        self.setGeometry(240,200,560,480)
        layout = QVBoxLayout()
        btn_logout = QPushButton('Cerrar sesión')
        btn_logout.clicked.connect(self.logout)
        layout.addWidget(btn_logout)
        self.doctors_list = QListWidget()
        layout.addWidget(QLabel('Médicos disponibles:'))
        layout.addWidget(self.doctors_list)
        btn_refresh = QPushButton('Listar médicos')
        btn_refresh.clicked.connect(self.list_doctors)
        layout.addWidget(btn_refresh)
        form_layout = QHBoxLayout()
        self.date_edit = QDateEdit(); self.date_edit.setDate(QDate.currentDate()); self.date_edit.setCalendarPopup(True)
        self.time_edit = QTimeEdit(); self.time_edit.setTime(QTime.currentTime())
        form_layout.addWidget(QLabel('Fecha:')); form_layout.addWidget(self.date_edit)
        form_layout.addWidget(QLabel('Hora:')); form_layout.addWidget(self.time_edit)
        layout.addLayout(form_layout)
        btn_schedule = QPushButton('Agendar cita')
        btn_schedule.clicked.connect(self.schedule_appointment)
        layout.addWidget(btn_schedule)
        self.remote_label = QLabel('Video remoto')
        self.remote_label.setFixedSize(480,270)
        self.remote_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.remote_label)
        self.local_label = QLabel('Tu cámara (preview)')
        self.local_label.setFixedSize(240,135)
        self.local_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.local_label)
        btn_connect = QPushButton('Conectar videollamada (2 vías)')
        btn_connect.clicked.connect(self.start_av_call)
        layout.addWidget(btn_connect)
        self.setLayout(layout)
        self.list_doctors()
        self._receiver = None
        self._receiver_frame = None
        self._receiver_timer = QTimer()
        self._receiver_timer.timeout.connect(self._update_remote_frame)

    def logout(self):
        self.close()
        w = LoginRegisterWindow(); w.show()

    def list_doctors(self):
        self.doctors_list.clear()
        resp = users.doctorsList(self.patient_id)
        if resp.get('status')=='ok':
            for d in resp.get('doctors',[]):
                self.doctors_list.addItem(f"{d['id']} - {d['name']}")
        else:
            self.doctors_list.addItem('Error cargando médicos')

    def schedule_appointment(self):
        cur = self.doctors_list.currentItem()
        if not cur: QMessageBox.warning(self,'Error','Seleccione un médico'); return
        doc = cur.text().split(' - ')[0]
        date = self.date_edit.date().toString('yyyy-MM-dd')
        time = self.time_edit.time().toString('HH:mm')
        resp = users.addAppointment(self.patient_id, doc, date, time)
        if resp.get('status')=='ok': QMessageBox.information(self,'OK','Cita agendada')
        else: QMessageBox.warning(self,'Error','No se pudo agendar')

    def start_av_call(self):
        cur = self.doctors_list.currentItem()
        if not cur: QMessageBox.warning(self,'Error','Seleccione un médico'); return
        doctor_id = cur.text().split(' - ')[0]

        doctor_ip = "172.20.10.3"
        

        self.av_client = av_call.av_client(doctor_ip, self.remote_label, 480, 270)
        threading.Thread(target=self.av_client.connect, daemon=True).start()

        self._sender = SimpleVideoSender(doctor_ip, port=7000, cam_index=0, fps=10)
        self._sender.start()

        self._cap = cv2.VideoCapture(0)
        self._preview_timer = QTimer()
        self._preview_timer.timeout.connect(self._update_local_preview)
        self._preview_timer.start(100)

    def _update_local_preview(self):
        if hasattr(self,'_cap') and self._cap.isOpened():
            ret, frame = self._cap.read()
            if not ret: return
            frame = cv2.resize(frame, (240,135))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h,w,ch = rgb.shape
            bytes_per_line = ch*w
            img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pix = QPixmap.fromImage(img)
            self.local_label.setPixmap(pix)

    def _update_remote_frame(self):
        pass

class DoctorWindow(QWidget):
    def __init__(self, doctor_id):
        super().__init__()
        self.doctor_id = doctor_id
        self.setWindowTitle(f'Médico: {doctor_id}')
        self.setGeometry(240,200,560,480)
        layout = QVBoxLayout()
        btn_logout = QPushButton('Cerrar sesión')
        btn_logout.clicked.connect(self.logout)
        layout.addWidget(btn_logout)
        self.appt_list = QListWidget(); layout.addWidget(QLabel('Citas agendadas:')); layout.addWidget(self.appt_list)
        btn_refresh = QPushButton('Listar citas'); btn_refresh.clicked.connect(self.list_appointments); layout.addWidget(btn_refresh)
        btn_wait = QPushButton('Iniciar servidor AV (esperar paciente)'); btn_wait.clicked.connect(self.start_av_server); layout.addWidget(btn_wait)
        self.remote_patient_label = QLabel('Video paciente (si se conecta)')
        self.remote_patient_label.setFixedSize(480,270)
        self.remote_patient_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.remote_patient_label)
        self.setLayout(layout)
        self.list_appointments()
        self._receiver = None
        self._receiver_timer = QTimer()
        self._receiver_timer.timeout.connect(self._poll_receiver_frame)

    def logout(self):
        w = LoginRegisterWindow(); w.show(); self.close()

    def list_appointments(self):
        resp = users.listAppointments(self.doctor_id)
        self.appt_list.clear()
        if resp.get('status')=='ok':
            for a in resp.get('appointments',[]):
                self.appt_list.addItem(f"{a['date']} {a['time']} - Paciente {a['patient']}")
        else:
            self.appt_list.addItem('Error cargando citas')

    def start_av_server(self):
        self.vw = VideoWindow('medico', self.doctor_id)
        self.vw.show()

        def receiver_loop():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
                s.bind(('0.0.0.0',7000))
                s.listen(1)
                print('Receiver listening on 7000')
                conn,addr = s.accept()
                print('Patient connected',addr)
                data=b''
                payload_size = struct.calcsize('!I')
                while True:
                    while len(data)<payload_size:
                        packet = conn.recv(4096)
                        if not packet:
                            return
                        data+=packet
                    packed_size = data[:payload_size]; data=data[payload_size:]
                    frame_size = struct.unpack('!I', packed_size)[0]
                    while len(data)<frame_size:
                        packet = conn.recv(4096)
                        if not packet:
                            return
                        data+=packet
                    frame_data = data[:frame_size]; data=data[frame_size:]
                    nparr = np.frombuffer(frame_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if frame is None: continue
                    frame = cv2.resize(frame, (480,270))
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h,w,ch = rgb.shape
                    bytes_per_line = ch*w
                    img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    pix = QPixmap.fromImage(img)
                    def set_pix():
                        self.remote_patient_label.setPixmap(pix)
                    QTimer.singleShot(0, set_pix)
            except Exception as e:
                print('Receiver error', e)

        threading.Thread(target=receiver_loop, daemon=True).start()

    def _poll_receiver_frame(self):
        pass

class VideoWindow(QWidget):
    def __init__(self, role, peer_id, server_ip=None):
        super().__init__()
        self.role = role
        self.peer_id = peer_id
        self.server_ip = server_ip
        self.setWindowTitle(f'AV Call - {role} {peer_id}')
        self.setGeometry(300,200,640,480)
        layout = QVBoxLayout()
        self.video_label = QLabel('Video')
        self.video_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.video_label)
        btn_close = QPushButton('Cerrar')
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)
        self.setLayout(layout)
        threading.Thread(target=self._start_av, daemon=True).start()

    def _start_av(self):
        w = 640; h = 360
        if self.role=='medico':
            srv = av_call.av_server(self.video_label, w, h)
            srv.start_server()
        else:
            cli = av_call.av_client(self.server_ip, self.video_label, w, h)
            cli.connect()

def main():
    app = QApplication(sys.argv)
    w = LoginRegisterWindow(); w.show(); sys.exit(app.exec_())

if __name__=='__main__':
    main()


