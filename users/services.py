from users.models import CustomUser

def get_user(email: str) -> CustomUser:
    return CustomUser.objects.get(email=email)

def create_user(email: str) -> CustomUser:
    return CustomUser.objects.create_user(email=email, password=None)

def update_user(email: str) -> CustomUser:
    user = CustomUser.objects.get(email=email)
    user.save()
    return user

def delete_user(email: str) -> bool:
    count, _ = CustomUser.objects.filter(email=email).delete()
    return count > 0