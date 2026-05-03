import nbformat

from src.MVC.models.main_menu_model import MainMenuModel


def _write_notebook(path, cell_source):
    notebook = nbformat.v4.new_notebook()
    notebook.cells = [nbformat.v4.new_markdown_cell(cell_source)]
    nbformat.write(notebook, path)


def test_folder_loading_keeps_notebooks_in_alphabetical_order(tmp_path):
    _write_notebook(tmp_path / "b_second.ipynb", "second")
    _write_notebook(tmp_path / "a_first.ipynb", "first")

    model = MainMenuModel()
    model.load_notebooks_from_folder(str(tmp_path))

    assert [source["name"] for source in model.notebook_sources] == [
        "a_first.ipynb",
        "b_second.ipynb",
    ]
    assert [cell["source"] for cell in model.notebook_data["cells"]] == [
        "first",
        "second",
    ]