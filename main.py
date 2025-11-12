from flask import Flask, render_template, request, jsonify, send_file, make_response
import os
from multiprocessing import Process, Queue
from tkinter import Tk, filedialog
import time
import json
import subprocess

app = Flask(__name__)
CURRENT_PATH = os.path.dirname(__file__).replace("\\", "/") + "/"


videoPath = None  # ruta local del vídeo



# === 🔧 DESACTIVAR CACHÉ GLOBALMENTE ===
@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# === 🎬 Selección de vídeo con Tkinter ===
def trg_seleccionar_ruta_videos(queue):
    root = Tk()
    root.withdraw()
    selected = filedialog.askdirectory(
        title="Selecciona una ruta para cortar vídeos"
    )
    print(selected)
    root.destroy()
    queue.put(selected)



@app.route("/listar_videos")
def listar_videos():
    videos = [f for f in os.listdir(app.config['VIDEOS_DIR']) if f.lower().endswith((".mp4", ".mov", ".avi", ".mkv"))]
    videosData = []
    
    for video in videos:
        extension = video.split(".")[-1]
        clipCount = [f for f in os.listdir(app.config['CLIPS_FOLDER']) if (f.lower().endswith((".mp4", ".mov", ".avi", ".mkv")) and f.lower().startswith(video.lower().replace(f".{extension}", "")))]
        videosData.append({"video": video, "clips" : clipCount.__len__()})

    return jsonify({"videos": videosData, "videos_path":app.config['VIDEOS_DIR']})

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




@app.route("/seleccionar_ruta_videos")
def seleccionar_ruta_videos():
    # Abrir Tkinter para seleccionar vídeo
    queue = Queue()
    p = Process(target=trg_seleccionar_ruta_videos, args=(queue,))
    p.start()
    p.join()
    selected_paths = queue.get()
    if not selected_paths:
        return jsonify({"success": False, "error": "No se seleccionó ninguna ruta"})
    else:
        app.config['VIDEOS_DIR'] = selected_paths
    return jsonify({"success": True})

@app.route("/abrir_video")
def abrir_video():
    global videoPath
    video_name = request.args.get("video")
    if not video_name:
        return jsonify({"error": "No se indicó ningún vídeo"}), 400
    video_path = os.path.join(app.config['VIDEOS_DIR'], video_name)
    if not os.path.exists(video_path):
        return jsonify({"error": "Vídeo no encontrado"}), 404
    videoPath = video_path

    return jsonify({"video_url": f"/video?video={video_name}&ts={int(time.time())}"})




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
        video_base_name = os.path.basename(videoPath)
        extension = video_base_name.split(".")[-1]
        video_base_name = video_base_name.replace(f".{extension}", "")
        base_name = f"{video_base_name}_{int(start*1000)}_{int(end*1000)}"
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
            "-accurate_seek",                     # precisión total
            "-ss", str(start),
            "-to", str(end),
            "-i", videoPath,                     # input después de -i para precisión
            "-map", "0", # Copia todas las pistas de vídeo y audio
            "-c", "copy", # Copia sin recodificar ni cambiar la calidad
            "-avoid_negative_ts", "1", # corrige timestamps negativos
            "-fflags", "+genpts", # recalcula los PTS (Presentation Timestamps) del vídeo
            "-reset_timestamps", "1", # fuerza que todos los streams comiencen en 0
            "-y",
            clip_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
        print(f"👌 Vídeo generado en {clip_path}")

        # Agregar parámetro temporal para evitar caché
        version = int(time.time())
        return jsonify({"clip_url": f"{app.config['CLIPS_FOLDER']}/{clip_filename}?v={version}"})
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
    # app.run(debug=True, use_reloader=False, host="192.168.1.189")

    app.config['CLIPS_FOLDER'] = 'static/clips'
    app.config['VIDEOS_DIR'] = CURRENT_PATH + "videos_entrada"
    host= "127.0.0.1"
    port = 5000
    serverConfigPath =CURRENT_PATH+"serverConfig.json"
    try:
        with open(serverConfigPath, encoding="utf-8") as serverConfig:
            serverConfigData = json.loads(serverConfig.read())
            host = serverConfigData["host"]
            port = serverConfigData["port"]
            app.config['CLIPS_FOLDER'] = serverConfigData["clips_output"]
            app.config['VIDEOS_DIR'] = serverConfigData["default_videos_input"]
    except Exception as e:
        print(f"Error al abrir el archivo de configuración del servidor en {serverConfigPath}. \n{e}")

    os.makedirs(app.config['CLIPS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['VIDEOS_DIR'], exist_ok=True)
    app.run(debug=True, use_reloader=False, host=host, port=port)
