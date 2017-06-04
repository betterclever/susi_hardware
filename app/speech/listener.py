from threading import Thread
import speech_recognition as sr


class AudioProducer(Thread):
    """
    AudioProducer
    given a mic and a recognizer implementation, continuously listens to the
    mic for potential speech chunks and pushes them onto the queue.
    """

    def __init__(self, state, queue, mic, recognizer, emitter):
        super(AudioProducer, self).__init__()
        self.daemon = True
        self.state = state
        self.queue = queue
        self.mic = mic
        self.recognizer = recognizer
        self.emitter = emitter

    def run(self):
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            while self.state.running:
                try:
                    audio = self.recognizer.listen(source, self.emitter)
                    self.queue.put(audio)
                except IOError as ex:
                    self.emitter.emit("recognizer_loop:ioerror", ex)

    def stop(self):
        """
            Stop producer thread.
        """
        self.state.running = False
        self.recognizer.stop()

class AudioConsumer(Thread):
    """
    AudioConsumer
    Consumes AudioData chunks off the queue
    """

    # In seconds, the minimum audio size to be sent to remote STT
    MIN_AUDIO_SIZE = 0.5

    def __init__(self, state, queue, emitter, stt):
        super(AudioConsumer, self).__init__()
        self.daemon = True
        self.queue = queue
        self.state = state
        self.emitter = emitter
        self.stt = stt

    def run(self):
        while self.state.running:
            self.read()

    def read(self):
        audio = self.queue.get()

        if audio is not None:
            self.process(audio)

    @staticmethod
    def _audio_length(audio):
        return float(len(audio.frame_data)) / (
            audio.sample_rate * audio.sample_width)

    def process(self, audio):

        if self._audio_length(audio) < self.MIN_AUDIO_SIZE:
            print("Audio too short to be processed")
        else:
            self.transcribe(audio)

    def transcribe(self, audio):
        text = None
        try:
            # Invoke the STT engine on the audio clip
            text = self.stt.execute(audio).lower().strip()
            print("STT: " + text)
        except sr.RequestError as e:
            print("Could not request Speech Recognition {0}".format(e))
        except ConnectionError as e:
            print("Connection Error: {0}".format(e))
            self.emitter.emit("recognizer_loop:no_internet")
        except Exception as e:
            print(e)
            print("Speech Recognition could not understand audio")

        if text:
            # STT succeeded, send text to TTS engine for output
            # TODO: Send text to TTS Engine
            pass