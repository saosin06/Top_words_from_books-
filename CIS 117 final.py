# File: book_analyzer.py
# Author: Nick Costello
# Date: 12/11/2024
# Description: An application that searches Project Gutenberg for books, analyzes word frequencies, and stores results in an SQLite database. 
# The application uses a GUI for user interaction.

import sqlite3
import tkinter as tk
from tkinter import messagebox
import requests
from collections import Counter
import re
from bs4 import BeautifulSoup


class DatabaseManager:
    """
    Handles all interactions with the SQLite database.

    Attributes:
        conn (sqlite3.Connection): Database connection object.
        cursor (sqlite3.Cursor): Cursor for executing SQL commands.
    """

    def __init__(self, db_name="books.db"):
        """
        Initializes the database connection and ensures the table exists.

        Args:
            db_name (str): Name of the SQLite database file. Defaults to "books.db".
        """
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        """
        Creates a table for storing book titles, words, and word frequencies if it doesn't already exist.
        """
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS books 
                               (title TEXT, word TEXT, frequency INTEGER)''')
        self.conn.commit()

    def fetch_from_database(self, title):
        """
        Fetches word frequency data for a given book title from the database.

        Args:
            title (str): The title of the book.

        Returns:
            list: A list of tuples containing words and their frequencies.
        """
        self.cursor.execute("SELECT word, frequency FROM books WHERE title=?", (title,))
        return self.cursor.fetchall()

    def insert_into_database(self, title, word_frequencies):
        """
        Inserts word frequency data into the database for a given book title.

        Args:
            title (str): The title of the book.
            word_frequencies (list): A list of tuples containing words and their frequencies.
        """
        for word, freq in word_frequencies:
            self.cursor.execute("INSERT INTO books (title, word, frequency) VALUES (?, ?, ?)", 
                                (title, word, freq))
        self.conn.commit()

    def close_connection(self):
        """
        Closes the database connection.
        """
        self.conn.close()


class TextAnalyzer:
    """
    Performs text analysis such as calculating word frequency.
    """

    @staticmethod
    def calculate_word_frequency(text):
        """
        Calculates the top 10 most common words in a given text.

        Args:
            text (str): The input text.

        Returns:
            list: A list of tuples containing the most common words and their frequencies.
        """
        words = re.findall(r'\b[a-z]+\b', text.lower())  # Extract words using regex
        return Counter(words).most_common(10)


class GutenbergSearcher:
    """
    Handles searching Project Gutenberg for books and fetching their text.
    """

    @staticmethod
    def fetch_book_text(url):
        """
        Fetches the content of a book from the provided URL.

        Args:
            url (str): URL to the book's plain text file.

        Returns:
            str: The content of the book as text, or None if an error occurs.
        """
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch data from URL: {e}")
            return None

    @staticmethod
    def search_gutenberg_for_title(title):
        """
        Searches Project Gutenberg for a book by title.

        Args:
            title (str): The title of the book.

        Returns:
            str: URL of the plain text file of the book, or None if not found.
        """
        search_url = f"https://www.gutenberg.org/ebooks/search/?query={title.replace(' ', '+')}"
        try:
            response = requests.get(search_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for result in soup.find_all('li', class_='booklink'):
                link = result.find('a', href=True)
                if link:
                    book_page_url = f"https://www.gutenberg.org{link['href']}"
                    book_page_response = requests.get(book_page_url)
                    book_page_response.raise_for_status()
                    book_page_soup = BeautifulSoup(book_page_response.text, 'html.parser')
                    txt_link = book_page_soup.find('a', href=True, text="Plain Text UTF-8")
                    if txt_link:
                        return f"https://www.gutenberg.org{txt_link['href']}"
            messagebox.showinfo("Info", "Book not found in Project Gutenberg.")
            return None
        except Exception as e:
            messagebox.showerror("Error", f"Failed to search Project Gutenberg: {e}")
            return None


class BookAnalyzerGUI:
    """
    Manages the graphical user interface (GUI) for the application.

    Attributes:
        root (tk.Tk): The root window of the Tkinter application.
        db_manager (DatabaseManager): Manages database interactions.
        gutenberg_searcher (GutenbergSearcher): Handles book search and fetching.
        text_analyzer (TextAnalyzer): Analyzes word frequency.
    """

    def __init__(self, root):
        """
        Initializes the GUI and its components.

        Args:
            root (tk.Tk): The root window of the Tkinter application.
        """
        self.root = root
        self.db_manager = DatabaseManager()
        self.gutenberg_searcher = GutenbergSearcher()
        self.text_analyzer = TextAnalyzer()
        self.setup_gui()

    def setup_gui(self):
        """
        Sets up the GUI components for the application.
        """
        tk.Label(self.root, text="Book Title:").pack()
        self.title_entry = tk.Entry(self.root, width=50)
        self.title_entry.pack()

        tk.Button(self.root, text="Search Title", command=self.search_title).pack()

        tk.Label(self.root, text="Book URL:").pack()
        self.url_entry = tk.Entry(self.root, width=50)
        self.url_entry.pack()

        tk.Button(self.root, text="Search URL", command=self.search_url).pack()

        self.results_text = tk.Text(self.root, width=60, height=20)
        self.results_text.pack()

    def search_title(self):
        """
        Searches for a book by title, analyzes its text, and displays word frequencies.
        """
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showerror("Error", "Please enter a book title.")
            return

        data = self.db_manager.fetch_from_database(title)
        if data:
            self.display_results(data)
        else:
            url = self.gutenberg_searcher.search_gutenberg_for_title(title)
            if url:
                text = self.gutenberg_searcher.fetch_book_text(url)
                if text:
                    word_frequencies = self.text_analyzer.calculate_word_frequency(text)
                    self.db_manager.insert_into_database(title, word_frequencies)
                    self.display_results(word_frequencies)

    def search_url(self):
        """
        Fetches and analyzes text from a user-provided URL and displays word frequencies.
        """
        url = self.url_entry.get().strip()
        title = self.title_entry.get().strip()
        if not url or not title:
            messagebox.showerror("Error", "Please enter both a book title and URL.")
            return

        text = self.gutenberg_searcher.fetch_book_text(url)
        if text:
            word_frequencies = self.text_analyzer.calculate_word_frequency(text)
            self.db_manager.insert_into_database(title, word_frequencies)
            self.display_results(word_frequencies)

    def display_results(self, data):
        """
        Displays the results of word frequency analysis in the GUI.

        Args:
            data (list): A list of tuples containing words and their frequencies.
        """
        self.results_text.delete("1.0", tk.END)
        for word, freq in data:
            self.results_text.insert(tk.END, f"{word}: {freq}\n")

    def on_close(self):
        """
        Handles the closing of the application by closing the database connection.
        """
        self.db_manager.close_connection()
        self.root.destroy()


# Main application entry point
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Book Word Frequency Analyzer")
    app = BookAnalyzerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
