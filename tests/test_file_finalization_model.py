from src.MVC.models.file_finalization_model import FileFinalizationModel

def _finalize(tex_content, include_toc=False, include_headers_numeration=False):
    model = FileFinalizationModel(tex_content, {})
    model.refine_file(
        include_toc=include_toc,
        include_headers_numeration=include_headers_numeration,
    )
    return model.final_tex_content


def test_formulab_heading_markers_are_removed_without_options():
    tex_content = (
        "\\begin{document}\n"
        "\\FormuLabHeading{1}{Heading}\n"
        "\\addvspace{1.2em}\\noindent{\\LARGE\\bfseries Heading}\n"
        "\\end{document}\n"
    )

    result = _finalize(tex_content)
    assert "\\FormuLabHeading" not in result
    assert "\\addcontentsline" not in result
    assert "\\noindent{\\LARGE\\bfseries Heading}" in result


def test_formulab_heading_markers_create_table_of_contents_entries():
    tex_content = (
        "\\begin{document}\n"
        "\\FormuLabHeading{1}{Heading 1}\n"
        "\\addvspace{1.2em}\\noindent{\\LARGE\\bfseries Heading 1}\n"
        "\\FormuLabHeading{4}{Heading 4}\n"
        "\\addvspace{0.9em}\\noindent{\\normalsize\\bfseries Heading 4}\n"
        "\\end{document}\n"
    )

    result = _finalize(tex_content, include_toc=True)
    assert "\\setcounter{tocdepth}{5}" in result
    assert "\\tableofcontents" in result
    assert result.count("\\phantomsection") == 2
    assert "\\addcontentsline{toc}{section}{Heading 1}" in result
    assert "\\addcontentsline{toc}{paragraph}{Heading 4}" in result
    assert "\\FormuLabHeading" not in result

def test_formulab_heading_markers_add_visible_numbers():
    tex_content = (
        "\\begin{document}\n"
        "\\FormuLabHeading{1}{Heading 1}\n"
        "\\addvspace{1.2em}\\noindent{\\LARGE\\bfseries Heading 1}\n"
        "\\FormuLabHeading{2}{Heading 2}\n"
        "\\addvspace{1.1em}\\noindent{\\Large\\bfseries Heading 2}\n"
        "\\end{document}\n"
    )

    result = _finalize(tex_content, include_headers_numeration=True)
    assert "\\noindent{\\LARGE\\bfseries 1 Heading 1}" in result
    assert "\\noindent{\\Large\\bfseries 1.1 Heading 2}" in result
    assert "\\addcontentsline" not in result
    assert "\\FormuLabHeading" not in result

def test_formulab_heading_markers_support_toc_and_numbering_together():
    tex_content = (
        "\\begin{document}\n"
        "\\FormuLabHeading{1}{Heading 1}\n"
        "\\addvspace{1.2em}\\noindent{\\LARGE\\bfseries Heading 1}\n"
        "\\FormuLabHeading{2}{Heading 2}\n"
        "\\addvspace{1.1em}\\noindent{\\Large\\bfseries Heading 2}\n"
        "\\end{document}\n"
    )

    result = _finalize(tex_content, include_toc=True, include_headers_numeration=True)
    assert result.count("\\phantomsection") == 2
    assert "\\addcontentsline{toc}{section}{1 Heading 1}" in result
    assert "\\addcontentsline{toc}{subsection}{1.1 Heading 2}" in result
    assert "\\noindent{\\LARGE\\bfseries 1 Heading 1}" in result
    assert "\\noindent{\\Large\\bfseries 1.1 Heading 2}" in result


def test_formulab_heading_markers_are_processed_inside_text_lines():
    tex_content = (
        "\\begin{document}\n"
        "Some text before marker. \\FormuLabHeading{3}{Inline Heading}\n"
        "\\addvspace{1em}\\noindent{\\large\\bfseries Inline Heading}\n"
        "\\end{document}\n"
    )

    result = _finalize(tex_content, include_toc=True, include_headers_numeration=True)
    assert "\\FormuLabHeading" not in result
    assert "Some text before marker." in result
    assert "Some text before marker. \n\\phantomsection\n\\addcontentsline" in result
    assert "\\addcontentsline{toc}{subsubsection}{1.1.1 Inline Heading}" in result
    assert "\\noindent{\\large\\bfseries 1.1.1 Inline Heading}" in result


def test_modular_batch_export_creates_main_file_and_input_parts(tmp_path, monkeypatch):
    tex_part_1 = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\FormuLabHeading{1}{First}\n"
        "\\addvspace{1.2em}\\noindent{\\LARGE\\bfseries First}\n"
        "\\end{document}\n"
    )
    tex_part_2 = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\FormuLabHeading{1}{Second}\n"
        "\\addvspace{1.2em}\\noindent{\\LARGE\\bfseries Second}\n"
        "\\end{document}\n"
    )
    merged_tex = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\FormuLabHeading{1}{First}\n"
        "\\addvspace{1.2em}\\noindent{\\LARGE\\bfseries First}\n"
        "\\FormuLabHeading{1}{Second}\n"
        "\\addvspace{1.2em}\\noindent{\\LARGE\\bfseries Second}\n"
        "\\end{document}\n"
    )

    model = FileFinalizationModel(
        merged_tex,
        {},
        tex_parts=[
            {"name": "a_notebook.ipynb", "tex_content": tex_part_1},
            {"name": "b_notebook.ipynb", "tex_content": tex_part_2},
        ],
        is_batch=True,
    )
    model.refine_file(include_toc=True)
    monkeypatch.setattr("src.MVC.models.file_finalization_model.filedialog.askdirectory", lambda **_kwargs: str(tmp_path))

    model.save_file(strategy="modular")

    main_tex = (tmp_path / "main.tex").read_text(encoding="utf-8")
    first_part = (tmp_path / "parts" / "a_notebook.tex").read_text(encoding="utf-8")
    second_part = (tmp_path / "parts" / "b_notebook.tex").read_text(encoding="utf-8")

    assert "\\tableofcontents" in main_tex
    assert "\\input{parts/a_notebook.tex}" in main_tex
    assert "\\input{parts/b_notebook.tex}" in main_tex
    assert "\\addcontentsline{toc}{section}{First}" in first_part
    assert "\\addcontentsline{toc}{section}{Second}" in second_part
    assert "\\tableofcontents" not in first_part


def test_modular_batch_export_saves_images_next_to_main_file(tmp_path, monkeypatch):
    tex_part = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\adjustimage{max size={\\linewidth}{\\paperheight}}{image_0_0.png}\n"
        "\\end{document}\n"
    )

    model = FileFinalizationModel(
        tex_part,
        {"image_1.png": b"image-bytes"},
        tex_parts=[{"name": "plots.ipynb", "tex_content": tex_part}],
        is_batch=True,
    )
    model.refine_file()
    monkeypatch.setattr("src.MVC.models.file_finalization_model.filedialog.askdirectory", lambda **_kwargs: str(tmp_path))

    model.save_file(strategy="modular")

    part_tex = (tmp_path / "parts" / "plots.tex").read_text(encoding="utf-8")
    image_file = tmp_path / "main_FormuLab_images" / "image_1.png"
    assert "{main_FormuLab_images/image_1.png}" in part_tex
    assert image_file.read_bytes() == b"image-bytes"


def test_modular_batch_export_reuses_same_saved_image_for_duplicate_latex_references(tmp_path, monkeypatch):
    tex_part = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\adjustimage{max size={\\linewidth}{\\paperheight}}{image_0_0.png}\n"
        "\\adjustimage{max size={\\linewidth}{\\paperheight}}{image_0_0.png}\n"
        "\\end{document}\n"
    )

    model = FileFinalizationModel(
        tex_part,
        {"image_1.png": b"image-bytes"},
        tex_parts=[{"name": "plots.ipynb", "tex_content": tex_part}],
        is_batch=True,
    )
    model.refine_file()
    monkeypatch.setattr("src.MVC.models.file_finalization_model.filedialog.askdirectory", lambda **_kwargs: str(tmp_path))

    model.save_file(strategy="modular")

    part_tex = (tmp_path / "parts" / "plots.tex").read_text(encoding="utf-8")
    image_files = list((tmp_path / "main_FormuLab_images").glob("*.png"))
    assert part_tex.count("{main_FormuLab_images/image_1.png}") == 2
    assert "image_2.png" not in part_tex
    assert [image_file.name for image_file in image_files] == ["image_1.png"]


def test_modular_batch_export_treats_equal_temp_image_names_in_different_parts_as_different_images(tmp_path, monkeypatch):
    tex_part = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\adjustimage{max size={\\linewidth}{\\paperheight}}{image_0_0.png}\n"
        "\\end{document}\n"
    )

    model = FileFinalizationModel(
        tex_part + tex_part,
        {
            "image_1.png": b"first-image",
            "image_2.png": b"second-image",
        },
        tex_parts=[
            {"name": "first.ipynb", "tex_content": tex_part},
            {"name": "second.ipynb", "tex_content": tex_part},
        ],
        is_batch=True,
    )
    model.refine_file()
    monkeypatch.setattr("src.MVC.models.file_finalization_model.filedialog.askdirectory", lambda **_kwargs: str(tmp_path))

    model.save_file(strategy="modular")

    first_part = (tmp_path / "parts" / "first.tex").read_text(encoding="utf-8")
    second_part = (tmp_path / "parts" / "second.tex").read_text(encoding="utf-8")
    assert "{main_FormuLab_images/image_1.png}" in first_part
    assert "{main_FormuLab_images/image_2.png}" in second_part
    assert (tmp_path / "main_FormuLab_images" / "image_1.png").read_bytes() == b"first-image"
    assert (tmp_path / "main_FormuLab_images" / "image_2.png").read_bytes() == b"second-image"


def test_modular_batch_export_does_not_rename_non_nbconvert_image_references(tmp_path, monkeypatch):
    tex_part = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\adjustimage{max size={\\linewidth}{\\paperheight}}{local_plot.png}\n"
        "\\adjustimage{max size={\\linewidth}{\\paperheight}}{image_0_0.png}\n"
        "\\end{document}\n"
    )

    model = FileFinalizationModel(
        tex_part,
        {"image_1.png": b"image-bytes"},
        tex_parts=[{"name": "plots.ipynb", "tex_content": tex_part}],
        is_batch=True,
    )
    model.refine_file()
    monkeypatch.setattr("src.MVC.models.file_finalization_model.filedialog.askdirectory", lambda **_kwargs: str(tmp_path))

    model.save_file(strategy="modular")

    part_tex = (tmp_path / "parts" / "plots.tex").read_text(encoding="utf-8")
    assert "{local_plot.png}" in part_tex
    assert "{main_FormuLab_images/image_1.png}" in part_tex
    assert "image_2.png" not in part_tex


def test_modular_batch_export_downloads_remote_image_references(tmp_path, monkeypatch):
    remote_url = "https://drive.google.com/uc?id=13kmqLXa-3FBUJq0Q3XVOkz8TENpVTkqk&export=download"
    tex_part = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        f"\\pandocbounded{{\\includegraphics[keepaspectratio]{{{remote_url}}}}}\n"
        "\\end{document}\n"
    )

    model = FileFinalizationModel(
        tex_part,
        {},
        tex_parts=[{"name": "remote.ipynb", "tex_content": tex_part}],
        is_batch=True,
    )
    model.refine_file()
    monkeypatch.setattr("src.MVC.models.file_finalization_model.filedialog.askdirectory", lambda **_kwargs: str(tmp_path))
    monkeypatch.setattr(
        FileFinalizationModel,
        "_FileFinalizationModel__download_remote_image",
        staticmethod(lambda _url: (b"remote-image-bytes", ".png")),
    )

    model.save_file(strategy="modular")

    part_tex = (tmp_path / "parts" / "remote.tex").read_text(encoding="utf-8")
    remote_image_file = tmp_path / "main_FormuLab_images" / "remote_image_1.png"
    assert f"\\pandocbounded{{\\includegraphics[keepaspectratio]{{main_FormuLab_images/remote_image_1.png}}}}" in part_tex
    assert remote_url not in part_tex
    assert remote_image_file.read_bytes() == b"remote-image-bytes"


def test_modular_batch_export_uses_text_fallback_when_remote_image_download_fails(tmp_path, monkeypatch):
    remote_url = "https://drive.google.com/uc?id=13kmqLXa-3FBUJq0Q3XVOkz8TENpVTkqk&export=download"
    tex_part = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        f"\\pandocbounded{{\\includegraphics[keepaspectratio]{{{remote_url}}}}}\n"
        "\\end{document}\n"
    )

    model = FileFinalizationModel(
        tex_part,
        {},
        tex_parts=[{"name": "remote.ipynb", "tex_content": tex_part}],
        is_batch=True,
    )
    model.refine_file()
    monkeypatch.setattr("src.MVC.models.file_finalization_model.filedialog.askdirectory", lambda **_kwargs: str(tmp_path))
    monkeypatch.setattr(
        FileFinalizationModel,
        "_FileFinalizationModel__download_remote_image",
        staticmethod(lambda _url: None),
    )

    model.save_file(strategy="modular")

    part_tex = (tmp_path / "parts" / "remote.tex").read_text(encoding="utf-8")
    assert "\\adjustimage" not in part_tex
    assert "\\includegraphics" not in part_tex
    assert "\\noindent Remote image: \\url{" in part_tex