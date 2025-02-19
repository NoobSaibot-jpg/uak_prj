import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import configparser
import os
import sys
import shutil
import fitz  # PyMuPDF
from PIL import Image, ImageTk

class PDFViewerApp:
    def __init__(self, master):
        self.master = master
        master.title("PDF/Image Viewer with Side Preview")
        master.state("zoomed")

        # Определяем путь к config.ini
        if getattr(sys, 'frozen', False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.config_file = os.path.join(self.base_path, "config.ini")
        self.config = configparser.ConfigParser()
        self.load_or_create_config()

        # Инициализация переменных состояния
        self.folder_path = ""
        self.files = []
        self.current_index = 0
        self.new_filename = tk.StringVar()
        self.selected_category = tk.StringVar()
        self.convert_to_pdf = tk.BooleanVar(value=False)

        # Инициализация GUI компонентов
        self.create_widgets()

    def load_or_create_config(self):
        """ Загружаем или создаем config.ini """
        if not os.path.exists(self.config_file):
            self.config["DEFAULT"] = {"Без категорії": os.path.join(self.base_path, "Без категорії")}
            with open(self.config_file, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)

        self.config.read(self.config_file, encoding="utf-8")
        self.categories = {key: value for key, value in self.config["DEFAULT"].items()}

    def create_widgets(self):
        control_frame = tk.Frame(self.master, width=300, padx=10, pady=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)

        tk.Button(control_frame, text="Обрати папку", command=self.select_folder).pack(pady=5)

        tk.Label(control_frame, text="Нове ім'я файла:").pack(anchor="w")
        self.new_filename_entry = tk.Entry(control_frame, textvariable=self.new_filename, width=40)
        self.new_filename_entry.pack(pady=5)

        tk.Label(control_frame, text="Категорія збереження:").pack(anchor="w")
        self.category_dropdown = ttk.Combobox(control_frame, textvariable=self.selected_category, state="readonly")
        self.category_dropdown["values"] = list(self.categories.keys())
        self.category_dropdown.pack(pady=5)
        self.category_dropdown.current(0)

        tk.Button(control_frame, text="Додати нову категорію", command=self.add_category).pack(pady=5)

        self.remaining_label = tk.Label(control_frame, text="Залишилось файлів: 0")
        self.remaining_label.pack(pady=5)

        tk.Button(control_frame, text="Зберегти і перейти до наступного", command=self.save_and_next).pack(pady=5)

        self.preview_frame = tk.Frame(self.master, bg="gray")
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.preview_frame, bg="black")
        self.scroll_y = tk.Scrollbar(self.preview_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.configure(yscrollcommand=self.scroll_y.set)
        self.convert_checkbox = ttk.Checkbutton(
            control_frame, 
            text="Конвертувати зображення в PDF",
            variable=self.convert_to_pdf
        )

    def select_folder(self):
        folder = filedialog.askdirectory(title="Оберіть папку з файлами")
        if folder:
            self.folder_path = folder
            # Добавляем поддержку изображений
            self.files = [f for f in os.listdir(folder) 
                        if f.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png'))]
            self.files.sort()
            self.current_index = 0
            self.update_remaining_files()
            self.load_next_file()

    def load_next_file(self):
        if self.current_index < len(self.files):
            filename = os.path.join(self.folder_path, self.files[self.current_index])
            self.load_preview(filename)
            # Показываем/скрываем чекбокс в зависимости от типа файла
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                self.convert_checkbox.pack(pady=5)
            else:
                self.convert_checkbox.pack_forget()
        else:
            messagebox.showinfo("Готово", "Всі файли оброблені")
            self.master.quit()

    def load_preview(self, filename):
        """Загружает превью файла и управляет видимостью чекбокса"""
        try:
            # Определяем тип файла
            is_image = filename.lower().endswith(('.jpg', '.jpeg', '.png'))
            
            # Управление видимостью чекбокса
            if is_image:
                self.convert_checkbox.pack(pady=5)
            else:
                self.convert_checkbox.pack_forget()

            # Загрузка контента
            if is_image:
                img = Image.open(filename)
            else:
                doc = fitz.open(filename)
                page = doc.load_page(0)
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Масштабирование и отображение
            img.thumbnail((800, 1000))
            img_tk = ImageTk.PhotoImage(img)

            # Очистка предыдущего превью
            self.canvas.delete("all")
            self.canvas.create_image(10, 10, anchor=tk.NW, image=img_tk)
            self.canvas.image = img_tk
            self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося завантажити файл:\n{str(e)}")
            # Сброс превью при ошибке
            self.canvas.delete("all")

    def save_and_next(self):
        if self.current_index < len(self.files):
            old_path = os.path.join(self.folder_path, self.files[self.current_index])
            new_name = self.new_filename.get().strip()

            # Удаляем существующее расширение из имени файла
            if '.' in new_name:
                new_name = os.path.splitext(new_name)[0]

            # Проверка обязательного имени файла
            if not new_name:
                messagebox.showerror("Помилка", "Введіть ім'я")
                return

            # Получаем выбранную категорию
            category = self.selected_category.get()
            save_path = self.categories.get(category, "")

            # Проверка категории "Без категорії"
            if category.lower() == "без категорії":
                confirm = messagebox.askyesno(
                    "Підтвердження",
                    "Ви обрали категорію 'Без категорії'. Продовжити?",
                    icon='question'
                )
                if not confirm:
                    return

            # Проверка существования пути категории
            if not save_path:
                messagebox.showerror("Помилка", "Виберіть категорію")
                return

            # Создаем папку категории если нужно
            os.makedirs(save_path, exist_ok=True)

            # Определяем тип файла и расширение
            is_image = old_path.lower().endswith(('.jpg', '.jpeg', '.png'))
            convert_to_pdf = self.convert_to_pdf.get() and is_image

            # Определяем конечное расширение
            output_extension = '.pdf' if convert_to_pdf else os.path.splitext(old_path)[1]
            save_full_path = os.path.join(save_path, f"{new_name}{output_extension}")

            # Проверка существования файла
            if os.path.exists(save_full_path):
                response = messagebox.askyesno(
                    "Файл існує",
                    "Файл з такою назвою вже існує. Додати індекс до імені?",
                    icon='question'
                )
                if response:
                    base_name = new_name
                    counter = 1
                    while True:
                        new_name_with_counter = f"{base_name}_{counter}{output_extension}"
                        new_save_path = os.path.join(save_path, new_name_with_counter)
                        if not os.path.exists(new_save_path):
                            save_full_path = new_save_path
                            break
                        counter += 1
                else:
                    return  # Отмена сохранения

            try:
                # Выполняем конвертацию или копирование
                if convert_to_pdf:
                    self.convert_image_to_pdf(old_path, save_full_path)
                else:
                    shutil.move(old_path, save_full_path)

                # Обновляем интерфейс
                self.new_filename.set("")
                self.current_index += 1
                self.update_remaining_files()
                self.load_next_file()

            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося зберегти:\n{str(e)}")
                # Удаляем частично созданный файл при ошибке
                if os.path.exists(save_full_path):
                    os.remove(save_full_path)

    def convert_image_to_pdf(self, image_path, pdf_path):
        """Конвертирует изображение в PDF"""
        try:
            image = Image.open(image_path)
            image.save(pdf_path, "PDF", resolution=100.0, save_all=True)
        except Exception as e:
            raise RuntimeError(f"Помилка конвертації: {str(e)}")

    def add_category(self):
        """ Добавление новой категории в config.ini """
        new_category = simpledialog.askstring("Нова категорія", "Введіть назву категорії:")
        if new_category:
            new_path = filedialog.askdirectory(title="Оберіть папку для збереження")
            if new_path:
                self.config["DEFAULT"][new_category] = new_path
                with open(self.config_file, "w", encoding="utf-8") as configfile:
                    self.config.write(configfile)

                self.categories[new_category] = new_path
                self.category_dropdown["values"] = list(self.categories.keys())
                self.category_dropdown.current(len(self.categories) - 1)

    def update_remaining_files(self):
        remaining = len(self.files) - self.current_index
        self.remaining_label.config(text=f"Файлів залишилось: {remaining}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFViewerApp(root)
    root.mainloop()


# pyinstaller --onefile --noconsole main.py
# py -3.9 -m pip install pyinstaller
# C:\Users\kra4k\AppData\Local\Programs\Python\Python310\python.exe -m pip install pyinstaller
# C:\Users\kra4k\AppData\Local\Programs\Python\Python310\python.exe -m PyInstaller --onefile --noconsole main.py