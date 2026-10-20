"""Persistence models with explicit public representations."""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import mapped_column, relationship

db = SQLAlchemy()


class BookAuthor(db.Model):
    __tablename__ = "book_authors"
    book_id = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), primary_key=True)
    author_id = mapped_column(ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True)
    role = mapped_column(String(4), nullable=False, default="co")
    __table_args__ = (CheckConstraint("role IN ('lead', 'co', 'ed')"),)
    author = relationship("Author", lazy="joined")


class Category(db.Model):
    __tablename__ = "categories"
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(100), nullable=False)
    slug = mapped_column(String(100), unique=True, nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "slug": self.slug}


class Author(db.Model):
    __tablename__ = "authors"
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(100), nullable=False)
    bio = mapped_column(Text, nullable=False, default="")
    books = relationship("Book", secondary="book_authors", viewonly=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "bio": self.bio}


class User(db.Model):
    __tablename__ = "users"
    id = mapped_column(Integer, primary_key=True)
    email = mapped_column(String(254), unique=True, nullable=False)
    display_name = mapped_column(String(100), nullable=False)

    def to_dict(self):
        return {"id": self.id, "display_name": self.display_name}


class Book(db.Model):
    __tablename__ = "books"
    id = mapped_column(Integer, primary_key=True)
    title = mapped_column(String(200), nullable=False)
    isbn = mapped_column(String(13), unique=True, nullable=False)
    price_vnd = mapped_column(Integer, nullable=False)
    stock = mapped_column(Integer, nullable=False, default=0)
    category_id = mapped_column(ForeignKey("categories.id"), nullable=False)
    category = relationship("Category", lazy="joined")
    author_links = relationship("BookAuthor", cascade="all, delete-orphan", lazy="selectin")
    authors = relationship("Author", secondary="book_authors", viewonly=True)
    reviews = relationship("Review", cascade="all, delete-orphan")
    __table_args__ = (
        CheckConstraint("price_vnd >= 0"), CheckConstraint("stock >= 0"),
        Index("ix_books_price_id", "price_vnd", "id"),
        Index("ix_books_category_price_id", "category_id", "price_vnd", "id"),
    )

    def to_dict(self):
        return {"id": f"book_{self.id}", "title": self.title, "isbn": self.isbn,
                "price": {"amount": self.price_vnd, "currency": "VND"},
                "stock": self.stock, "in_stock": self.stock > 0,
                "category": self.category.to_dict(),
                "authors": [{"id": a.author.id, "name": a.author.name, "role": a.role}
                            for a in self.author_links]}


class Review(db.Model):
    __tablename__ = "reviews"
    id = mapped_column(Integer, primary_key=True)
    rating = mapped_column(Integer, nullable=False)
    comment = mapped_column(Text, nullable=False, default="")
    book_id = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    user_id = mapped_column(ForeignKey("users.id"), nullable=False)
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5"),)

    def to_dict(self):
        return {"id": self.id, "rating": self.rating, "comment": self.comment,
                "book_id": f"book_{self.book_id}", "user_id": self.user_id}
