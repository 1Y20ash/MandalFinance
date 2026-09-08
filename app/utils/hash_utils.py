import hashlib

def compute_sha256(file_data_bytes_or_stream):
    """
    Computes SHA-256 hex string for a bytes object or file stream.
    """
    sha256_hash = hashlib.sha256()
    
    if isinstance(file_data_bytes_or_stream, bytes):
        sha256_hash.update(file_data_bytes_or_stream)
    else:
        # File-like object / stream
        file_data_bytes_or_stream.seek(0)
        for chunk in iter(lambda: file_data_bytes_or_stream.read(4096), b""):
            sha256_hash.update(chunk)
        file_data_bytes_or_stream.seek(0)
        
    return sha256_hash.hexdigest().lower()
