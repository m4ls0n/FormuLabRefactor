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