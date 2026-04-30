import base64
import nbformat
import re
from copy import deepcopy
from nbconvert import LatexExporter
from nbconvert.filters import escape_latex
from re import sub, DOTALL
from traitlets.config import Config

class CellSelectorModel:
    MARKDOWN_HEADING_STYLES = {
        1: ("\\LARGE", "1.2em", "0.8em"),
        2: ("\\Large", "1.1em", "0.7em"),
        3: ("\\large", "1em", "0.6em"),
        4: ("\\normalsize", "0.9em", "0.5em"),
        5: ("\\small", "0.8em", "0.45em"),
        6: ("\\footnotesize", "0.7em", "0.4em"),
    }

    def __init__(self, notebook_data):
        self.notebook_data = notebook_data
        self.tex_content = None
        self.ipynb_images = {}

    def get_cells(self):
        return self.notebook_data['cells'] if self.notebook_data else []

    def get_all_cell_indices(self):
        return list(range(1, len(self.get_cells()) + 1))

    def get_markdown_cell_indices(self):
        return self.__get_cell_indices_by_predicate(
            lambda cell: cell.get('cell_type') == 'markdown'
        )

    def get_code_cell_indices(self):
        return self.__get_cell_indices_by_predicate(
            lambda cell: cell.get('cell_type') == 'code'
        )

    def get_output_cell_indices(self):
        return self.__get_cell_indices_by_predicate(
            lambda cell: bool(cell.get('outputs'))
        )

    def __get_cell_indices_by_predicate(self, predicate):
        return [
            cell_index
            for cell_index, cell in enumerate(self.get_cells(), start=1)
            if predicate(cell)
        ]

    def convert_to_tex(self, selected_indices):
        # Нумерация в selected_indices идет с 1, а в notebook_data с 0.
        selected_cells = [deepcopy(self.notebook_data['cells'][i - 1]) for i in selected_indices]
        selected_cells = CellSelectorModel.__convert_markdown_headings(selected_cells)
        selected_cells = CellSelectorModel.__clear_image_output_filenames(selected_cells)
        temp_notebook = nbformat.v4.new_notebook()
        temp_notebook.cells = selected_cells

        self.__extract_images(selected_cells)

        c = Config()
        c.ExtractOutputPreprocessor.output_filename_template = "image_{cell_index}_{index}{extension}"

        latex_exporter = LatexExporter(config=c)
        try:
            tex_content, _ = latex_exporter.from_notebook_node(temp_notebook)
            tex_content = CellSelectorModel.__validate_tex(tex_content)
            self.tex_content = tex_content
        except Exception as e:
            raise Exception(f"Ошибка экспорта в LaTeX: {e}")

    def __extract_images(self, cells):
        """
        Проходит по всем output- и attachment-данным ячеек,
        извлекает картинки и сохраняет их в self.ipynb_images.
        """
        counter = 1
        for cell in cells:
            # Из выходных данных ячеек.
            for output in cell.get('outputs', []):
                for mime, content in output.get('data', {}).items():
                    if mime.startswith('image/'):
                        ext = mime.split('/')[1]
                        img_data = base64.b64decode(content)
                        name = f'image_{counter}.{ext}'
                        self.ipynb_images[name] = img_data
                        counter += 1
            # Из attachment в markdown.
            for attachment in cell.get('attachments', {}).values():
                for mime, content in attachment.items():
                    if mime.startswith('image/'):
                        ext = mime.split('/')[1]
                        img_data = base64.b64decode(content)
                        name = f'attach_{counter}.{ext}'
                        self.ipynb_images[name] = img_data
                        counter += 1

    @staticmethod
    def __clear_image_output_filenames(cells):
        for cell in cells:
            for output in cell.get('outputs', []):
                if not any(mime.startswith('image/') for mime in output.get('data', {})):
                    continue

                metadata = output.get('metadata')
                if not metadata:
                    continue

                metadata.pop('filename', None)
                metadata.pop('filenames', None)

        return cells

    @staticmethod
    def __convert_markdown_headings(cells):
        for cell in cells:
            if cell.get('cell_type') != 'markdown':
                continue

            source = cell.get('source', '')
            if isinstance(source, list):
                source = ''.join(source)

            cell['source'] = CellSelectorModel.__replace_markdown_headings(source)

        return cells

    @staticmethod
    def __replace_markdown_headings(markdown_source):
        result_lines = []
        in_fenced_block = False
        fence_char = None
        fence_length = 0

        for line in markdown_source.splitlines(keepends=True):
            line_body = line.rstrip('\r\n')
            line_ending = line[len(line_body):]

            fence_match = re.match(r'^[ \t]{0,3}(`{3,}|~{3,})', line_body)
            if fence_match:
                marker = fence_match.group(1)
                marker_char = marker[0]
                marker_length = len(marker)
                if not in_fenced_block:
                    in_fenced_block = True
                    fence_char = marker_char
                    fence_length = marker_length
                elif marker_char == fence_char and marker_length >= fence_length:
                    in_fenced_block = False
                    fence_char = None
                    fence_length = 0
                result_lines.append(line)
                continue

            if in_fenced_block:
                result_lines.append(line)
                continue

            heading_match = re.match(r'^[ \t]{0,3}(#{1,6})(?!#)(?:[ \t]+|$)(.*)$', line_body)
            if not heading_match:
                result_lines.append(line)
                continue

            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            heading_text = re.sub(r'[ \t]+#+[ \t]*$', '', heading_text).strip()
            escaped_heading = escape_latex(heading_text)
            size_command, top_space, bottom_space = CellSelectorModel.MARKDOWN_HEADING_STYLES[level]

            result_lines.append(
                rf"\FormuLabHeading{{{level}}}{{{escaped_heading}}}" + "\n"
                rf"\par\addvspace{{{top_space}}}\noindent{{{size_command}\bfseries {escaped_heading}}}"
                rf"\par\nobreak\vspace{{{bottom_space}}}{line_ending}"
            )

        return ''.join(result_lines)

    @staticmethod
    def __validate_tex(tex_content):
        tex_lines = tex_content.split("\n")
        tex_lines = CellSelectorModel.__add_required_libraries(tex_lines)
        tex_lines = CellSelectorModel.__comment_title(tex_lines)
        tex_lines = CellSelectorModel.__remove_labels(tex_lines)
        tex_lines = CellSelectorModel.__handle_long_math_formulas(tex_lines)
        return "\n".join(tex_lines)

    @staticmethod
    def __comment_title(tex_lines):
        # Комментируем \maketitle, если он есть.
        tex_lines = [
            "% \\maketitle" if line.strip() == "\\maketitle" else line
            for line in tex_lines
        ]

        return tex_lines

    @staticmethod
    def __add_required_libraries(tex_lines):
        header_insert = (
            # Заголовки для поддержки русского языка.
            "\\usepackage[T2A]{fontenc}\n"
            "\\usepackage[utf8]{inputenc} % Для поддержки Unicode (UTF-8)\n"
            "\\usepackage[russian]{babel} % Подключение русского языка\n"
            # Поддержка валидного отображения длинных математических формул.
            "% Поддержка валидного отображения длинных математических формул\n"
            "\\usepackage{breqn}\n"
            # Обёртка Pandoc – ограничивает размер картинки размерами текста и страницы.
            "% Обёртка Pandoc – ограничивает размер картинки размерами текста и страницы\n"
            "\\newcommand{\\pandocbounded}[1]{\n"
            "    \\adjustbox{max size={\\linewidth}{\\paperheight}}{#1}\n"
            "}\n"
        )

        if tex_lines and tex_lines[0].startswith("\\documentclass"):
            tex_lines.insert(1, header_insert)

        return tex_lines

    @staticmethod
    def __remove_labels(tex_lines):
        # Используем регулярное выражение для удаления \label{...}.
        tex_lines = [
            sub(r'\\label\{.*?}', '', line)  # Заменяем \label{...} на пустую строку.
            for line in tex_lines
        ]
        return tex_lines

    @staticmethod
    def __handle_long_math_formulas(tex_lines):
        """
        Ищет блоки формул, оформленные как $\displaystyle ...$, и если их содержимое превышает заданный порог,
        заменяет их на окружение display math (например, dmath* из пакета breqn), которое обеспечивает
        автоматический перенос строк.
        """
        threshold = 200  # Пороговое значение длины математической формулы.
        tex_str = "\n".join(tex_lines)

        def replace_display_math(match):
            content = match.group(1).strip()
            if not content:
                return match.group(0)
            return "\\begin{dmath*}\n" + content + "\n\\end{dmath*}"

        tex_str = sub(r'\\\[\s*(.*?)\s*\\\]', replace_display_math, tex_str, flags=DOTALL)
        tex_str = sub(r'\$\$\s*(.*?)\s*\$\$', replace_display_math, tex_str, flags=DOTALL)

        def replace_inline_math(match):
            content = match.group(1).strip()
            if len(content) > threshold:
                # Меняем на окружение dmath* для автоматического переноса длинных формул.
                return "\\begin{dmath*}\n" + content + "\n\\end{dmath*}"
            else:
                # Оставляем как есть.
                return match.group(0)

        # Ищем конструкции вида $\displaystyle ...$.
        tex_str = sub(r'\$\\displaystyle\s*(.*?)\$', replace_inline_math, tex_str, flags=DOTALL)
        return tex_str.split("\n")