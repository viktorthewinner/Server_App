import customtkinter as ctk
import threading
from cl_script import execute, upload
from cache_manager import save_to_cache, load_from_cache

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# all frames are declared as classes => mantaining all the variables in memory when we go from one frame to another
# class App is the full class

class HomeFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure((1, 2, 3, 5), weight=1)
        self.grid_rowconfigure(5, weight=1) 
        self.setup_ui()
        self.load_data()

    # the main container
    def setup_ui(self):
        # boxes to fill the info for the first server
        ctk.CTkLabel(self, text="First server:").grid(row=0, column=0, padx=10, pady=10)

        self.input_username = ctk.CTkEntry(self, placeholder_text="User")
        self.input_username.grid(row=0, column=1, padx=5, sticky="ew")

        self.input_ip = ctk.CTkEntry(self, placeholder_text="IP Address")
        self.input_ip.grid(row=0, column=2, padx=5, sticky="ew")

        self.input_port = ctk.CTkEntry(self, placeholder_text="22")
        self.input_port.grid(row=0, column=3, padx=5, sticky="ew")

        self.input_password = ctk.CTkEntry(self, placeholder_text="Password", show="*")
        self.input_password.grid(row=0, column=4, padx=5, sticky="ew")

        self.input_url = ctk.CTkEntry(self, placeholder_text="http://url.com")
        self.input_url.grid(row=0, column=5, padx=5, sticky="ew")


        # boxes to fill the info for the second server
        ctk.CTkLabel(self, text="Second server:").grid(row=1, column=0, padx=10, pady=10)

        self.output_username = ctk.CTkEntry(self, placeholder_text="User")
        self.output_username.grid(row=1, column=1, padx=5, sticky="ew")

        self.output_ip = ctk.CTkEntry(self, placeholder_text="IP Address")
        self.output_ip.grid(row=1, column=2, padx=5, sticky="ew")

        self.output_port = ctk.CTkEntry(self, placeholder_text="22")
        self.output_port.grid(row=1, column=3, padx=5, sticky="ew")

        self.output_password = ctk.CTkEntry(self, placeholder_text="Password", show="*")
        self.output_password.grid(row=1, column=4, padx=5, sticky="ew")


        # button to start the process
        self.begin_btn = ctk.CTkButton(self, text="🚀 Begin Archive", command=self.start_backup_task)
        self.begin_btn.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="ew")

        # console container
        self.console_container = ctk.CTkFrame(self, fg_color="transparent")
        self.console_container.grid(row=5, column=0, columnspan=10, padx=20, pady=(0, 20), sticky="nsew")
        self.console_container.grid_columnconfigure(0, weight=1)
        self.console_container.grid_rowconfigure(1, weight=1)

        # progress bar
        self.progress_bar = ctk.CTkProgressBar(self.console_container, orientation="horizontal")
        self.progress_bar.set(0)

        self.console_box = ctk.CTkTextbox(self.console_container, state="disabled", fg_color="#161616", font=("Consolas", 13))
        self.console_box.grid(row=1, column=0, sticky="nsew")
        self.console_box._textbox.tag_config("error", foreground="#FF4B4B")   # Roșu
        self.console_box._textbox.tag_config("success", foreground="#00FF00") # Verde
        self.console_box._textbox.tag_config("info", foreground="#FFFFFF")    # Alb
        self.console_box._textbox.tag_config("system", foreground="#5CE1E6")  # Cyan


    # if you switch classes, remember the old values
    def load_data(self):
        cache = load_from_cache()
        if cache:
            if cache.get("user", "")!= "":
                self.input_username.insert(0, cache.get("user", ""))
            if cache.get("ip", "")!= "":
                self.input_ip.insert(0, cache.get("ip", ""))
            if cache.get("port", "")!= "":
                self.input_port.insert(0, cache.get("port", ""))
            if cache.get("url", "")!= "":
                self.input_url.insert(0, cache.get("url", ""))
            if cache.get("out_user", "")!= "":
                self.output_username.insert(0, cache.get("out_user", ""))
            if cache.get("out_ip", "")!= "":
                self.output_ip.insert(0, cache.get("out_ip", ""))  
            if cache.get("out_port", "")!= "":
                self.output_port.insert(0, cache.get("out_port", ""))
        else:
            self.input_port.insert(0, "22")
            self.output_port.insert(0, "22")

    # start the process
    def start_backup_task(self):
        h, u, p, po = self.input_ip.get(), self.input_username.get(), self.input_password.get(), self.input_port.get()
        url = self.input_url.get()
        o_h, o_u, o_p, o_po = self.output_ip.get(), self.output_username.get(), self.output_password.get(), self.output_port.get()

        required_fields = [h, u, p, po, url, o_h, o_u, o_p, o_po]

        if not all(required_fields):
            self.write_to_console("⚠️ System: All fields are required for migration.")
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            self.write_to_console("⚠️ System: Invalid URL. It must start with http:// or https://. Check your URL again!", "error")
            return

        save_to_cache({"user": u, "ip": h, "port": po, "url": url, "out_user": o_u, "out_ip": o_h, "out_port": o_po})

        self.progress_bar.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        self.progress_bar.set(0)
        self.begin_btn.configure(state="disabled")

        def run_sync():
            size = execute(h, u, p, po, self.update_progress_ui, self.write_to_console)
            if size > 0:
                self.after(0, lambda: self.progress_bar.set(0))
                upload(o_h, o_u, o_p, o_po, url, size, self.update_progress_ui, self.write_to_console)
            else:
                self.after(0, lambda: self.begin_btn.configure(state="normal"))

        threading.Thread(target=run_sync, daemon=True).start()


    def update_progress_ui(self, float_value):
        self.after(0, lambda: self.progress_bar.set(float_value))

    # writing in console
    def write_to_console(self, text, custom_tag=None):
        def _update():
            self.console_box.configure(state="normal")
            
            tag = "info"
            if custom_tag:
                tag = custom_tag
            elif "❌" in text or "error" in text.lower():
                tag = "error"
            elif "✅" in text or "🚀" in text or "successfully" in text.lower():
                tag = "success"
            elif "⚠️" in text or "system" in text.lower():
                tag = "system"
            
            self.console_box.insert("end", f"> {text}\n", tag)
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
        page = self.pages[name]
        page.tkraise()

if __name__ == "__main__":
    app = App()
    app.mainloop()