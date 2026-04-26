import base64
import nbformat
from src.MVC.models.cell_selector_model import CellSelectorModel

def _replace_markdown_headings(markdown_source):
    return CellSelectorModel._CellSelectorModel__replace_markdown_headings(markdown_source)


def _validate_tex(tex_content):
    return CellSelectorModel._CellSelectorModel__validate_tex(tex_content)


def _image_output(raw_bytes, filename="image_0.png"):
    encoded_image = base64.b64encode(raw_bytes).decode("ascii")
    return nbformat.v4.new_output(
        output_type="display_data",
        data={"image/png": encoded_image},
        metadata={"filename": filename},
    )


def test_markdown_headings_are_translated_to_visual_latex_blocks():
    markdown_source = (
        "# Heading 1\n"
        "## Heading 2\n"
        "### Heading 3\n"
        "#### Heading 4\n"
        "##### Heading 5\n"
        "###### Heading 6\n"
    )

    result = _replace_markdown_headings(markdown_source)
    assert r"\noindent{\LARGE\bfseries Heading 1}" in result
    assert r"\noindent{\Large\bfseries Heading 2}" in result
    assert r"\noindent{\large\bfseries Heading 3}" in result
    assert r"\noindent{\normalsize\bfseries Heading 4}" in result
    assert r"\noindent{\small\bfseries Heading 5}" in result
    assert r"\noindent{\footnotesize\bfseries Heading 6}" in result
    assert result.count(r"\par\nobreak\vspace") == 6

def test_markdown_heading_parser_ignores_fenced_code_blocks_and_escapes_text():
    markdown_source = (
        "## Value_A & B ###\n"
        "```python\n"
        "### Not a heading\n"
        "```\n"
    )

    result = _replace_markdown_headings(markdown_source)
    assert r"\noindent{\Large\bfseries Value\_A \& B}" in result
    assert "### Not a heading" in result
    assert r"\large\bfseries Not a heading" not in result


def test_multiple_image_outputs_are_extracted_and_filename_metadata_is_ignored():
    notebook = nbformat.v4.new_notebook()
    notebook.cells = [
        nbformat.v4.new_code_cell(
            "plot one and two",
            outputs=[
                _image_output(b"first-image"),
                _image_output(b"second-image"),
            ],
        ),
        nbformat.v4.new_code_cell(
            "plot three",
            outputs=[
                _image_output(b"third-image"),
            ],
        ),
    ]

    model = CellSelectorModel(notebook)
    model.convert_to_tex([1, 2])
    assert list(model.ipynb_images) == ["image_1.png", "image_2.png", "image_3.png"]
    assert model.ipynb_images["image_1.png"] == b"first-image"
    assert model.ipynb_images["image_2.png"] == b"second-image"
    assert model.ipynb_images["image_3.png"] == b"third-image"
    assert model.tex_content is not None


def test_display_math_blocks_are_wrapped_with_breqn_dmath():
    tex_content = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\[\n"
        "x_1+x_2+x_3+x_4+x_5+x_6+x_7+x_8+x_9+x_{10}=0\n"
        "\\]\n"
        "\\end{document}\n"
    )

    result = _validate_tex(tex_content)
    assert "\\usepackage{breqn}" in result
    assert "\\begin{dmath*}" in result
    assert "x_1+x_2+x_3" in result
    assert "\\end{dmath*}" in result
    assert "\\[\n" not in result
    assert "\\]\n" not in result

def test_markdown_display_math_is_converted_to_dmath_through_public_conversion():
    formula = "x_1+x_2+" * 30 + "x_n=0"
    notebook = nbformat.v4.new_notebook()
    notebook.cells = [
        nbformat.v4.new_markdown_cell(f"$$\n{formula}\n$$"),
    ]

    model = CellSelectorModel(notebook)
    model.convert_to_tex([1])
    assert model.tex_content.count("\\begin{dmath*}") == 1
    assert formula in model.tex_content
    assert model.tex_content.count("\\end{dmath*}") == 1