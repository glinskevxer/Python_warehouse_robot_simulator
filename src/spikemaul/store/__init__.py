"""The book: sqlite, the schema, and one register per kind of record.

A register takes records in and hands records out. It does not decide
anything, it does not print, and it does not know what a defect means. What it
does know is how a record turns into a row and back, which is the whole of
this layer's job and the reason it is worth having in one place.
"""

from spikemaul.store.codec import decode_date, decode_post, encode_date, encode_post

__all__ = ["decode_date", "decode_post", "encode_date", "encode_post"]
