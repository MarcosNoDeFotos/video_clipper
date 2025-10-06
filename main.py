from flask import Flask, render_template, request, jsonify, send_file
from moviepy.video.io.VideoFileClip import VideoFileClip as VFC
import os
from multiprocessing import Process, Queue
from tkinter import Tk, filedialog

app = Flask(__name__)
app.config['CLIPS_FOLDER'] = 'static/clips'
os.makedirs(app.config['CLIPS_FOLDER'], exist_ok=True)

videoPath = None  # ruta local del vídeo

# Función que se ejecuta en un proceso separado para abrir Tkinter
def seleccionar_video(queue):
    root = Tk()
    root.withdraw()
    filename = filedialog.askopenfilename(
        title="Selecciona un vídeo",
        filetypes=[("Video files", "*.mp4 *.mov *.avi")]
    )
    root.destroy()
    queue.put(filename)

# Endpoint para abrir vídeo dinámicamente
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
    # Se devuelve la URL que usará el navegador
    return jsonify({"video_url": "/video"})

# Endpoint para que el navegador pueda reproducir el vídeo
@app.route('/video')
def video_file():
    global videoPath
    if not videoPath:
        return "No hay vídeo seleccionado", 404
    return send_file(videoPath)

# Endpoint para generar clips con MoviePy
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

        # Usar with para cerrar automáticamente
        with VFC(videoPath).subclipped(start, end) as clip:
            clip.write_videofile(clip_path, codec="libx264")

        return jsonify({"clip_url": f"/static/clips/{clip_filename}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
