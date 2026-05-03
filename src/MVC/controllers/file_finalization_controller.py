from tkinter import messagebox

from src.MVC.models.file_finalization_model import FileFinalizationModel
from src.MVC.views.file_finalization_view import FileFinalizationView
from src.utils.formulab_exceptions import FileNotSelectedException


class FileFinalizationController:
    def __init__(self, app, intermediate_tex_content, ipynb_images, tex_parts=None, is_batch=False):
        self.app = app
        self.model = FileFinalizationModel(intermediate_tex_content, ipynb_images, tex_parts, is_batch)
        self.view = FileFinalizationView(self, intermediate_tex_content, is_batch)

    def finalize_file(self):
        self.model.refine_file(
            include_toc=self.view.is_table_of_contents_included.get(),
            include_headers_numeration=self.view.is_headers_numeration_included.get()
        )

        try:
            self.model.save_file(self.view.export_strategy.get())
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")
            return
        except FileNotSelectedException:
            messagebox.showwarning("Предупреждение", "Вы не выбрали место для сохранения.")
            return
        except Exception as e:
            messagebox.showerror("Неизвестная ошибка", f"Произошла ошибка при сохранении файла: {e}")
            return

        self.app.show_main_menu()

    def back(self):
        self.app.show_cell_selector()