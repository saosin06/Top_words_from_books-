import sqlite3
import tkinter as tk
from tkinter import messagebox
import requests
from collections import Counter
import re
from bs4 import BeautifulSoup


class DatabaseManager:
    """Handles all interactions with the SQLite database."""
    
    def __init__(self, db_name="books.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()
    
    def create_table(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS books 
                               (title TEXT, word TEXT, frequency INTEGER)''')
        self.conn.commit()
    
    def fetch_from_database(self, title):
        self.cursor.execute("SELECT word, frequency FROM books WHERE title=?", (title,))
        return self.cursor.fetchall()
    
    def insert_into_database(self, title, word_frequencies):
        for word, freq in word_frequencies:
            self.cursor.execute("INSERT INTO books (title, word, frequency) VALUES (?, ?, ?)", 
                                (title, word, freq))
        self.conn.commit()
    
    def close_connection(self):
        self.conn.close()


class TextAnalyzer:
    """Performs text analysis such as calculating word frequency."""
    
    @staticmethod
    def calculate_word_frequency(text):
        # Only keep alphabetic words and convert to lowercase
        words = re.findall(r'\b[a-z]+\b', text.lower())
        return Counter(words).most_common(10)


class GutenbergSearcher:
    """Handles searching Project Gutenberg for books."""
    
    @staticmethod
    def fetch_book_text(url):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an error for bad responses
            return response.text
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch data from URL: {e}")
            return None
    
    @staticmethod
    def search_gutenberg_for_title(title):
        search_url = f"https://www.gutenberg.org/ebooks/search/?query={title.replace(' ', '+')}"
        try:
            response = requests.get(search_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            # Find the first result that has a plain text link
            for result in soup.find_all('li', class_='booklink'):
                link = result.find('a', href=True)
                if link:
                    book_page_url = f"https://www.gutenberg.org{link['href']}"
                    # Navigate to the book page to find the plain text file link
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
    """Manages the GUI for the application."""
    
    def __init__(self, root):
        self.root = root
        self.db_manager = DatabaseManager()
        self.gutenberg_searcher = GutenbergSearcher()
        self.text_analyzer = TextAnalyzer()
        self.setup_gui()
    
    def setup_gui(self):
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
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showerror("Error", "Please enter a book title.")
            return

        data = self.db_manager.fetch_from_database(title)
        if data:
            self.display_results(data)
        else:
            # If not in the database, search Project Gutenberg
            url = self.gutenberg_searcher.search_gutenberg_for_title(title)
            if url:
                text = self.gutenberg_searcher.fetch_book_text(url)
                if text:
                    word_frequencies = self.text_analyzer.calculate_word_frequency(text)
                    self.db_manager.insert_into_database(title, word_frequencies)
                    self.display_results(word_frequencies)
    
    def search_url(self):
        url = self.url_entry.get().strip()
        title = self.title_entry.get().strip()
        if not url or not title:
            messagebox.showerror("Error", "Please enter both a book title and URL.")
            return

        text = self.gutenberg_searcher.fetch_book_text(url)
        if text:
            # Analyze text and store results in the database
            word_frequencies = self.text_analyzer.calculate_word_frequency(text)
            self.db_manager.insert_into_database(title, word_frequencies)
            self.display_results(word_frequencies)
    
    def display_results(self, data):
        self.results_text.delete("1.0", tk.END)
        for word, freq in data:
            self.results_text.insert(tk.END, f"{word}: {freq}\n")
    
    def on_close(self):
        self.db_manager.close_connection()
        self.root.destroy()


# Main application
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Book Word Frequency Analyzer")
    app = BookAnalyzerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
