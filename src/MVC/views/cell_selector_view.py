import tkinter as tk


class CellSelectorView(tk.Frame):
    PAGE_SIZE = 250

    def __init__(self, controller, file_names):
        super().__init__(controller.app.root)
        self.controller = controller
        self.file_names = file_names
        self.current_file_index = 0
        self.current_page = 0
        self.cell_vars = {}
        self.canvas = None
        self.file_listbox = None
        self.show_screen()

    def show_screen(self):
        self.controller.app.root.title("FormuLab")
        self.pack(fill=tk.BOTH, expand=True)
        self.clear_frame()

        header = tk.Label(self, text="Выберите ячейки для конвертации", font=("Arial", 14))
        header.pack(pady=10, anchor="n")

        content_frame = tk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True)

        self.__show_file_list(content_frame)
        self.__show_current_file_cells(content_frame)
        self.__show_action_buttons()

    def __show_file_list(self, parent):
        file_frame = tk.Frame(parent, width=260)
        file_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 4), pady=4)
        file_frame.pack_propagate(False)

        tk.Label(file_frame, text="Файлы", font=("Arial", 11, "bold")).pack(anchor="w")
        self.file_listbox = tk.Listbox(file_frame, exportselection=False)
        self.file_listbox.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.file_listbox.bind("<<ListboxSelect>>", self.__on_file_selected)
        self.__refresh_file_list()

    def __show_current_file_cells(self, parent):
        cells = self.controller.get_cells_for_file(self.current_file_index)
        total_pages = max(1, (len(cells) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.current_page = min(self.current_page, total_pages - 1)

        cell_area = tk.Frame(parent)
        cell_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 8), pady=4)

        tk.Label(
            cell_area,
            text=f"{self.file_names[self.current_file_index]} (стр. {self.current_page + 1}/{total_pages})",
            font=("Arial", 11, "bold")
        ).pack(anchor="w")

        list_frame = tk.Frame(cell_area)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(list_frame)
        self.canvas.bind_all("<MouseWheel>", self._on_canvas_mousewheel)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.config(yscrollcommand=scrollbar.set)

        scrollable_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        start = self.current_page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        for offset, cell in enumerate(cells[start:end], start=start + 1):
            self.__show_cell(scrollable_frame, offset, cell)

        scrollable_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def __show_cell(self, parent, cell_index, cell):
        cell_type = cell.get('cell_type', '')
        content = cell.get('source', '')
        cell_frame = tk.Frame(parent)
        cell_frame.pack(fill=tk.X, pady=5)

        text_frame = tk.Frame(cell_frame)
        text_frame.pack(fill=tk.X)

        text_widget = tk.Text(
            text_frame,
            height=5,
            width=80,
            wrap=tk.WORD,
            bg="white",
            fg="black",
            font=("Arial", 10)
        )
        text_widget.insert(tk.END, f"{cell_index}: [{cell_type}] {content}")
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_widget.bind("<MouseWheel>", self._on_text_mousewheel)

        scrollbar_inner = tk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        scrollbar_inner.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar_inner.set)

        tk.Checkbutton(
            cell_frame,
            text=f"Выбрать {cell_index}",
            variable=self.__get_cell_var(self.current_file_index, cell_index),
            command=self.__refresh_file_list
        ).pack(anchor="w", pady=2)

    def __show_action_buttons(self):
        button_frame = tk.Frame(self)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        current_file_frame = tk.Frame(button_frame)
        current_file_frame.pack(fill=tk.X)
        tk.Button(current_file_frame, text="Выделить все (файл)", command=lambda: self.controller.select_all_cells("current")).pack(side=tk.LEFT, padx=4, pady=3)
        tk.Button(current_file_frame, text="Снять выделение (файл)", command=lambda: self.controller.deselect_all_cells("current")).pack(side=tk.LEFT, padx=4, pady=3)
        tk.Button(current_file_frame, text="Только текст (файл)", command=lambda: self.controller.select_markdown_cells("current")).pack(side=tk.LEFT, padx=4, pady=3)
        tk.Button(current_file_frame, text="Только код (файл)", command=lambda: self.controller.select_code_cells("current")).pack(side=tk.LEFT, padx=4, pady=3)
        tk.Button(current_file_frame, text="Только выходные данные (файл)", command=lambda: self.controller.select_output_cells("current")).pack(side=tk.LEFT, padx=4, pady=3)

        all_files_frame = tk.Frame(button_frame)
        all_files_frame.pack(fill=tk.X)
        tk.Button(all_files_frame, text="Выделить все (все)", command=lambda: self.controller.select_all_cells("all")).pack(side=tk.LEFT, padx=4, pady=3)
        tk.Button(all_files_frame, text="Снять выделение (все)", command=lambda: self.controller.deselect_all_cells("all")).pack(side=tk.LEFT, padx=4, pady=3)
        tk.Button(all_files_frame, text="Только текст (все)", command=lambda: self.controller.select_markdown_cells("all")).pack(side=tk.LEFT, padx=4, pady=3)
        tk.Button(all_files_frame, text="Только код (все)", command=lambda: self.controller.select_code_cells("all")).pack(side=tk.LEFT, padx=4, pady=3)
        tk.Button(all_files_frame, text="Только выходные данные (все)", command=lambda: self.controller.select_output_cells("all")).pack(side=tk.LEFT, padx=4, pady=3)

        navigation_frame = tk.Frame(button_frame)
        navigation_frame.pack(fill=tk.X)

        cells = self.controller.get_cells_for_file(self.current_file_index)
        if self.current_page > 0:
            tk.Button(navigation_frame, text="Назад", command=self.previous_page).pack(side=tk.LEFT, padx=4, pady=5)
        if (self.current_page + 1) * self.PAGE_SIZE < len(cells):
            tk.Button(navigation_frame, text="Далее", command=self.next_page).pack(side=tk.LEFT, padx=4, pady=5)

        tk.Button(navigation_frame, text="Конвертировать", command=self.controller.convert).pack(side=tk.LEFT, padx=4, pady=5)
        tk.Button(navigation_frame, text="Отмена", command=self.controller.back).pack(side=tk.LEFT, padx=4, pady=5)

    def __on_file_selected(self, _event):
        selection = self.file_listbox.curselection()
        if not selection:
            return
        self.current_file_index = selection[0]
        self.current_page = 0
        self.show_screen()

    def __refresh_file_list(self):
        if not self.file_listbox:
            return
        self.file_listbox.delete(0, tk.END)
        for file_index, file_name in enumerate(self.file_names):
            marker = "✓" if self.__file_has_selected_cells(file_index) else " "
            self.file_listbox.insert(tk.END, f"{marker} {file_name}")
        self.file_listbox.selection_set(self.current_file_index)

    def __file_has_selected_cells(self, file_index):
        return any(
            var.get()
            for (selected_file_index, _cell_index), var in self.cell_vars.items()
            if selected_file_index == file_index
        )

    def clear_frame(self):
        for widget in self.winfo_children():
            widget.destroy()

    def __get_cell_var(self, file_index, cell_index):
        key = (file_index, cell_index)
        if key not in self.cell_vars:
            self.cell_vars[key] = tk.BooleanVar()
        return self.cell_vars[key]

    def set_selected_indices(self, file_index, selected_indices):
        selected_indices = set(selected_indices)
        cells = self.controller.get_cells_for_file(file_index)
        for cell_index in range(1, len(cells) + 1):
            self.__get_cell_var(file_index, cell_index).set(cell_index in selected_indices)
        self.__refresh_file_list()

    def set_selected_indices_by_file(self, selected_indices_by_file):
        for file_index, selected_indices in selected_indices_by_file.items():
            self.set_selected_indices(file_index, selected_indices)

    def get_selected_cells_by_file(self):
        selected = {file_index: [] for file_index in range(len(self.file_names))}
        for (file_index, cell_index), var in self.cell_vars.items():
            if var.get():
                selected[file_index].append(cell_index)
        return {
            file_index: sorted(indices)
            for file_index, indices in selected.items()
        }

    def get_selected_indices(self):
        if len(self.file_names) != 1:
            return []
        return self.get_selected_cells_by_file().get(0, [])

    def next_page(self):
        self.current_page += 1
        self.show_screen()

    def previous_page(self):
        self.current_page -= 1
        self.show_screen()

    def _on_text_mousewheel(self, event):
        event.widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _on_canvas_mousewheel(self, event):
        if self.canvas:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")