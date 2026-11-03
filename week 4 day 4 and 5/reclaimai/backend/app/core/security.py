from datetime import datetime,timedelta,timezone
import jwt
from pwdlib import PasswordHash
from app.config import settings
password_hash=PasswordHash.recommended()
def hash_password(value:str)->str:return password_hash.hash(value)
def verify_password(value:str,stored:str)->bool:return password_hash.verify(value,stored)
def normalize_verification_answer(value:str)->str:return " ".join(value.split()).casefold()
def hash_verification_answer(value:str)->str:return hash_password(normalize_verification_answer(value))
def verify_verification_answer(value:str,stored:str)->bool:return verify_password(normalize_verification_answer(value),stored)
def create_access_token(subject:str,expires_delta:timedelta|None=None)->str:
    now=datetime.now(timezone.utc); exp=now+(expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    return jwt.encode({"sub":subject,"iat":now,"exp":exp},settings.jwt_secret_key,algorithm=settings.jwt_algorithm)
def decode_access_token(token:str)->dict:return jwt.decode(token,settings.jwt_secret_key,algorithms=[settings.jwt_algorithm])
