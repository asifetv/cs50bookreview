import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine (os.getenv("DATABASE_URL"))
db = scoped_session (sessionmaker(bind=engine))

def main ():
    f = open ("books.csv")
    reader = csv.reader (f)
    db.execute ('CREATE TABLE IF NOT EXISTS "books" ( '
                'isbn VARCHAR,'
                'title VARCHAR,'
                'author VARCHAR,'
                'year SMALLINT,'
                'PRIMARY KEY (isbn));')

    db.execute ("CREATE TABLE IF NOT EXISTS usertable (username VARCHAR(20) PRIMARY KEY UNIQUE, pwdhash VARCHAR(100) NOT NULL, firstname VARCHAR(100) NOT NULL,lastname VARCHAR(100) NOT NULL,email VARCHAR(120) NOT NULL)")
    counter = 0           
    for isbn, title, author, year in reader:
        db.execute ("INSERT INTO books(isbn, title, author, year) VALUES (:isbn,:title,:author,:year)",
                    {"isbn": isbn, "title": title, "author": author, "year": year})
        counter += 1
        print (f"{counter} -- Added book {title}.")
    db.commit ()

if __name__ == "__main__":
    main ()
        
                    
