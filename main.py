import customtkinter as ctk
import threading
from cl_script import execute 

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class HomeFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure((1, 2, 3, 5), weight=1)
        self.grid_rowconfigure(5, weight=1) 
        self.setup_ui()

    def setup_ui(self):

        ctk.CTkLabel(self, text="First server:").grid(row=0, column=0, padx=10, pady=10)
        self.input_username = ctk.CTkEntry(self, placeholder_text="User")
        self.input_username.grid(row=0, column=1, padx=5, sticky="ew")
        self.input_ip = ctk.CTkEntry(self, placeholder_text="IP Address")
        self.input_ip.grid(row=0, column=2, padx=5, sticky="ew")
        self.input_port = ctk.CTkEntry(self, placeholder_text="22")
        self.input_port.insert(0, "22")
        self.input_port.grid(row=0, column=3, padx=5, sticky="ew")
        self.input_password = ctk.CTkEntry(self, placeholder_text="Password", show="*")
        self.input_password.grid(row=0, column=5, padx=5, sticky="ew")

        ctk.CTkLabel(self, text="Second server:").grid(row=1, column=0, padx=10, pady=10)
        self.output_server = ctk.CTkEntry(self, placeholder_text="Optional Output IP")
        self.output_server.grid(row=1, column=1, padx=5, sticky="ew")
        self.output_port = ctk.CTkEntry(self, placeholder_text="Port")
        self.output_port.grid(row=1, column=2, padx=5, sticky="ew")

        self.begin_btn = ctk.CTkButton(self, text="🚀 Begin Archive", command=self.start_backup_task)
        self.begin_btn.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

        self.console_container = ctk.CTkFrame(self, fg_color="transparent")
        self.console_container.grid(row=5, column=0, columnspan=10, padx=20, pady=(0, 20), sticky="nsew")
        self.console_container.grid_columnconfigure(0, weight=1)
        self.console_container.grid_rowconfigure(1, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.console_container, orientation="horizontal")
        self.progress_bar.set(0)

        self.console_box = ctk.CTkTextbox(self.console_container, state="disabled", fg_color="#161616", text_color="#00ff00")
        self.console_box.grid(row=1, column=0, sticky="nsew")

    def start_backup_task(self):
        h, u, p, po = self.input_ip.get(), self.input_username.get(), self.input_password.get(), self.input_port.get()

        if not h or not u or not p:
            self.write_to_console("⚠️ System: Missing fields.")
            return

        self.progress_bar.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        self.progress_bar.set(0)
        
        self.begin_btn.configure(state="disabled")
        
        thread = threading.Thread(
            target=execute,
            args=(h, u, p, po, self.update_progress_ui, self.write_to_console),
            daemon=True
        )
        thread.start()

    def update_progress_ui(self, float_value):
        self.after(0, lambda: self.progress_bar.set(float_value))

    def write_to_console(self, text):
        def _update():
            self.console_box.configure(state="normal")
            self.console_box.insert("end", f"> {text}\n")
            self.console_box.configure(state="disabled")
            self.console_box.see("end")
            
            if "completed" in text.lower() or "error" in text.lower():
                self.begin_btn.configure(state="normal")
                self.progress_bar.grid_remove()
        
        self.after(0, _update)

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Application Settings", font=("Arial", 20)).grid(row=0, column=0, pady=50)
        ctk.CTkSwitch(self, text="Keep logs after session").grid(row=1, column=0, pady=10)
        ctk.CTkSwitch(self, text="Verify checksum after archive").grid(row=2, column=0, pady=10)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ServerApp Pro")
        self.geometry("1100x700")

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.top_bar = ctk.CTkFrame(self, height=60, corner_radius=0)
        self.top_bar.grid(row=0, column=0, sticky="ew")
        
        self.btn_home = ctk.CTkButton(self.top_bar, text="🏠 Home", width=120, command=lambda: self.show_page("home"))
        self.btn_home.grid(row=0, column=0, padx=20, pady=15)
        
        self.btn_settings = ctk.CTkButton(self.top_bar, text="⚙️ Settings", width=120, command=lambda: self.show_page("settings"))
        self.btn_settings.grid(row=0, column=1, padx=5, pady=15)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.pages = {}
        self.pages["home"] = HomeFrame(self.container)
        self.pages["settings"] = SettingsFrame(self.container)

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        self.show_page("home")

    def show_page(self, name):
        """Aduce pagina cerută în prim-plan fără a distruge celelalte frame-uri"""
        page = self.pages[name]
        page.tkraise()

if __name__ == "__main__":
    app = App()
    app.mainloop()