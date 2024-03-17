# OMR Sheet Processing Web Application

This Django web application allows users to process OMR (Optical Mark Recognition) sheets by uploading images and providing answers for each question. The processed answers are then displayed and can be downloaded as a zip file.

## Installation

1. Clone the repository to your local machine:

    ```bash
    git clone https://github.com/suraj-k-s/OMR-UI.git
    ```

2. Navigate to the project directory:

    ```bash
    cd omr_sheet_processing
    ```

3. Install the required Python packages using pip:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Start the Django development server:

    ```bash
    python manage.py runserver
    ```

2. Open a web browser and go to [http://localhost:8000/](http://localhost:8000/) to access the application.

3. Upload OMR sheets images and provide answers for each question.

4. Click the "Process Image" button to process the uploaded images and generate the answers.

5. After processing, the answers will be displayed, and you can download them as a zip file.

## Folder Structure

- `omr_sheet_processing/`: Main Django project directory.
  - `main/`: Django app containing views, templates, and static files.
  - `OMR_Sheets/`: Folder to upload OMR sheet images.
  - `OMR_Answers/`: Folder to store processed answers.
  - `media/`: Django media root folder (automatically created).

## Requirements

- Python 3.x
- Django 3.x
- OpenCV (Python)
- NumPy

## License

This project is licensed under the [MIT License](LICENSE).
