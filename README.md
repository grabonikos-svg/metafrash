# Metafrasi

Εφαρμογή για Windows που διαβάζει αγγλικό κείμενο από μια περιοχή της οθόνης και το δείχνει μεταφρασμένο στα ελληνικά. Η μετάφραση γίνεται τοπικά, με μοντέλο Argos, χωρίς να στέλνεται το κείμενο σε online υπηρεσία.

## Τι χρειάζεται

- Windows
- Python 3
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) με τα αγγλικά (`eng.traineddata`), στην προεπιλεγμένη διαδρομή `C:\Program Files\Tesseract-OCR`

## Εκτέλεση από τον κώδικα

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

Στην πρώτη εκκίνηση κατεβαίνει αυτόματα το μοντέλο αγγλικά προς ελληνικά. Το μοντέλο, το Tesseract και τα αρχεία build δεν περιλαμβάνονται σε αυτό το repository.

## Εκτελέσιμο

Το `build-exe.bat` φτιάχνει το πρόγραμμα με PyInstaller. Το `installer.iss` είναι το script του Inno Setup για τον installer.
