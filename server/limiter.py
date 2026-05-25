from slowapi import Limiter
from slowapi.util import get_remote_address

# Inisialisasi Limiter global menggunakan remote IP address klien sebagai kunci
limiter = Limiter(key_func=get_remote_address)
