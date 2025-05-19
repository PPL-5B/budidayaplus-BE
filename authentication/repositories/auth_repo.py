from django.contrib.auth.models import User

class UserRepository:
    @staticmethod
    def get_user_by_username(username):
        return User.objects.get(username=username)

    @staticmethod
    def user_exists(username):
        return User.objects.filter(username=username).exists()

    @staticmethod
    def create_user(username, password, first_name, last_name):
        return User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=True
        )

    @staticmethod
    def get_user_by_id(user_id):
        return User.objects.filter(id=user_id).exists()