from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize rate limiter with remote IP as the key function
limiter = Limiter(key_func=get_remote_address)
