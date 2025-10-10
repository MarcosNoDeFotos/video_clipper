from flask import Flask, render_template, request, jsonify, send_file, make_response
from moviepy.video.io.VideoFileClip import VideoFileClip as VFC
import os
from multiprocessing import Process, Queue
from tkinter import Tk, filedialog
import time
import subprocess

app = Flask(__name__)
app.config['CLIPS_FOLDER'] = 'static/clips'
os.makedirs(app.config['CLIPS_FOLDER'], exist_ok=True)

videoPath = None  # ruta local del vídeo


# === 🔧 DESACTIVAR CACHÉ GLOBALMENTE ===
@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# === 🎬 Selección de vídeo con Tkinter ===
def seleccionar_video(queue):
    root = Tk()
    root.withdraw()
    filename = filedialog.askopenfilename(
        title="Selecciona un vídeo",
        filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv *.flv *.wmv")]
    )
    root.destroy()
    queue.put(filename)


# === 📂 Endpoint para abrir vídeo dinámicamente ===
@app.route('/abrir_video', methods=['GET'])
def abrir_video():
    global videoPath
    queue = Queue()
    p = Process(target=seleccionar_video, args=(queue,))
    p.start()
    p.join()
    selected_path = queue.get()

    if not selected_path:
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    videoPath = selected_path
    # Se devuelve la URL que usará el navegador (forzando recarga con timestamp)
    return jsonify({"video_url": f"/video?ts={int(time.time())}"})


# === 🎥 Endpoint para servir el vídeo seleccionado ===
@app.route('/video')
def video_file():
    global videoPath
    if not videoPath:
        return "No hay vídeo seleccionado", 404

    response = make_response(send_file(videoPath))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# === ✂️ Endpoint para generar clips ===
@app.route('/generate_clip', methods=['POST'])
def generate_clip():
    global videoPath
    if not videoPath:
        return jsonify({"error": "No hay vídeo seleccionado"}), 400

    data = request.json
    start = float(data['start'])
    end = float(data['end'])

    if start >= end:
        return jsonify({"error": "El tiempo de inicio debe ser menor que el de fin."}), 400

    try:
        # Crear nombre de clip evitando sobrescribir
        i = 1
        base_name = f"clip_{int(start*1000)}_{int(end*1000)}"
        clip_filename = f"{base_name}.mp4"
        while os.path.exists(os.path.join(app.config['CLIPS_FOLDER'], clip_filename)):
            clip_filename = f"{base_name}_{i}.mp4"
            i += 1
        clip_path = os.path.join(app.config['CLIPS_FOLDER'], clip_filename)

        # Crear clip temporal sin cargar todo el vídeo a memoria
        # with VFC(videoPath) as video:
        #     subclip = video.subclipped(start, end)
        #     subclip.write_videofile(clip_path, codec="libx264")
            
        # Extraer el clip con FFmpeg conservando TODAS las pistas de audio y video
        cmd = [
            "ffmpeg",
            "-y",  # sobrescribir sin preguntar
            "-i", videoPath,
            "-ss", str(start),
            "-to", str(end),
            "-c", "copy",  # copia directa sin recodificar
            clip_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            

        # Agregar parámetro temporal para evitar caché
        version = int(time.time())
        return jsonify({"clip_url": f"/static/clips/{clip_filename}?v={version}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === 🏠 Página principal ===
@app.route('/')
def index():
    response = make_response(render_template('index.html'))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
