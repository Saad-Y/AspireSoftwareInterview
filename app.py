import os
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, login_required, logout_user, current_user, UserMixin
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_
import re  

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure secret key
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'library.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Set an admin secret code for registration.
app.config['ADMIN_SECRET'] = 'myadminsecret'  # Change this value in production

db = SQLAlchemy(app)


def process_nlp_query(nlp_query):
    """
    Process a natural language query string to extract filters for the Book model.
    Recognized patterns:
      - "after <YYYY>"   → books with year > YYYY
      - "before <YYYY>"  → books with year < YYYY
      - "by <author>"    → books where the author name contains the provided text
    If no pattern is recognized, the entire query is used to search in title or author.
    """
    filters = []
    q = nlp_query.lower()

    # Pattern: "after <year>"
    after_match = re.search(r'after (\d{4})', q)
    if after_match:
        year_after = int(after_match.group(1))
        filters.append(Book.year > year_after)

    # Pattern: "before <year>"
    before_match = re.search(r'before (\d{4})', q)
    if before_match:
        year_before = int(before_match.group(1))
        filters.append(Book.year < year_before)

    # Pattern: "by <author>"
    by_match = re.search(r'by ([a-z\s]+)', q)
    if by_match:
        author_name = by_match.group(1).strip()
        filters.append(Book.author.ilike(f"%{author_name}%"))

    # If no filters were extracted, use the entire query to search title or author
    if not filters:
        filters.append(or_(
            Book.title.ilike(f"%{nlp_query}%"),
            Book.author.ilike(f"%{nlp_query}%")
        ))
    return filters

def get_recommendations(user):
    """
    Generate book recommendations for the given user.
    If the user currently has one or more books checked out,
    extract the authors from those books and recommend other books
    by those authors that the user hasn't borrowed.
    If the user has no checked-out books, return a default list
    of the latest books.
    """
    # Query books currently checked out by the user
    user_books = Book.query.filter_by(borrower=user.name, checked_out=True).all()
    
    if user_books:
        # Extract favorite authors (using a set to avoid duplicates)
        favorite_authors = set(book.author for book in user_books)
        # Recommend books by these authors that are not currently borrowed by the user
        recommendations = Book.query.filter(
            Book.author.in_(favorite_authors),
            Book.borrower != user.name  # Avoid recommending books the user already has
        ).all()
        return recommendations
    else:
        # Default: recommend the latest 5 books (you can adjust as needed)
        default_recommendations = Book.query.order_by(Book.year.desc()).limit(3).all()
        return default_recommendations

# -------------------------------
# Database Models
# -------------------------------

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default='user')  # Either 'user' or 'admin'
    password_hash = db.Column(db.String(150), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email} - {self.role}>'

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    year = db.Column(db.Integer)
    checked_out = db.Column(db.Boolean, default=False)
    borrower = db.Column(db.String(150), default='')

    def __repr__(self):
        return f'<Book {self.title}>'


# -------------------------------
# Flask-Login Setup
# -------------------------------
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect unauthenticated users to login page

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------------
# Role-based Authorization Decorator
# -------------------------------
def roles_required(*roles):
    """Ensure that the current user has one of the specified roles."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in first.", "danger")
                return redirect(url_for("login"))
            if current_user.role not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("index"))
            return func(*args, **kwargs)
        return wrapper
    return decorator

# -------------------------------
# Authentication Routes
# -------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user with email and password.
       If the correct admin code is supplied, register as an admin.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        admin_code = request.form.get('admin_code', '')
        
        if not email or not name or not password or not confirm:
            flash('All fields except admin code are required.', 'danger')
            return redirect(url_for('register'))
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
            
        role = 'admin' if admin_code == app.config['ADMIN_SECRET'] else 'user'
        user = User(email=email, name=name, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login user using email and password."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f"Logged in successfully as {user.name} ({user.role}).", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# -------------------------------
# Library Routes
# -------------------------------

@app.route('/')
@login_required
def index():
    """List all books with search filters for title/author, year, borrower, and natural language queries."""
    query = request.args.get('query', '')
    year = request.args.get('year', '')
    borrower = request.args.get('borrower', '')
    nlp_query = request.args.get('nlp_query', '')

    filters = []
    if query:
        filters.append(or_(
            Book.title.ilike(f'%{query}%'),
            Book.author.ilike(f'%{query}%')
        ))
    if year:
        try:
            filters.append(Book.year == int(year))
        except ValueError:
            flash('Year must be an integer.', 'danger')
            return redirect(url_for('index'))
    if borrower:
        filters.append(Book.borrower.ilike(f'%{borrower}%'))
    if nlp_query:
        # Incorporate filters derived from the natural language query
        filters += process_nlp_query(nlp_query)

    books = Book.query.filter(*filters).all() if filters else Book.query.all()
    recommendations = get_recommendations(current_user)
    
    return render_template(
        'index.html',
        books=books,
        query=query,
        year=year,
        borrower=borrower,
        nlp_query=nlp_query,
        recommendations=recommendations
    )

@app.route('/add', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def add_book():
    """Add a new book (admin only)."""
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        year = request.form.get('year')

        if not title or not author:
            flash('Title and Author are required fields.', 'danger')
            return redirect(url_for('add_book'))

        try:
            year = int(year) if year else None
        except ValueError:
            flash('Year must be an integer.', 'danger')
            return redirect(url_for('add_book'))

        new_book = Book(title=title, author=author, year=year)
        db.session.add(new_book)
        db.session.commit()
        flash('Book added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add_book.html')

@app.route('/delete/<int:book_id>', methods=['POST'])
@login_required
@roles_required('admin')
def delete_book(book_id):
    """Delete a book (admin only)."""
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash('Book deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/checkout/<int:book_id>', methods=['GET', 'POST'])
@login_required
def checkout_book(book_id):
    """Check out a book.
       - Regular users auto-checkout a book using their own name.
       - Admins can specify a custom borrower via a form.
    """
    book = Book.query.get_or_404(book_id)
    if book.checked_out:
        flash('Book is already checked out!', 'danger')
        return redirect(url_for('index'))

    if request.method == 'GET':
        if current_user.role != 'admin':
            # Regular user auto-checks out the book
            book.borrower = current_user.name
            book.checked_out = True
            db.session.commit()
            flash('Book checked out successfully!', 'success')
            return redirect(url_for('index'))
        else:
            # Admin user sees a form to optionally override the borrower name
            return render_template('checkout.html', book=book)
    else:  # POST
        if current_user.role == 'admin':
            borrower = request.form.get('borrower')
            if not borrower:
                flash('Borrower name is required!', 'danger')
                return redirect(url_for('checkout_book', book_id=book_id))
            book.borrower = borrower
        else:
            book.borrower = current_user.name
        book.checked_out = True
        db.session.commit()
        flash('Book checked out successfully!', 'success')
        return redirect(url_for('index'))

@app.route('/return/<int:book_id>', methods=['POST'])
@login_required
def return_book(book_id):
    """Return a checked-out book.
       Only the original borrower or an admin can return a book.
    """
    book = Book.query.get_or_404(book_id)
    if current_user.role != 'admin' and book.borrower != current_user.name:
        flash("You do not have permission to return this book.", "danger")
        return redirect(url_for('index'))
    if not book.checked_out:
        flash('Book is not checked out.', 'danger')
        return redirect(url_for('index'))

    book.borrower = ''
    book.checked_out = False
    db.session.commit()
    flash('Book returned successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def edit_book(book_id):
    """Edit an existing book (admin only)."""
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        year = request.form.get('year')
        
        if not title or not author:
            flash('Title and Author are required fields.', 'danger')
            return redirect(url_for('edit_book', book_id=book_id))
            
        book.title = title
        book.author = author
        try:
            book.year = int(year) if year else None
        except ValueError:
            flash('Year must be an integer.', 'danger')
            return redirect(url_for('edit_book', book_id=book_id))
            
        db.session.commit()
        flash('Book updated successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('edit_book.html', book=book)

# -------------------------------
# Run the Application
# -------------------------------
if __name__ == '__main__':
    app.run(debug=True)
