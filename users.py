# users.py
from datetime import datetime
import os
import users
print("Python está usando este users.py:", users.__file__)

# ============================
# Base de datos simple en memoria
# ============================
# users_db: id -> {name, password, role, session}
users_db = {}

# Archivo donde se guardan las citas
appointments_file = "appointments.txt"

# ============================
# Funciones de usuarios
# ============================

def registerUser(name, user_id, role, password):
    """Registrar un nuevo usuario"""
    if user_id in users_db:
        return {"status": "error", "message": "ID ya registrado"}
    users_db[user_id] = {"name": name, "role": role, "password": password, "session": ""}
    return {"status": "ok", "message": "Usuario registrado"}

def openSession(user_id, password, ip):
    """Iniciar sesión de un usuario"""
    u = users_db.get(user_id)
    if not u:
        return {"status": "error", "message": "Usuario no encontrado"}
    if u["password"] != password:
        return {"status": "error", "message": "Contraseña incorrecta"}
    u["session"] = ip
    return {"status": "ok", "message": "Sesión iniciada", "role": u["role"]}

def closeSession(user_id):
    """Cerrar sesión de un usuario"""
    u = users_db.get(user_id)
    if not u:
        return {"status": "error", "message": "Usuario no encontrado"}
    u["session"] = ""
    return {"status": "ok", "message": "Sesión cerrada"}

def doctorsList(user_id):
    """Listar todos los doctores para un paciente"""
    user = users_db.get(user_id)
    if not user or user["role"] != "paciente":
        return {"status": "error", "message": "Acceso denegado"}
    doctors = [{"id": uid, "name": u["name"]} for uid, u in users_db.items() if u["role"]=="medico"]
    return {"status": "ok", "doctors": doctors}

def addAppointment(patient_id, doctor_id, date, time):
    """Agregar una cita"""
    if doctor_id not in users_db or users_db[doctor_id]["role"] != "medico":
        return {"status": "error", "message": "Doctor no encontrado"}
    if patient_id not in users_db or users_db[patient_id]["role"] != "paciente":
        return {"status": "error", "message": "Paciente no encontrado"}
    
    # Validar fecha y hora
    try:
        datetime.strptime(date, "%Y-%m-%d")
        datetime.strptime(time, "%H:%M")
    except ValueError:
        return {"status": "error", "message": "Fecha u hora inválida"}

    # Guardar cita en archivo
    with open(appointments_file, "a", encoding="utf-8") as f:
        f.write(f"{patient_id}|{doctor_id}|{date}|{time}\n")
    return {"status": "ok", "message": "Cita agendada"}

def listAppointments(doctor_id):
    """Listar todas las citas de un doctor"""
    if doctor_id not in users_db or users_db[doctor_id]["role"] != "medico":
        return {"status": "error", "message": "Doctor no encontrado"}
    lines = []
    if os.path.exists(appointments_file):
        with open(appointments_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
    appts = []
    for line in lines:
        parts = line.split("|")
        if len(parts) >= 4:
            pid, did, date, time = parts[:4]
            if did == doctor_id:
                appts.append({"patient": pid, "date": date, "time": time})
    return {"status": "ok", "appointments": appts}
