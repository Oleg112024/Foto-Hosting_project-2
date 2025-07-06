import os
import logging
from datetime import datetime
from flask import Flask, request, render_template, url_for, flash, redirect
from werkzeug.utils import secure_filename
from PIL import Image


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size
app.config['UPLOAD_FOLDER'] = 'images'

# Создаем директории, если они не существуют
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('logs', exist_ok=True)


# Настройка логирования
logging.basicConfig(
    filename='logs/app.log',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            logging.warning('Upload attempt without selecting a file')
            flash('Файл не выбран')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            logging.warning('Upload attempt with empty filename')
            flash('Файл не выбран')
            return redirect(request.url)
        
        logging.info(f'Starting file processing: {file.filename}')
        
        # Проверка размера файла
        try:
            file.seek(0, 2)  # Перемещаем указатель в конец файла
            file_size = file.tell()  # Получаем размер файла
            file.seek(0)  # Возвращаем указатель в начало
            
            if file_size > app.config['MAX_CONTENT_LENGTH']:
                logging.error(f'File size exceeds limit: {file_size} bytes (max: {app.config["MAX_CONTENT_LENGTH"]} bytes)')
                flash('Размер файла превышает допустимый предел (5MB)')
                return redirect(request.url)
                
            logging.info(f'File size check passed: {file_size} bytes')
        except Exception as e:
            logging.error(f'Error checking file size: {str(e)}')
            flash('Ошибка при проверке размера файла')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # разделяем имя файла от расширения
            base_name, ext_name = os.path.splitext(file.filename)
            # проверка имени на безопасность + расширение
            safe_filename = secure_filename(base_name) + ext_name
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            new_filename = f"{base_name}_(Foto-Hosting_{timestamp})_{ext_name}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)

            logging.info(f'File {base_name}_{ext_name} will be saved as {new_filename}')
            
            try:
                file.save(file_path)
                logging.info(f'File {new_filename} successfully saved to {file_path}')
                
                # Проверяем, что файл действительно является изображением
                with Image.open(file_path) as img:
                    img.verify()
                    img_size = os.path.getsize(file_path)
                    logging.info(f'File {new_filename} successfully verified as an image (size: {img_size} bytes)')
                
                image_url = url_for('uploaded_file', filename=new_filename, _external=True)
                logging.info(f'Access URL for file {new_filename}: {image_url}')
                return render_template('upload_success.html', image_url=image_url)
            
            except Exception as e:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logging.error(f'File {new_filename} deleted due to error: {str(e)}')
                logging.error(f'Error processing file {safe_filename}: {str(e)}')
                flash('Ошибка при загрузке файла')
                return redirect(request.url)
        else:
            logging.warning(f'Attempt to upload unsupported file format: {file.filename} (allowed formats: {", ".join(ALLOWED_EXTENSIONS)})')
            flash('Разрешены только изображения форматов: .jpg, .png, .gif')
            return redirect(request.url)
    
    return render_template('upload.html')


@app.route('/images/<filename>')
def uploaded_file(filename):
    return redirect(url_for('static', filename=f'images/{filename}'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)