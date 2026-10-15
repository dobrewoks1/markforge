"""Оконное приложение MarkForge (Tkinter).

Главный интерфейс для ПК: перетаскивание файлов, выбор формата-цели,
пакетная конвертация с отдельным статусом по каждому файлу, настройки,
переключение языка RU/EN. Конвертация идёт в фоновом потоке, интерфейс
не подвисает.
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from markforge import __version__
from markforge.core.engine import convert
from markforge.core.errors import MarkForgeError
from markforge.core.formats import (
    INPUT_EXTENSIONS,
    Format,
    coerce_format,
    detect_format,
)
from markforge.core.options import ConvertOptions, EpubMetadata
from markforge.core.presets import list_presets
from markforge.surfaces.i18n import I18n

# Drag & drop — опционально (tkinterdnd2). Без него работают кнопки.
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    _HAS_DND = True
except Exception:  # pragma: no cover
    _HAS_DND = False

_TARGETS = [Format.MARKDOWN, Format.DOCX, Format.EPUB, Format.HTML, Format.PDF]
_BACKENDS = ["auto", "pandoc", "native"]

BG = "#f4f5f7"
ACCENT = "#2d6cdf"
ACCENT_ACTIVE = "#2559bd"


class ConverterApp:
    def __init__(self) -> None:
        self.i18n = I18n("ru")
        self.root = TkinterDnD.Tk() if _HAS_DND else tk.Tk()
        self.root.title(self.i18n.t("app_title"))
        self.root.geometry("880x600")
        self.root.minsize(760, 540)
        self.root.configure(bg=BG)

        self._queue: "queue.Queue" = queue.Queue()
        self._i18n_widgets: List[tuple] = []  # (widget, attr, key)
        self._paths: List[Path] = []
        self.last_output_dir: Optional[Path] = None

        self._setup_style()
        self._build_menu()
        self._build_layout()
        self._retranslate()
        self._check_pandoc()
        self._fit_to_content()

    def _fit_to_content(self) -> None:
        """Окно не меньше, чем нужно содержимому (иначе обрезается нижняя панель)."""
        self.root.update_idletasks()
        req_w, req_h = self.root.winfo_reqwidth(), self.root.winfo_reqheight()
        self.root.minsize(max(760, req_w), max(540, req_h))
        self.root.geometry(f"{max(880, req_w)}x{max(600, req_h + 40)}")

    # --------------------------------------------------------------- style
    def _setup_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:  # pragma: no cover
            pass
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI Semibold", 11))
        style.configure("Hint.TLabel", foreground="#8a8f98")
        style.configure("TLabelframe", background=BG)
        style.configure("TLabelframe.Label", background=BG, font=("Segoe UI Semibold", 10))
        style.configure("TCheckbutton", background=BG, font=("Segoe UI", 10))
        style.configure("TRadiobutton", background=BG, font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 11),
                        foreground="white", background=ACCENT, padding=8)
        style.map("Accent.TButton",
                  background=[("active", ACCENT_ACTIVE), ("disabled", "#9db6e6")])
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=24)
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10))

    def _reg(self, widget, key: str, attr: str = "text") -> None:
        self._i18n_widgets.append((widget, attr, key))

    # ---------------------------------------------------------------- menu
    def _build_menu(self) -> None:
        # tearoff=0: иначе индекс 0 занимает «отрывная» строка и индексы пунктов сдвигаются
        menubar = tk.Menu(self.root, tearoff=0)
        self._lang_menu_index = 0
        menubar.add_command(label="RU / EN", command=self._toggle_lang)
        menubar.add_command(label=self.i18n.t("menu_about"), command=self._about)
        self.root.config(menu=menubar)
        self._menubar = menubar

    # -------------------------------------------------------------- layout
    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=3)
        outer.columnconfigure(1, weight=2)
        outer.rowconfigure(0, weight=1)

        self._build_files_panel(outer)
        self._build_settings_panel(outer)
        self._build_bottom_bar()

    def _build_files_panel(self, parent) -> None:
        frame = ttk.Labelframe(parent, padding=8)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)
        self._reg(frame, "files")
        self.files_frame = frame

        self.hint = ttk.Label(frame, style="Hint.TLabel", anchor="center", justify="center")
        self.hint.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self._reg(self.hint, "drop_hint")

        tree = ttk.Treeview(frame, columns=("status",), show="tree headings", height=12)
        tree.column("#0", width=340, anchor="w")
        tree.column("status", width=110, anchor="center")
        tree.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        tree.configure(yscrollcommand=scroll.set)
        tree.tag_configure("ok", foreground="#1a7f37")
        tree.tag_configure("fail", foreground="#cf222e")
        tree.tag_configure("skip", foreground="#8a8f98")
        self.tree = tree

        if _HAS_DND:
            tree.drop_target_register(DND_FILES)
            tree.dnd_bind("<<Drop>>", self._on_drop)
            self.hint.drop_target_register(DND_FILES)
            self.hint.dnd_bind("<<Drop>>", self._on_drop)

        btns = ttk.Frame(frame)
        btns.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        b_add = ttk.Button(btns, command=self._add_files_dialog)
        b_add.pack(side="left")
        self._reg(b_add, "add_files")
        b_rm = ttk.Button(btns, command=self._remove_selected)
        b_rm.pack(side="left", padx=6)
        self._reg(b_rm, "remove")
        b_clr = ttk.Button(btns, command=self._clear_files)
        b_clr.pack(side="left")
        self._reg(b_clr, "clear")
        # чтобы блокировать их на время конвертации
        self._file_buttons = [b_add, b_rm, b_clr]

    def _build_settings_panel(self, parent) -> None:
        frame = ttk.Labelframe(parent, padding=10)
        frame.grid(row=0, column=1, sticky="nsew")
        frame.columnconfigure(1, weight=1)
        self._reg(frame, "settings")
        r = 0

        self.lbl_target = ttk.Label(frame)
        self.lbl_target.grid(row=r, column=0, sticky="w", pady=4)
        self._reg(self.lbl_target, "target_format")
        self.target_var = tk.StringVar(value=Format.DOCX.title)
        self.cmb_target = ttk.Combobox(frame, textvariable=self.target_var, state="readonly",
                                       values=[f.title for f in _TARGETS])
        self.cmb_target.grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        self.lbl_backend = ttk.Label(frame)
        self.lbl_backend.grid(row=r, column=0, sticky="w", pady=4)
        self._reg(self.lbl_backend, "backend")
        self.backend_var = tk.StringVar(value="auto")
        self.cmb_backend = ttk.Combobox(frame, textvariable=self.backend_var, state="readonly")
        self.cmb_backend.grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        self.lbl_preset = ttk.Label(frame)
        self.lbl_preset.grid(row=r, column=0, sticky="w", pady=4)
        self._reg(self.lbl_preset, "preset")
        self._presets = {"—": None}
        self._presets.update({title: name for name, title in list_presets().items()})
        self.preset_var = tk.StringVar(value="—")
        self.cmb_preset = ttk.Combobox(frame, textvariable=self.preset_var, state="readonly",
                                       values=list(self._presets.keys()))
        self.cmb_preset.grid(row=r, column=1, sticky="ew", pady=4)
        r += 1

        # опции
        opt = ttk.Labelframe(frame, padding=8)
        opt.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        self._reg(opt, "options")
        self.var_toc = tk.BooleanVar()
        self.var_zip = tk.BooleanVar()
        self.var_embed = tk.BooleanVar()
        self.var_number = tk.BooleanVar()
        self.var_overwrite = tk.BooleanVar()
        c1 = ttk.Checkbutton(opt, variable=self.var_toc)
        c1.pack(anchor="w"); self._reg(c1, "opt_toc")
        c4 = ttk.Checkbutton(opt, variable=self.var_number)
        c4.pack(anchor="w"); self._reg(c4, "opt_number")
        c2 = ttk.Checkbutton(opt, variable=self.var_zip)
        c2.pack(anchor="w"); self._reg(c2, "opt_zip")
        c3 = ttk.Checkbutton(opt, variable=self.var_embed)
        c3.pack(anchor="w"); self._reg(c3, "opt_embed")
        c5 = ttk.Checkbutton(opt, variable=self.var_overwrite)
        c5.pack(anchor="w"); self._reg(c5, "opt_overwrite")
        r += 1

        # метаданные EPUB
        meta = ttk.Labelframe(frame, padding=8)
        meta.grid(row=r, column=0, columnspan=2, sticky="ew", pady=4)
        meta.columnconfigure(1, weight=1)
        self._reg(meta, "epub_meta")
        self.lbl_mtitle = ttk.Label(meta); self.lbl_mtitle.grid(row=0, column=0, sticky="w")
        self._reg(self.lbl_mtitle, "meta_title")
        self.ent_title = ttk.Entry(meta); self.ent_title.grid(row=0, column=1, sticky="ew", pady=2)
        self.lbl_mauthor = ttk.Label(meta); self.lbl_mauthor.grid(row=1, column=0, sticky="w")
        self._reg(self.lbl_mauthor, "meta_author")
        self.ent_author = ttk.Entry(meta); self.ent_author.grid(row=1, column=1, sticky="ew", pady=2)
        self.lbl_mlang = ttk.Label(meta); self.lbl_mlang.grid(row=2, column=0, sticky="w")
        self._reg(self.lbl_mlang, "meta_lang")
        self.ent_lang = ttk.Entry(meta); self.ent_lang.insert(0, "ru")
        self.ent_lang.grid(row=2, column=1, sticky="ew", pady=2)
        r += 1

        # вывод
        out = ttk.Labelframe(frame, padding=8)
        out.grid(row=r, column=0, columnspan=2, sticky="ew", pady=4)
        out.columnconfigure(0, weight=1)
        self._reg(out, "output")
        self.out_mode = tk.StringVar(value="same")
        rb1 = ttk.Radiobutton(out, variable=self.out_mode, value="same",
                              command=self._update_out_label)
        rb1.grid(row=0, column=0, sticky="w"); self._reg(rb1, "out_same")
        row2 = ttk.Frame(out); row2.grid(row=1, column=0, sticky="ew")
        rb2 = ttk.Radiobutton(row2, variable=self.out_mode, value="choose",
                              command=self._choose_out_dir)
        rb2.pack(side="left"); self._reg(rb2, "out_choose")
        self.out_path_lbl = ttk.Label(out, style="Hint.TLabel", anchor="w")
        self.out_path_lbl.grid(row=2, column=0, sticky="ew")

    def _build_bottom_bar(self) -> None:
        bar = ttk.Frame(self.root, padding=(12, 6, 12, 12))
        bar.pack(fill="x", side="bottom")
        bar.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(bar, mode="determinate")
        self.progress.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.status = ttk.Label(bar, style="Hint.TLabel")
        self.status.grid(row=1, column=0, sticky="w")

        self.btn_open = ttk.Button(bar, command=self._open_output)
        self._reg(self.btn_open, "open_folder")
        self.btn_convert = ttk.Button(bar, style="Accent.TButton", command=self._start)
        self._reg(self.btn_convert, "convert")
        # колонка 1 — «Открыть папку результата» (появляется после конвертации)
        self.btn_convert.grid(row=0, column=2, rowspan=2, sticky="e", padx=(10, 0))

    # ------------------------------------------------------------ i18n
    def _retranslate(self) -> None:
        self.root.title(self.i18n.t("app_title"))
        for widget, attr, key in self._i18n_widgets:
            try:
                widget.configure(**{attr: self.i18n.t(key)})
            except tk.TclError:  # pragma: no cover
                pass
        self.tree.heading("#0", text=self.i18n.t("col_file"))
        self.tree.heading("status", text=self.i18n.t("col_status"))
        self.cmb_backend.configure(values=[
            self.i18n.t("backend_auto"), self.i18n.t("backend_pandoc"),
            self.i18n.t("backend_native"),
        ])
        self._backend_display = {
            self.i18n.t("backend_auto"): "auto",
            self.i18n.t("backend_pandoc"): "pandoc",
            self.i18n.t("backend_native"): "native",
        }
        # сохранить выбранный движок
        cur = self.backend_var.get()
        inv = {v: k for k, v in self._backend_display.items()}
        self.backend_var.set(inv.get(cur if cur in _BACKENDS else "auto", self.i18n.t("backend_auto")))
        self._menubar.entryconfigure(1, label=self.i18n.t("menu_about"))
        self.status.configure(text=self.i18n.t("ready"))
        self._update_out_label()

    def _toggle_lang(self) -> None:
        self.i18n.toggle()
        self._retranslate()

    def _about(self) -> None:
        messagebox.showinfo(self.i18n.t("menu_about"),
                            self.i18n.t("about_text", ver=__version__))

    def _check_pandoc(self) -> None:
        from markforge.core.backends.pandoc_locate import pandoc_available

        if not pandoc_available():
            self.status.configure(text=self.i18n.t("pandoc_missing"))

    # ------------------------------------------------------------ files
    def _add_paths(self, paths) -> None:
        for p in paths:
            path = Path(p)
            if not path.is_file():
                continue
            if path.suffix.lower() not in INPUT_EXTENSIONS:
                continue
            if path in self._paths:
                continue
            self._paths.append(path)
            self.tree.insert("", "end", iid=str(path), text=path.name,
                             values=(self.i18n.t("status_queued"),))
        if self._paths:
            self.hint.grid_remove()

    def _on_drop(self, event) -> None:
        paths = self.root.tk.splitlist(event.data)
        self._add_paths(paths)

    def _add_files_dialog(self) -> None:
        exts = " ".join(f"*{e}" for e in INPUT_EXTENSIONS)
        paths = filedialog.askopenfilenames(
            title=self.i18n.t("add_files"),
            filetypes=[("Документы", exts), ("Все файлы", "*.*")],
        )
        self._add_paths(paths)

    def _remove_selected(self) -> None:
        for iid in self.tree.selection():
            self.tree.delete(iid)
            p = Path(iid)
            if p in self._paths:
                self._paths.remove(p)
        if not self._paths:
            self.hint.grid()

    def _clear_files(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._paths.clear()
        self.hint.grid()

    # ------------------------------------------------------------ output
    def _update_out_label(self) -> None:
        if self.out_mode.get() == "choose" and self.last_output_dir:
            self.out_path_lbl.configure(text=str(self.last_output_dir))
        else:
            self.out_path_lbl.configure(text="")

    def _choose_out_dir(self) -> None:
        d = filedialog.askdirectory(title=self.i18n.t("out_choose"))
        if d:
            self.last_output_dir = Path(d)
            self.out_mode.set("choose")
        else:
            self.out_mode.set("same")
        self._update_out_label()

    def _open_output(self) -> None:
        target = self.last_output_dir
        if not target and self._paths:
            target = self._paths[0].parent
        if target and target.exists():
            try:
                os.startfile(str(target))  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover
                subprocess.Popen(["explorer", str(target)])

    # ------------------------------------------------------------ convert
    def _selected_target(self) -> Format:
        title = self.target_var.get()
        for f in _TARGETS:
            if f.title == title:
                return f
        return Format.DOCX

    def _selected_backend(self) -> str:
        disp = getattr(self, "_backend_display", {})
        return disp.get(self.backend_var.get(), "auto")

    def _build_options(self) -> ConvertOptions:
        preset = self._presets.get(self.preset_var.get())
        return ConvertOptions(
            toc=self.var_toc.get(),
            number_sections=self.var_number.get(),
            zip_output=self.var_zip.get(),
            embed_resources=self.var_embed.get(),
            overwrite=self.var_overwrite.get(),
            preset=preset,
            epub=EpubMetadata(
                title=self.ent_title.get().strip() or None,
                authors=[self.ent_author.get().strip()] if self.ent_author.get().strip() else [],
                language=self.ent_lang.get().strip() or "ru",
            ),
        )

    def _start(self) -> None:
        if not self._paths:
            messagebox.showwarning(self.i18n.t("app_title"), self.i18n.t("no_files"))
            return
        target = self._selected_target()
        backend = self._selected_backend()
        options = self._build_options()
        out_dir = self.last_output_dir if self.out_mode.get() == "choose" else None

        for iid in self.tree.get_children():
            self.tree.set(iid, "status", self.i18n.t("status_queued"))
            self.tree.item(iid, tags=())

        self.btn_convert.configure(state="disabled")
        for b in self._file_buttons:  # нельзя менять список файлов во время конвертации
            b.configure(state="disabled")
        self.btn_open.grid_remove()
        self.progress.configure(maximum=len(self._paths), value=0)
        self.status.configure(text=self.i18n.t("converting"))

        worker = threading.Thread(
            target=self._worker,
            args=(list(self._paths), target, options, backend, out_dir),
            daemon=True,
        )
        worker.start()
        self.root.after(80, self._poll)

    def _worker(self, paths, target, options, backend, out_dir) -> None:
        ok = fail = 0
        for path in paths:
            try:
                if detect_format(path) == target:
                    self._queue.put(("skip", path, None))
                    continue
            except MarkForgeError:
                pass
            try:
                res = convert(path, target, options=options, backend=backend, output=out_dir)
                ok += 1
                self._queue.put(("ok", path, res))
            except Exception as e:  # noqa: BLE001
                fail += 1
                self._queue.put(("fail", path, e))
        self._queue.put(("done", ok, fail))

    def _poll(self) -> None:
        done = False
        try:
            while True:
                kind, a, b = self._queue.get_nowait()
                if kind == "done":
                    self._on_all_done(a, b)
                    done = True
                    break
                try:
                    self._on_one(kind, a, b)
                except Exception:  # noqa: BLE001 — не даём опросу заглохнуть
                    pass
        except queue.Empty:
            pass
        if not done:
            self.root.after(80, self._poll)

    def _on_one(self, kind, path, payload) -> None:
        self.progress.step(1)
        iid = str(path)
        exists = self.tree.exists(iid)  # строку могли убрать из списка
        if kind == "ok":
            self.last_output_dir = payload.artifact.parent
            if exists:
                label = self.i18n.t("status_ok")
                if payload.warnings:
                    label += " ⚠"
                self.tree.set(iid, "status", label)
                self.tree.item(iid, tags=("ok",))
        elif kind == "skip":
            if exists:
                self.tree.set(iid, "status", self.i18n.t("status_skip"))
                self.tree.item(iid, tags=("skip",))
        else:  # fail
            if exists:
                self.tree.set(iid, "status", self.i18n.t("status_fail"))
                self.tree.item(iid, tags=("fail",))

    def _on_all_done(self, ok, fail) -> None:
        self.btn_convert.configure(state="normal")
        for b in self._file_buttons:
            b.configure(state="normal")
        # step() у ttk.Progressbar на максимуме сбрасывается в 0 — показываем 100 % явно
        self.progress.configure(value=self.progress.cget("maximum"))
        self.status.configure(text=self.i18n.t("done_all", ok=ok, fail=fail))
        if self.last_output_dir:
            self.btn_open.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))
        self._update_out_label()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = ConverterApp()
    app.run()


if __name__ == "__main__":
    main()
