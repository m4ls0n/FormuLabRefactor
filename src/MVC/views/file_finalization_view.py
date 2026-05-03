import tkinter as tk
from tkinter import scrolledtext


class FileFinalizationView(tk.Frame):
    def __init__(self, controller, tex_content, is_batch=False):
        super().__init__(controller.app.root)
        self.controller = controller
        self.tex_content = tex_content
        self.is_batch = is_batch
        self.is_table_of_contents_included = tk.BooleanVar()
        self.is_headers_numeration_included = tk.BooleanVar()
        self.export_strategy = tk.StringVar(value="merge")
        self.show_screen()

    def show_screen(self):
        self.controller.app.root.title("FormuLab")

        tk.Label(self, text="Доработка файла", font=("Arial", 14)).pack(pady=20)
        tk.Checkbutton(self, text="Добавить оглавление", variable=self.is_table_of_contents_included).pack(anchor="w")
        tk.Checkbutton(self, text="Добавить нумерацию заголовков", variable=self.is_headers_numeration_included).pack(anchor="w")

        if self.is_batch:
            strategy_frame = tk.LabelFrame(self, text="Стратегия пакетной обработки")
            strategy_frame.pack(fill=tk.X, padx=10, pady=8)
            tk.Radiobutton(
                strategy_frame,
                text="Слияние в единый .tex файл",
                variable=self.export_strategy,
                value="merge"
            ).pack(anchor="w")
            tk.Radiobutton(
                strategy_frame,
                text="Модульная структура: main.tex + отдельные части",
                variable=self.export_strategy,
                value="modular"
            ).pack(anchor="w")

        tk.Label(self, text="Предпросмотр .tex файла:").pack(pady=10)
        preview = scrolledtext.ScrolledText(self, height=15, wrap=tk.WORD, font=("Courier", 10))
        preview.insert(tk.END, self.tex_content)
        preview.config(state=tk.DISABLED)
        preview.pack(expand=True, fill="both", padx=10, pady=10)

        tk.Button(self, text="Сохранить файл", command=self.controller.finalize_file).pack(pady=10)
        tk.Button(self, text="Назад", command=self.controller.back).pack(pady=10)