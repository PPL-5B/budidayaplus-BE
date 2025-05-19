from authentication.repositories.auth_repo import UserRepository
from ninja_jwt.tokens import RefreshToken
from ninja.errors import HttpError
from ninja_jwt.exceptions import TokenError
from django.contrib.auth.models import User

class AuthenticationService:
    @staticmethod
    def login(phone_number, password):
        try:
            user = UserRepository.get_user_by_username(phone_number)
            if not user.check_password(password):
                raise HttpError(404, "Pengguna tidak terdaftar atau kata sandi salah")

            refresh = RefreshToken.for_user(user)
            return {
                "message": "Login berhasil",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        except User.DoesNotExist:
            raise HttpError(404, "Pengguna tidak terdaftar atau kata sandi salah")

    @staticmethod
    def register(phone_number, first_name, last_name, password):
        if UserRepository.user_exists(phone_number):
            raise HttpError(400, "Pengguna sudah terdaftar")

        user = UserRepository.create_user(phone_number, password, first_name, last_name)
        refresh = RefreshToken.for_user(user)
        return {
            "message": "Akun berhasil dibuat",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @staticmethod
    def refresh_token(refresh_token):
        try:
            refresh = RefreshToken(refresh_token)
            user_id = refresh.payload.get("user_id")
            if not UserRepository.get_user_by_id(user_id):
                raise HttpError(401, "Pengguna tidak ditemukan atau token tidak valid")

            return {"access": str(refresh.access_token)}
        except TokenError:
            raise HttpError(401, "Token invalid atau telah kadaluarsa")

    @staticmethod
    def validate_token(user):
        return {"message": "Token valid"}

    @staticmethod
    def get_user_details(user):
        return {
            "id": user.id,
            "phone_number": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }