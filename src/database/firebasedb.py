import pyrebase

firebaseConfig={ "apiKey": "AIzaSyCItpT1o1O8MDoFqN_wJNtWojH0GxRWBlM",
    "authDomain": "distributedproject-23.firebaseapp.com",
    "projectId": "distributedproject-23",
    "storageBucket": "distributedproject-23.appspot.com",
    "messagingSenderId": "765070258676",
    "appId": "1:765070258676:web:af1795308b8c75feeb49a1",
    "measurementId": "G-3SYWE5C4EK",
    "databaseURL": "https://distributedproject-23-default-rtdb.firebaseio.com/"}

firebase = pyrebase.initialize_app(firebaseConfig)
