from tkinter import messagebox

from src.MVC.models.cell_selector_model import CellSelectorModel
from src.MVC.views.cell_selector_view import CellSelectorView


class CellSelectorController:
    def __init__(self, app, notebook_data, notebook_sources=None):
        self.app = app
        self.model = CellSelectorModel(notebook_data, notebook_sources)
        self.view = CellSelectorView(self, self.model.get_file_names())

    def get_cells_for_file(self, file_index):
        return self.model.get_cells(file_index)

    def convert(self):
        selected_cells_by_file = self.view.get_selected_cells_by_file()
        if not any(selected_cells_by_file.values()):
            messagebox.showwarning("Предупреждение", "Выберите хотя бы одну ячейку!")
            return

        try:
            self.model.convert_selection_to_tex(selected_cells_by_file)
            self.app.show_file_finalization()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def back(self):
        self.app.show_main_menu()

    def select_all_cells(self, scope="current"):
        self.__apply_selection(scope, self.model.get_all_cell_indices)

    def deselect_all_cells(self, scope="current"):
        if scope == "all":
            self.view.set_selected_indices_by_file({
                file_index: []
                for file_index in range(len(self.model.get_file_names()))
            })
        else:
            self.view.set_selected_indices(self.view.current_file_index, [])

    def select_markdown_cells(self, scope="current"):
        self.__apply_selection(scope, self.model.get_markdown_cell_indices)

    def select_code_cells(self, scope="current"):
        self.__apply_selection(scope, self.model.get_code_cell_indices)

    def select_output_cells(self, scope="current"):
        self.__apply_selection(scope, self.model.get_output_cell_indices)

    def __apply_selection(self, scope, index_getter):
        if scope == "all":
            self.view.set_selected_indices_by_file({
                file_index: index_getter(file_index)
                for file_index in range(len(self.model.get_file_names()))
            })
        else:
            file_index = self.view.current_file_index
            self.view.set_selected_indices(file_index, index_getter(file_index))