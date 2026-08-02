import os

PDF_ROOT = "data/pdfs"

def create_subject(subject_name):
    path = os.path.join(PDF_ROOT, subject_name)

    if not os.path.exists(path):
        os.makedirs(path)

    return path


def get_subjects():
    if not os.path.exists(PDF_ROOT):
        os.makedirs(PDF_ROOT)

    return sorted([
        folder
        for folder in os.listdir(PDF_ROOT)
        if os.path.isdir(os.path.join(PDF_ROOT, folder))
    ])


def get_subject_path(subject_name):
    return os.path.join(PDF_ROOT, subject_name)