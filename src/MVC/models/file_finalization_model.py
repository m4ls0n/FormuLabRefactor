import os
import re
import urllib.request
from tkinter import filedialog
from src.utils.formulab_exceptions import FileNotSelectedException

class FileFinalizationModel:
    FORMULAB_HEADING_PATTERN = re.compile(
        r'\\FormuLabHeading\{(?P<level>[1-6])\}\{(?P<title>(?:\\[{}]|[^{}])*)\}'
    )
    FORMULAB_TOC_LEVELS = {
        1: "section",
        2: "subsection",
        3: "subsubsection",
        4: "paragraph",
        5: "subparagraph",
        6: "subparagraph",
    }

    def __init__(self, intermediate_tex_content, ipynb_images, tex_parts=None, is_batch=False):
        self.intermediate_tex_content = intermediate_tex_content
        self.ipynb_images = ipynb_images
        self.tex_parts = tex_parts or []
        self.final_tex_parts = []
        self.is_batch = is_batch
        self.final_tex_content = None

    def refine_file(self, include_toc=False, include_headers_numeration=False):
        """Дорабатывает tex-файл на основе выбранных опций."""
        self.final_tex_content = self.intermediate_tex_content

        if include_toc:
            self.__add_table_of_contents()

        self.__apply_formulab_heading_options(
            include_toc=include_toc,
            include_headers_numeration=include_headers_numeration
        )

        if include_headers_numeration:
            self.__add_header_numeration()

        # Случай, при котором необходимо принудительно включить ненумерованные заголовки в оглавление.
        if include_toc and not include_headers_numeration:
            self.__add_not_numbered_headers_to_toc()

        self.final_tex_parts = []
        for part in self.tex_parts:
            part_model = FileFinalizationModel(part["tex_content"], {})
            part_model.refine_file(
                include_toc=include_toc,
                include_headers_numeration=include_headers_numeration
            )
            self.final_tex_parts.append({
                "name": part["name"],
                "tex_content": part_model.final_tex_content,
            })

    def save_file(self, strategy="merge"):
        """Сохраняет доработанный tex-файл."""
        if self.final_tex_content is None:
            raise ValueError("Нет содержимого для сохранения.")

        if strategy == "modular" and self.is_batch:
            self.__save_modular_files()
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".tex", filetypes=[("LaTeX files", "*.tex")])

        if not file_path:
            raise FileNotSelectedException()

        # Определение папки для картинок рядом с tex-файлом.
        base, _ = os.path.splitext(os.path.basename(file_path))
        folder_name = f"{base}_FormuLab_images"
        img_folder = os.path.join(os.path.dirname(file_path), folder_name)
        remote_image_map = {}
        self.final_tex_content, _ = self.__localize_remote_image_references(
            self.final_tex_content,
            img_folder,
            folder_name,
            remote_image_map,
            0
        )

        # Сохранение изображений в отдельной папке, если они есть.
        if self.ipynb_images:
            # Шаг 1: сохранение изображений на ПК в отдельной папке.
            self.__save_images(img_folder)

            # Шаг 2: переименовывание файлов в latex-коде.
            self.__rename_files_in_latex_code()

            # Шаг 3: обновление путей в tex-контенте, добавляя папку перед названием файла.
            self.__add_image_folder_info(folder_name)

        with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.final_tex_content)

    def __save_modular_files(self):
        output_dir = filedialog.askdirectory(title="Выберите папку для модульной структуры")
        if not output_dir:
            raise FileNotSelectedException()

        parts_dir_name = "parts"
        parts_dir = os.path.join(output_dir, parts_dir_name)
        os.makedirs(parts_dir, exist_ok=True)

        folder_name = "main_FormuLab_images"
        saved_image_names = self.__get_saved_image_names()
        image_counter = 0
        if self.ipynb_images:
            self.__save_images(os.path.join(output_dir, folder_name))

        tex_parts = self.final_tex_parts or self.tex_parts
        used_part_names = set()
        input_paths = []
        remote_image_map = {}
        remote_image_counter = 0

        for part_index, part in enumerate(tex_parts, start=1):
            part_filename = self.__unique_part_filename(part["name"], used_part_names, part_index)
            part_path = os.path.join(parts_dir, part_filename)
            _, part_body = self.__split_latex_document(part["tex_content"])
            part_body = self.__remove_table_of_contents_commands(part_body)
            part_body, remote_image_counter = self.__localize_remote_image_references(
                part_body,
                os.path.join(output_dir, folder_name),
                folder_name,
                remote_image_map,
                remote_image_counter
            )

            if self.ipynb_images:
                part_body, image_counter = self.__rename_files_in_latex_content(
                    part_body,
                    {},
                    saved_image_names,
                    image_counter
                )
                part_body = self.__add_image_folder_info_to_content(
                    part_body,
                    folder_name,
                    saved_image_names
                )

            with open(part_path, "w", encoding="utf-8") as f:
                f.write(part_body.strip() + "\n")

            input_paths.append(f"{parts_dir_name}/{part_filename}")

        preamble, merged_body = self.__split_latex_document(self.final_tex_content)
        main_lines = [
            preamble.rstrip(),
            "\\begin{document}",
        ]

        if "\\tableofcontents" in merged_body:
            if "\\setcounter{tocdepth}{5}" in merged_body:
                main_lines.append("\\setcounter{tocdepth}{5}")
            main_lines.append("\\tableofcontents")

        main_lines.extend(
            f"\\input{{{input_path}}}"
            for input_path in input_paths
        )
        main_lines.append("\\end{document}")

        with open(os.path.join(output_dir, "main.tex"), "w", encoding="utf-8") as f:
            f.write("\n".join(line for line in main_lines if line) + "\n")

    def __save_images(self, output_dir):
        """
        Сохраняет все извлеченные картинки в указанную папку.
        """
        if not self.ipynb_images:
            return
        os.makedirs(output_dir, exist_ok=True)
        for saved_name, data in zip(self.__get_saved_image_names(), self.ipynb_images.values()):
            with open(os.path.join(output_dir, saved_name), 'wb') as f:
                f.write(data)

    def __get_saved_image_names(self):
        saved_names = []
        for index, original_name in enumerate(self.ipynb_images, start=1):
            _, ext = os.path.splitext(original_name)
            saved_names.append(f"image_{index}{ext or '.png'}")
        return saved_names

    def __rename_files_in_latex_code(self):
        r"""
        Переименовывает файлы в latex-коде.

        Случай 1:
          \\adjustimage{...}{old.png} ->

          \\adjustimage{...}{image_1.png}
        Случай 2:
          \\pandocbounded{\\includegraphics[...] {old.png}} ->

          \\pandocbounded{\\includegraphics[...] {image_1.png}}
        """
        self.final_tex_content = self.__rename_files_in_latex_content(
            self.final_tex_content,
            {},
            self.__get_saved_image_names(),
            0
        )[0]

    @staticmethod
    def __rename_files_in_latex_content(tex_content, image_name_map, saved_image_names, start_index):
        next_image_index = start_index

        def repl(match):
            nonlocal next_image_index
            if match.group(1):
                original_name = match.group(2)
                if not FileFinalizationModel.__is_nbconvert_generated_image_name(original_name):
                    return match.group(0)
                new_name, next_image_index = FileFinalizationModel.__get_mapped_image_name(
                    original_name,
                    image_name_map,
                    saved_image_names,
                    next_image_index
                )
                return match.group(1) + "{" + new_name + "}"

            original_name = match.group(4)
            if not FileFinalizationModel.__is_nbconvert_generated_image_name(original_name):
                return match.group(0)
            new_name, next_image_index = FileFinalizationModel.__get_mapped_image_name(
                original_name,
                image_name_map,
                saved_image_names,
                next_image_index
            )
            return match.group(3) + new_name + "}"

        image_pattern = re.compile(
            r'(\\adjustimage\{(?:[^{}]|\{[^{}]*\})*\})\{([^}]+)\}'
            r'|'
            r'(\\pandocbounded\{\\includegraphics\[[^\]]*\]\{)([^}]+)\}'
        )
        return image_pattern.sub(repl, tex_content), next_image_index

    @staticmethod
    def __is_nbconvert_generated_image_name(image_name):
        normalized_image_name = image_name.replace("\\", "/").split("/")[-1]
        return bool(re.fullmatch(r'image_\d+_\d+\.[A-Za-z0-9+]+', normalized_image_name))

    @staticmethod
    def __get_mapped_image_name(original_name, image_name_map, saved_image_names, next_image_index):
        normalized_original_name = original_name.replace("\\", "/").split("/")[-1]
        if normalized_original_name not in image_name_map:
            if next_image_index >= len(saved_image_names):
                raise ValueError(
                    "Количество ссылок на изображения в LaTeX превышает количество "
                    "извлеченных изображений из notebook."
                )
            image_name_map[normalized_original_name] = saved_image_names[next_image_index]
            next_image_index += 1
        return image_name_map[normalized_original_name], next_image_index

    def __add_image_folder_info(self, folder_name):
        r"""
        Добавляет префикс папки к путям изображений в tex-контенте.

        Случай 1:
          \\adjustimage{...}{image_1.png} ->

          \\adjustimage{...}{folder_name/image_1.png}
        Случай 2:
          \\pandocbounded{\\includegraphics[...]{image_1.png}} ->

          \\pandocbounded{\\includegraphics[...]{folder_name/image_1.png}}
        """

        saved_image_names = self.__get_saved_image_names()

        # Случай 1: обработка adjustimage.
        pattern = r'(\\adjustimage\{(?:[^{}]|\{[^{}]*\})*\})\{([^}]+)\}'
        self.final_tex_content = re.sub(
            pattern,
            lambda match: self.__add_folder_to_image_match(match, folder_name, saved_image_names),
            self.final_tex_content
        )

        # Случай 2: обработка pandocbounded + includegraphics.
        pattern2 = r'(\\pandocbounded\{\\includegraphics\[[^\]]*\]\{)([^}]+)\}'
        self.final_tex_content = re.sub(
            pattern2,
            lambda match: self.__add_folder_to_image_match(match, folder_name, saved_image_names),
            self.final_tex_content
        )

    @staticmethod
    def __add_image_folder_info_to_content(tex_content, folder_name, saved_image_names):
        pattern = r'(\\adjustimage\{(?:[^{}]|\{[^{}]*\})*\})\{([^}]+)\}'
        tex_content = re.sub(
            pattern,
            lambda match: FileFinalizationModel.__add_folder_to_image_match(
                match,
                folder_name,
                saved_image_names
            ),
            tex_content
        )

        pattern2 = r'(\\pandocbounded\{\\includegraphics\[[^\]]*\]\{)([^}]+)\}'
        return re.sub(
            pattern2,
            lambda match: FileFinalizationModel.__add_folder_to_image_match(
                match,
                folder_name,
                saved_image_names
            ),
            tex_content
        )

    @staticmethod
    def __add_folder_to_image_match(match, folder_name, saved_image_names):
        image_name = match.group(2)
        normalized_image_name = image_name.replace("\\", "/").split("/")[-1]
        if normalized_image_name not in saved_image_names:
            return match.group(0)
        return match.group(1) + "{" + folder_name + "/" + image_name + "}"

    @staticmethod
    def __localize_remote_image_references(
            tex_content,
            image_output_dir,
            latex_folder_name,
            remote_image_map,
            remote_image_counter
    ):
        def repl(match):
            nonlocal remote_image_counter
            image_name = match.group("image_name")
            if not FileFinalizationModel.__is_remote_image_reference(image_name):
                return match.group(0)

            local_image_name = remote_image_map.get(image_name)
            if not local_image_name:
                downloaded_image = FileFinalizationModel.__download_remote_image(image_name)
                if not downloaded_image:
                    return FileFinalizationModel.__remote_image_fallback(image_name)

                remote_image_counter += 1
                image_data, image_extension = downloaded_image
                local_image_name = f"remote_image_{remote_image_counter}{image_extension}"
                os.makedirs(image_output_dir, exist_ok=True)
                with open(os.path.join(image_output_dir, local_image_name), "wb") as image_file:
                    image_file.write(image_data)
                remote_image_map[image_name] = local_image_name

            return match.group("prefix") + latex_folder_name + "/" + local_image_name + match.group("suffix")

        pandocbounded_pattern = re.compile(
            r'(?P<prefix>\\pandocbounded\{\\includegraphics(?:\[[^\]]*\])?\{)'
            r'(?P<image_name>[^{}]+)'
            r'(?P<suffix>\}\})'
        )
        adjustimage_pattern = re.compile(
            r'(?P<prefix>\\adjustimage\{(?:[^{}]|\{[^{}]*\})*\}\{)'
            r'(?P<image_name>[^{}]+)'
            r'(?P<suffix>\})'
        )
        includegraphics_pattern = re.compile(
            r'(?P<prefix>\\includegraphics(?:\[[^\]]*\])?\{)'
            r'(?P<image_name>[^{}]+)'
            r'(?P<suffix>\})'
        )

        tex_content = pandocbounded_pattern.sub(repl, tex_content)
        tex_content = adjustimage_pattern.sub(repl, tex_content)
        tex_content = includegraphics_pattern.sub(repl, tex_content)
        return tex_content, remote_image_counter

    @staticmethod
    def __is_remote_image_reference(image_name):
        return image_name.startswith(("http://", "https://"))

    @staticmethod
    def __download_remote_image(image_url):
        try:
            request = urllib.request.Request(
                image_url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                image_data = response.read()
                content_type = response.headers.get_content_type()
        except Exception:
            return None

        image_extension = FileFinalizationModel.__detect_image_extension(image_data, content_type)
        if not image_extension:
            return None
        return image_data, image_extension

    @staticmethod
    def __detect_image_extension(image_data, content_type):
        if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if image_data.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if image_data.startswith(b"%PDF"):
            return ".pdf"
        if image_data.startswith((b"GIF87a", b"GIF89a")):
            return ".gif"

        content_type_extensions = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "application/pdf": ".pdf",
            "image/gif": ".gif",
        }
        return content_type_extensions.get(content_type)

    @staticmethod
    def __remote_image_fallback(image_url):
        return f"\\noindent Remote image: \\url{{{image_url}}}"

    @staticmethod
    def __split_latex_document(tex_content):
        begin_marker = "\\begin{document}"
        end_marker = "\\end{document}"
        begin_index = tex_content.find(begin_marker)

        if begin_index == -1:
            return "", tex_content

        preamble = tex_content[:begin_index]
        body_start = begin_index + len(begin_marker)
        end_index = tex_content.rfind(end_marker)
        if end_index == -1:
            return preamble, tex_content[body_start:]

        return preamble, tex_content[body_start:end_index]

    @staticmethod
    def __remove_table_of_contents_commands(tex_content):
        tex_content = re.sub(r'^[ \t]*\\setcounter\{tocdepth\}\{5\}[ \t]*\r?\n?', '', tex_content, flags=re.MULTILINE)
        tex_content = re.sub(r'^[ \t]*\\tableofcontents[ \t]*\r?\n?', '', tex_content, flags=re.MULTILINE)
        return tex_content

    @staticmethod
    def __unique_part_filename(source_name, used_names, part_index):
        base_name, _ = os.path.splitext(source_name)
        safe_name = re.sub(r'[^A-Za-z0-9_-]+', '_', base_name).strip('_')
        if not safe_name:
            safe_name = f"notebook_{part_index}"

        candidate = f"{safe_name}.tex"
        suffix = 2
        while candidate.lower() in used_names:
            candidate = f"{safe_name}_{suffix}.tex"
            suffix += 1

        used_names.add(candidate.lower())
        return candidate

    def __add_table_of_contents(self):
        """Добавляет оглавление в tex-файл."""
        self.final_tex_content = self.final_tex_content.replace(
            "\\begin{document}",
            "\\begin{document}\n\\setcounter{tocdepth}{5}\n\\tableofcontents",
            1
        )

    def __apply_formulab_heading_options(self, include_toc=False, include_headers_numeration=False):
        tex_lines = self.final_tex_content.splitlines(keepends=True)
        new_tex_lines = []
        heading_counters = [0] * 6
        pending_heading = None

        for line in tex_lines:
            line_without_markers = []
            current_position = 0
            for heading_match in self.FORMULAB_HEADING_PATTERN.finditer(line):
                line_without_markers.append(line[current_position:heading_match.start()])
                level = int(heading_match.group("level"))
                title = heading_match.group("title")
                heading_number = None

                if include_headers_numeration:
                    heading_number = self.__next_heading_number(heading_counters, level)

                if include_toc:
                    toc_title = f"{heading_number} {title}" if heading_number else title
                    toc_level = self.FORMULAB_TOC_LEVELS[level]
                    if line_without_markers and not line_without_markers[-1].endswith(("\n", "\r")):
                        line_without_markers.append("\n")
                    line_without_markers.append(
                        f"\\phantomsection\n\\addcontentsline{{toc}}{{{toc_level}}}{{{toc_title}}}\n"
                    )

                pending_heading = {
                    "title": title,
                    "number": heading_number,
                }
                current_position = heading_match.end()

            if current_position:
                line_without_markers.append(line[current_position:])
                line = "".join(line_without_markers)

            if pending_heading and pending_heading["title"] in line and "\\addcontentsline" not in line:
                if pending_heading["number"]:
                    line = line.replace(
                        pending_heading["title"],
                        f"{pending_heading['number']} {pending_heading['title']}",
                        1
                    )
                pending_heading = None

            new_tex_lines.append(line)

        self.final_tex_content = "".join(new_tex_lines)

    @staticmethod
    def __next_heading_number(heading_counters, level):
        level_index = level - 1
        for index in range(level_index):
            if heading_counters[index] == 0:
                heading_counters[index] = 1

        heading_counters[level_index] += 1

        for index in range(level, len(heading_counters)):
            heading_counters[index] = 0

        return ".".join(str(counter) for counter in heading_counters[:level] if counter)

    def __add_header_numeration(self):
        """Добавляет нумерацию заголовков h1-h5 в tex-файл."""
        # Разбиваем исходный tex-файл построчно.
        tex_lines = self.final_tex_content.split("\n")

        # Убираем * из секционных команд для возврата нумерации заголовков h1-h5.
        tex_lines = [
            line if not any(
                line.strip().startswith(command) for command in [
                    "\\section",
                    "\\subsection",
                    "\\subsubsection",
                    "\\paragraph",
                    "\\subparagraph",
                ])
            else line.replace("\\section*", "\\section").replace("\\subsection*", "\\subsection").replace(
                "\\subsubsection*", "\\subsubsection").replace("\\paragraph*", "\\paragraph").replace(
                "\\subparagraph*", "\\subparagraph")
            for line in tex_lines
        ]

        self.final_tex_content = "\n".join(tex_lines)

    def __add_not_numbered_headers_to_toc(self):
        """Добавляет ненумерованные заголовки в оглавление."""
        tex_lines = self.final_tex_content.split("\n")
        new_tex_lines = []

        for i, line in enumerate(tex_lines):
            # Проверяем, начинается ли строка с ненумерованного заголовка.
            if line.strip().startswith((
                    "\\section*{",
                    "\\subsection*{",
                    "\\subsubsection*{",
                    "\\paragraph*{",
                    "\\subparagraph*{",
            )):
                # Определяем уровень заголовка.
                if line.strip().startswith("\\section*{"):
                    level = "section"
                elif line.strip().startswith("\\subsection*{"):
                    level = "subsection"
                elif line.strip().startswith("\\subsubsection*{"):
                    level = "subsubsection"
                elif line.strip().startswith("\\paragraph*{"):
                    level = "paragraph"
                else:
                    level = "subparagraph"

                # Извлекаем название заголовка (может быть на одной или нескольких строках).
                header_content = line.split("{", 1)[1] if "{" in line else ""
                if not header_content.endswith("}"):
                    for j in range(i + 1, len(tex_lines)):
                        header_content += tex_lines[j].strip()
                        if tex_lines[j].strip().endswith("}"):
                            break
                header_content = header_content.rstrip("}")

                # Добавляем строку для оглавления ПЕРЕД самой строкой с заголовком.
                new_tex_lines.append(f"\\addcontentsline{{toc}}{{{level}}}{{{header_content}}}")

            # Добавляем саму строку с заголовком.
            new_tex_lines.append(line)

        self.final_tex_content = "\n".join(new_tex_lines)