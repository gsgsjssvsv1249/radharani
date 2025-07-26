from flask import Flask, send_file
from waifu import Waifu

app = Flask(__name__)
waifu = Waifu()
waifu.initialise(...)

@app.route("/")
def index():
    return "Waifu is ready to chat!"

@app.route("/speak")
def speak():
    waifu.conversation_cycle()
    return send_file("output.mp3", mimetype="audio/mpeg")
