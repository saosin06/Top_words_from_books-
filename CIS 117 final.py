#Final Presentation CIS 117 Project gut


import sqlite3
import tkinter as tk
from tkinter import messagebox
import requests
from collections import Counter
import re
from bs4 import BeautifulSoup


# Database setup
def create_table():
    conn = sqlite3.connect("books.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS books 
                      (title TEXT, word TEXT, frequency INTEGER)''')
    conn.commit()
    conn.close()

def fetch_from_database(title):
    conn = sqlite3.connect("books.db")
    cursor = conn.cursor()
    cursor.execute("SELECT word, frequency FROM books WHERE title=?", (title,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def insert_into_database(title, word_frequencies):
    conn = sqlite3.connect("books.db")
    cursor = conn.cursor()
    for word, freq in word_frequencies:
        cursor.execute("INSERT INTO books (title, word, frequency) VALUES (?, ?, ?)", 
                       (title, word, freq))
    conn.commit()
    conn.close()

# Word frequency analysis
def calculate_word_frequency(text):
    # Only keep alphabetic words and convert to lowercase
    words = re.findall(r'\b[a-z]+\b', text.lower())
    return Counter(words).most_common(10)

# Fetch book text
def fetch_book_text(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        return response.text
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch data from URL: {e}")
        return None

# Search Project Gutenberg for book title
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

# GUI functions
def search_title():
    title = title_entry.get().strip()
    if not title:
        messagebox.showerror("Error", "Please enter a book title.")
        return

    data = fetch_from_database(title)
    if data:
        display_results(data)
    else:
        # If not in the database, search Project Gutenberg
        url = search_gutenberg_for_title(title)
        if url:
            text = fetch_book_text(url)
            if text:
                word_frequencies = calculate_word_frequency(text)
                insert_into_database(title, word_frequencies)
                display_results(word_frequencies)

def search_url():
    url = url_entry.get().strip()
    title = title_entry.get().strip()
    if not url or not title:
        messagebox.showerror("Error", "Please enter both a book title and URL.")
        return

    text = fetch_book_text(url)
    if text:
        # Analyze text and store results in the database
        word_frequencies = calculate_word_frequency(text)
        insert_into_database(title, word_frequencies)
        display_results(word_frequencies)

def display_results(data):
    results_text.delete("1.0", tk.END)
    for word, freq in data:
        results_text.insert(tk.END, f"{word}: {freq}\n")


# GUI setup
create_table()
root = tk.Tk()
root.title("Book Word Frequency Analyzer")

# Title input
tk.Label(root, text="Book Title:").pack()
title_entry = tk.Entry(root, width=50)
title_entry.pack()

# Search by title
tk.Button(root, text="Search Title", command=search_title).pack()

# URL input
tk.Label(root, text="Book URL:").pack()
url_entry = tk.Entry(root, width=50)
url_entry.pack()

# Search by URL
tk.Button(root, text="Search URL", command=search_url).pack()

# Results display
results_text = tk.Text(root, width=60, height=20)
results_text.pack()

# Run GUI loop
root.mainloop()

