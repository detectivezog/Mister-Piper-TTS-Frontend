import os
import threading
import traceback
import customtkinter as ctk
import sounddevice as sd
import numpy as np
from piper.voice import PiperVoice

class PiperVictoryReader(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Piper AI - Local Victory Reader")
        self.geometry("850x700")
        
        self.voices_dir = "./voices/"
        self.voice = None
        self.is_speaking = False

        # --- UI SETUP ---
        self.text_area = ctk.CTkTextbox(self, font=("Segoe UI", 15))
        self.text_area.pack(padx=20, pady=20, fill="both", expand=True)
        self.text_area.insert("0.0", "Type here. Check terminal for logs.")

        self.status_label = ctk.CTkLabel(self, text="Status: Ready", text_color="gray")
        self.status_label.pack(pady=5)

        self.ctrl_frame = ctk.CTkFrame(self)
        self.ctrl_frame.pack(pady=10, fill="x", padx=20)

        # Voice Menu
        self.voice_menu = ctk.CTkOptionMenu(self.ctrl_frame, command=self.load_voice)
        self.voice_menu.pack(side="left", padx=10, pady=10)

        # Speed Slider
        ctk.CTkLabel(self.ctrl_frame, text="Speed").pack(side="left", padx=5)
        self.speed_slider = ctk.CTkSlider(self.ctrl_frame, from_=0.5, to=2.0)
        self.speed_slider.set(1.0)
        self.speed_slider.pack(side="left", padx=10)

        # Volume Slider (Restored)
        ctk.CTkLabel(self.ctrl_frame, text="Vol").pack(side="left", padx=5)
        self.vol_slider = ctk.CTkSlider(self.ctrl_frame, from_=0.0, to=1.5)
        self.vol_slider.set(1.0)
        self.vol_slider.pack(side="left", padx=10)

        self.play_btn = ctk.CTkButton(self, text="▶ Speak", command=self.speak, fg_color="#2ecc71")
        self.play_btn.pack(pady=20)

        self.scan_voices()

    def update_status(self, msg, color="white"):
        self.status_label.configure(text=f"Status: {msg}", text_color=color)
        self.update_idletasks()

    def scan_voices(self):
        if not os.path.exists(self.voices_dir): os.makedirs(self.voices_dir)
        files = [f for f in os.listdir(self.voices_dir) if f.endswith(".onnx")]
        if files: self.voice_menu.configure(values=files)

    def load_voice(self, filename):
        # Immediate visual feedback
        self.update_status(f"Loading {filename}...", "orange")
        print(f"--- Loading {filename} ---")
        
        def _bg_load():
            try:
                path = os.path.join(self.voices_dir, filename)
                self.voice = PiperVoice.load(path)
                self.update_status(f"Loaded: {filename}", "#2ecc71")
            except Exception:
                traceback.print_exc()
                self.update_status("Load Failed!", "red")

        threading.Thread(target=_bg_load, daemon=True).start()

    def speak(self):
        text = self.text_area.get("1.0", "end-1c").strip()
        if self.voice and text and not self.is_speaking:
            self.is_speaking = True
            threading.Thread(target=self._run, args=(text,), daemon=True).start()

    def _run(self, text):
        try:
            self.update_status("Synthesizing...", "cyan")
            self.voice.config.length_scale = 1.0 / self.speed_slider.get()
            
            raw_chunks = []
            for chunk in self.voice.synthesize(text):
                # The specific fix for your version of Piper:
                if hasattr(chunk, 'audio_int16_bytes'):
                    raw_chunks.append(chunk.audio_int16_bytes)
                else:
                    raw_chunks.append(chunk) # Fallback to bytes

            audio_bytes = b"".join(raw_chunks)
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            
            # Apply Volume Slider
            audio_np = audio_np * self.vol_slider.get()
            # Normalize to avoid clipping
            audio_np = np.clip(audio_np, -32768, 32767).astype(np.int16)

            self.update_status("Speaking...", "#3498db")
            sd.play(audio_np, self.voice.config.sample_rate)
            sd.wait()
            self.update_status("Finished.", "gray")

        except Exception:
            print("\n!!! SYNTHESIS CRASH !!!")
            traceback.print_exc()
            self.update_status("Error - Check Terminal", "red")
        finally:
            self.is_speaking = False

if __name__ == "__main__":
    app = PiperVictoryReader()
    app.mainloop()