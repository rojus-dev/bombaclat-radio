import os
import sounddevice as sd
import soundfile as sf

class AudioEngine:
    def __init__(self, settings):
        self.settings = settings
        self.volume = settings.get("startup_volume", 80) / 100
        self.active_players = []
        self.now_playing = []

    def get_output_devices(self):
        devices = []

        for i, device in enumerate(sd.query_devices()):
            if device["max_output_channels"] > 0:
                devices.append(f"{i}: {device['name']}")

        return devices

    def get_selected_device_id(self):
        selected = self.settings.get("output_device", "")

        if selected:
            try:
                return int(selected.split(":")[0])
            except:
                return None

        return None

    def set_volume(self, value):
        self.volume = float(value) / 100
        self.settings["startup_volume"] = int(float(value))

    def play_sound(self, path, name=None, file_id=None, sound_volume=100):
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        player = SoundPlayer(
            path=path,
            name=name or os.path.basename(path),
            file_id=file_id,
            engine=self,
            sound_volume=sound_volume
        )

        player.play()
        self.active_players.append(player)
        self.now_playing.append(player)

        return player

    def stop_all(self):
        for player in self.active_players:
            player.stop()

        self.active_players.clear()
        self.now_playing.clear()

    def cleanup_finished(self):
        self.active_players[:] = [p for p in self.active_players if not p.done]
        self.now_playing[:] = [p for p in self.now_playing if not p.done]

class SoundPlayer:
    def __init__(self, path, name, file_id, engine, sound_volume=100):
        self.path = path
        self.name = name
        self.file_id = file_id
        self.engine = engine
        self.sound_volume = sound_volume / 100
        self.position = 0
        self.done = False

        data, samplerate = sf.read(path, dtype="float32", always_2d=True)

        self.data = data
        self.samplerate = samplerate
        self.channels = data.shape[1]

        self.stream = sd.OutputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="float32",
            device=self.engine.get_selected_device_id(),
            callback=self.callback
        )

    def callback(self, outdata, frames, time, status):
        remaining = len(self.data) - self.position

        if remaining <= 0:
            outdata.fill(0)
            self.done = True
            raise sd.CallbackStop

        chunk = self.data[self.position:self.position + frames]
        final_volume = self.engine.volume * self.sound_volume

        if len(chunk) < frames:
            outdata[:len(chunk)] = chunk * final_volume
            outdata[len(chunk):].fill(0)
            self.done = True
            raise sd.CallbackStop
        else:
            outdata[:] = chunk * final_volume

        self.position += frames

    def get_progress(self):
        if len(self.data) == 0:
            return 0.0

        return min(1.0, self.position / len(self.data))

    def play(self):
        self.stream.start()

    def stop(self):
        try:
            self.stream.stop()
            self.stream.close()
        except:
            pass

        self.done = True
