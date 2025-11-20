# conect.patient.py (VERSIÓN PyQt5, totalmente compatible)

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QMessageBox
from PyQt5.QtCore import QTimer
import json
from av_call import open_video_window

class DoctorConnectWindow(QWidget):
    def __init__(self, client, doctor_id):
        super().__init__()
        self.client = client
        self.doctor_id = doctor_id

        self.setWindowTitle("Médico - Esperar Paciente")
        self.setGeometry(300, 200, 400, 300)

        layout = QVBoxLayout()

        self.lista = QListWidget()
        layout.addWidget(self.lista)

        btn_listar = QPushButton("Listar citas")
        btn_listar.clicked.connect(self.listar_citas)
        layout.addWidget(btn_listar)

        btn_esperar = QPushButton("Esperar paciente")
        btn_esperar.clicked.connect(self.iniciar_espera)
        layout.addWidget(btn_esperar)

        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.verificar_conexion)

    def listar_citas(self):
        self.lista.clear()
        try:
            resp = self.client.getAppointmentsDoctor(self.doctor_id)
            citas = json.loads(resp)
            for c in citas:
                self.lista.addItem(f"{c['hora']} - Paciente {c['paciente']}")
        except Exception as e:
            self.lista.addItem(f"Error: {e}")

    def iniciar_espera(self):
        QMessageBox.information(self, "Esperando", "Esperando a que el paciente se conecte...")
        self.timer.start(2000)

    def verificar_conexion(self):
        try:
            resp = self.client.checkPatientConnection(self.doctor_id)
            data = json.loads(resp)

            if data.get("conectado"):
                paciente = data.get("paciente")
                QMessageBox.information(self, "Conexión encontrada",
                                        f"El paciente {paciente} está listo.")
                self.timer.stop()
                open_video_window("Doctor", self.doctor_id)
        except:
            pass
